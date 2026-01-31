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
        'SPACE.COM': 'https://www.space.com/feeds/all',
        'NASA': 'https://www.nasa.gov/rss/dyn/breaking_news.rss',
        'ARXIV': 'http://export.arxiv.org/api/query?search_query=cat:astro-ph&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending'
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

    def fetch_local_weather(self):
        # Coimbatore Coordinates
        LAT, LON = 11.0168, 76.9558
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        
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
        
        # 1. RSS Feeds (Parallel)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.parse_feed, source, url): source for source, url in self.FEED_SOURCES.items()}
            for future in futures:
                try:
                    aggregated_items.extend(future.result())
                except Exception as e:
                    print(f"Feed Error ({futures[future]}): {e}")

        aggregated_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # 2. Add Local Weather
        weather = self.fetch_local_weather()
        if weather: aggregated_items.append(weather)
        
        # 3. Special Data (NOAA & Launch) - Serial (fast APIs)
        try:
            solar_data = self.fetch_noaa_data()
            if solar_data: aggregated_items.append(solar_data)
        except Exception as e:
            print(f"NOAA Error: {e}")

        try:
            launch_data = self.fetch_launch_data()
            if launch_data: aggregated_items.append(launch_data)
        except Exception as e:
            print(f"Launch Error: {e}")

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
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries: pass

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
                if 'media_content' in entry: image_url = entry.media_content[0]['url']
                elif 'media_thumbnail' in entry: image_url = entry.media_thumbnail[0]['url']
                
                if not image_url and 'enclosures' in entry:
                     for enc in entry.enclosures:
                         if enc.type.startswith('image/'):
                             image_url = enc.href
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
