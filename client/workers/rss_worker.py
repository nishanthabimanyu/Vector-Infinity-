import feedparser
import html
import json
import requests
from PySide6.QtCore import QThread, Signal
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from time import mktime

class RSSWorker(QThread):
    feed_ready = Signal(list)

    FEED_SOURCES = {
        # NEW: High-Res Image Feeds
        'NASA IOTD': 'https://www.nasa.gov/rss/dyn/lg_image_of_the_day.rss',
        'ESA SCIENCE': 'https://www.esa.int/rssfeed/Our_Activities/Space_Science', # Stable Feed
        'HUBBLE': 'https://hubblesite.org/rss/news',
        'SPACE.COM': 'https://www.space.com/feeds/all'
    }

    def run(self):
        last_fetch = None
        cache_duration = timedelta(minutes=15)
        cached_items = []

        while not self.isInterruptionRequested():
            now = datetime.now()
            
            # Fetch if cache expired or not set
            if not last_fetch or (now - last_fetch) > cache_duration:
                print("RSSWorker: Refreshing Multi-Stream Feeds...")
                fetched_items = self.fetch_all_data()
                
                if fetched_items:
                    cached_items = fetched_items
                    last_fetch = now
                    # Emit immediately
                    self.feed_ready.emit(cached_items)
                else:
                    if not cached_items: # Emit error state if nothing
                         self.feed_ready.emit([])

            # Sleep Loop (check interruption frequently)
            for _ in range(60): 
                if self.isInterruptionRequested():
                    return
                self.sleep(1)
    
    def shutdown(self):
        self.requestInterruption()
        self.wait()

    def fetch_location(self):
        try:
            # IP-based Geolocation (ipinfo.io is often more precise than ip-api)
            # Fallback to ip-api if fails
            data = {}
            try:
                resp = requests.get('https://ipinfo.io/json', timeout=3)
                if resp.status_code == 200:
                    d = resp.json()
                    loc = d.get('loc', '0,0').split(',')
                    data = {
                        'city': d.get('city', 'Unknown'),
                        'region': d.get('region', ''),
                        'lat': float(loc[0]),
                        'lon': float(loc[1]),
                        'country': d.get('country', '')
                    }
            except:
                # Fallback
                resp = requests.get('http://ip-api.com/json/', timeout=3)
                if resp.status_code == 200:
                    d = resp.json()
                    data = {
                        'city': d.get('city', 'Unknown'),
                        'region': d.get('regionName', ''),
                        'lat': d.get('lat', 0.0),
                        'lon': d.get('lon', 0.0),
                        'country': d.get('country', '')
                    }

            if data:
                return {
                    'type': 'LOCATION',
                    'city': data.get('city', 'Unknown'),
                    'region': data.get('region', ''),
                    'country': data.get('country', ''),
                    'lat': data.get('lat', 11.0168),
                    'lon': data.get('lon', 76.9558),
                    'timestamp': datetime.now().timestamp()
                }
        except:
            pass
        return None

    def fetch_local_weather(self, lat=11.0168, lon=76.9558):
        # Default to Coimbatore if no geo data yet
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                cw = data.get('current_weather', {})
                return {
                    'type': 'WEATHER',
                    'temp': cw.get('temperature', 0),
                    'code': cw.get('weathercode', 0),
                    'wind': cw.get('windspeed', 0),
                    'source': 'OPEN-METEO'
                }
        except Exception as e:
            print(f"Weather Error: {e}")
        return None

    def fetch_all_data(self):
        aggregated_items = []
        
        # 1. Pre-Fetch Location (Fast) to determine Weather Coords
        loc_data = self.fetch_location()
        if loc_data: aggregated_items.append(loc_data)
        
        lat, lon = (loc_data['lat'], loc_data['lon']) if loc_data else (11.0168, 76.9558)

        # 2. Parallel Execution for remaining sources
        with ThreadPoolExecutor(max_workers=8) as executor:
            # RSS Feeds
            futures = {executor.submit(self.parse_feed, source, url): f"RSS-{source}" for source, url in self.FEED_SOURCES.items()}
            
            # API Feeds (Weather uses dynamic coords)
            futures[executor.submit(self.fetch_local_weather, lat, lon)] = "WEATHER"
            futures[executor.submit(self.fetch_noaa_data)] = "NOAA"
            futures[executor.submit(self.fetch_launch_data)] = "LAUNCH"
            futures[executor.submit(self.fetch_quake_data)] = "QUAKE"
            futures[executor.submit(self.fetch_iss_data)] = "ISS"
            
            for future in futures:
                try:
                    res = future.result()
                    if res:
                        if isinstance(res, list): # RSS returns list
                            aggregated_items.extend(res)
                        else: # APIs return dict
                            aggregated_items.append(res)
                except Exception as e:
                    print(f"Data Fetch Error ({futures[future]}): {e}")

        aggregated_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return aggregated_items

    def fetch_quake_data(self):
        # USGS Feed: 2.5+ Magnitude Earthquakes, Past Day
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('features'):
                    # Get the most recent significant quake
                    quake = data['features'][0]['properties']
                    return {
                        'type': 'SEISMIC',
                        'mag': quake['mag'],
                        'place': quake['place'],
                        'time': quake['time'],
                        'timestamp': quake['time'] / 1000 # Convert ms to s
                    }
        except:
            pass
        return None

    def fetch_iss_data(self):
        # 1. ORBITAL PHYSICS (Celestrak - Cached if possible, but we fetch live for now)
        # We want Inclination and Period (derived from Mean Motion)
        orbit_data = {}
        try:
            url = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=JSON"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    sat = data[0]
                    # Calc Period: 1440 mins / Mean Motion (revs/day)
                    mm = sat.get('MEAN_MOTION', 15.48)
                    period = 1440.0 / mm
                    orbit_data = {
                        'inclination': sat.get('INCLINATION', 0),
                        'period': period,
                        'name': sat.get('OBJECT_NAME', 'ISS')
                    }
        except:
            pass
            
        # 2. REAL-TIME POSITION (Open-Notify)
        # Because we lack SGP4 to propagate Celestrak TLE
        pos_data = {}
        try:
            url = "http://api.open-notify.org/iss-now.json"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if 'iss_position' in data:
                    pos = data['iss_position']
                    pos_data = {
                        'lat': float(pos['latitude']),
                        'lon': float(pos['longitude'])
                    }
        except:
            pass
            
        if orbit_data or pos_data:
            return {
                'type': 'SATELLITE',
                'name': orbit_data.get('name', 'ISS (ZARYA)'),
                'inclination': orbit_data.get('inclination', 51.6),
                'period': orbit_data.get('period', 92.9),
                'lat': pos_data.get('lat', 0.0),
                'lon': pos_data.get('lon', 0.0),
                'timestamp': datetime.now().timestamp()
            }
        return None

        aggregated_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        return aggregated_items

    def fetch_noaa_data(self):
        # Planetary K-index (3-hour data)
        url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # Format: [ [time, kp, a_running, station_count], ... ]
                # Last item is newest
                if len(data) > 1:
                    latest = data[-1]
                    kp = float(latest[1])
                    return {
                        'type': 'SOLAR',
                        'source': 'NOAA',
                        'k_index': kp,
                        'timestamp': datetime.now().timestamp(),
                        'title': f"K-Index: {kp}"
                    }
        except:
            pass
        return None

    def fetch_launch_data(self):
        # LL2 Upcoming
        url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=1"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('results'):
                    launch = data['results'][0]
                    return {
                        'type': 'LAUNCH',
                        'source': 'LL2',
                        'title': launch['name'],
                        'date': launch['net'], # ISO String
                        'location': launch['pad']['location']['name'],
                        'image': launch.get('image', ''),
                        'timestamp': datetime.now().timestamp()
                    }
        except:
            pass
        return None

    def parse_feed(self, source, url):
        items = []
        try:
            # Bypass potential User-Agent blocking (ESA/Hubble)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                print(f"Feed Error {source}: Status {resp.status_code}")
                return []
                
            feed = feedparser.parse(resp.content)
            if not feed.entries: 
                print(f"Feed Empty {source}")
                pass

            for entry in feed.entries[:5]:
                title = entry.get('title', 'No Title')
                link = entry.get('link', '#')
                summary = entry.get('summary', '') or entry.get('description', '')
                
                timestamp = 0
                pub_date_str = ""
                if 'published_parsed' in entry and entry.published_parsed:
                    timestamp = mktime(entry.published_parsed)
                    pub_date_str = datetime.fromtimestamp(timestamp).strftime("%a, %d %b %H:%M")
                elif 'updated_parsed' in entry and entry.updated_parsed:
                    timestamp = mktime(entry.updated_parsed)
                    pub_date_str = datetime.fromtimestamp(timestamp).strftime("%a, %d %b %H:%M")
                
                image_url = ""
                
                # PRIORITY 1: Media Content (Standard)
                if 'media_content' in entry: 
                    image_url = entry.media_content[0]['url']
                
                # PRIORITY 2: Enclosures (Podcasts/NASA)
                elif 'enclosures' in entry:
                     for enc in entry.enclosures:
                         if enc.type.startswith('image/'):
                             image_url = enc.href
                             break
                
                # PRIORITY 3: 'links' tag (New NASA Format)
                if not image_url and 'links' in entry:
                    for link in entry.links:
                        if link.get('rel') == 'enclosure' and link.get('type', '').startswith('image/'):
                            image_url = link.get('href')
                            break
                
                title = html.unescape(title)
                
                items.append({
                    'title': title,
                    'link': link,
                    'pubDate': pub_date_str,
                    'timestamp': timestamp,
                    'source': source,
                    'summary': summary,
                    'image': image_url,
                    'type': 'NEWS' # Default type
                })
        except Exception as e:
            print(f"Parse Error {source}: {e}")
            
        return items
