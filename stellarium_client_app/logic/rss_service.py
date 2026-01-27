
import requests
import xml.etree.ElementTree as ET
import re
import base64
from PySide6.QtCore import QObject, Signal, QThread

class RSSWorker(QObject):
    """
    Worker to fetch RSS feed.
    Features:
    - Aggressive Image Regex
    - Simulation Fallback
    - BASE64 Image Conversion (Bypasses Qt Network Issues)
    """
    finished = Signal(list)
    
    def __init__(self, feed_url=None):
        super().__init__()
        self.feed_url = feed_url or "https://www.nasa.gov/rss/dyn/breaking_news.rss"

    def run(self):
        news_items = []
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(self.feed_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                content = response.content
                try:
                    root = ET.fromstring(content)
                except:
                    print("XML Parse Error")
                    return

                namespaces = {
                    'media': 'http://search.yahoo.com/mrss/',
                    'atom': 'http://www.w3.org/2005/Atom',
                    'content': 'http://purl.org/rss/1.0/modules/content/'
                }

                items = root.findall('./channel/item')
                if not items:
                    items = root.findall('.//item') + root.findall('.//{http://www.w3.org/2005/Atom}entry')

                for item in items:
                    def get_text(elem, tag):
                        v = elem.find(tag)
                        if v is None:
                            for ns in namespaces.values():
                                v = elem.find(f"{{{ns}}}{tag}")
                                if v is not None: break
                        return v.text if v is not None else ""
                        
                    title = get_text(item, 'title') or "No Title"
                    description = ""
                    content_encoded = item.find('content:encoded', namespaces)
                    if content_encoded is not None:
                        description = content_encoded.text
                    else:
                        description = get_text(item, 'description') or get_text(item, 'summary')
                        
                    pub_date = get_text(item, 'pubDate') or get_text(item, 'updated') or ""
                    
                    # --- IMAGE EXTRACTION ---
                    image_url = ""
                    
                    enclosure = item.find('enclosure')
                    if enclosure is not None:
                        if 'image' in enclosure.get('type', '') or 'jpg' in enclosure.get('url', ''):
                            image_url = enclosure.get('url')
                            
                    if not image_url:
                        media_content = item.find('media:content', namespaces)
                        if media_content is not None:
                            image_url = media_content.get('url')
                        else:
                            media_thumb = item.find('media:thumbnail', namespaces)
                            if media_thumb is not None:
                                image_url = media_thumb.get('url')

                    if not image_url and description:
                        match = re.search(r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']', description, re.IGNORECASE)
                        if match:
                            image_url = match.group(1)

                    clean_desc = description
                    if clean_desc:
                        clean_desc = re.sub(r'<img[^>]+>', '', clean_desc, flags=re.IGNORECASE)
                        clean_desc = re.sub(r'<p>\s*</p>', '', clean_desc)

                    # --- CONVERT TO BASE64 ---
                    b64_image = ""
                    if image_url:
                        b64_image = self._download_image_as_base64(image_url)

                    news_items.append({
                        "title": title,
                        "description": clean_desc,
                        "date": pub_date,
                        "image": b64_image 
                    })
                    
                    if len(news_items) >= 5:
                        break
                        
        except Exception as e:
            print(f"RSS Fetch Error ({self.feed_url}): {e}")
            news_items = self._get_simulation_data()
        
        self.finished.emit(news_items)

    def _download_image_as_base64(self, url):
        """Downloads image and converts to base64 string for embedding."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                b64 = base64.b64encode(r.content).decode('utf-8')
                # Determine mime type roughly
                mime = "image/jpeg"
                if url.lower().endswith(".png"): mime = "image/png"
                elif url.lower().endswith(".gif"): mime = "image/gif"
                return f"data:{mime};base64,{b64}"
        except:
            pass
        return ""

    def _get_simulation_data(self):
        """Returns mock data with pre-fetched Base64 images is too large for code, using URL fallback or simple placeholder."""
        # For simulation, we will stick to URLs because they are reliable usually, but 
        # let's try to fetch them here too.
        
        sim_data = [
            {
                "title": "SIMULATION: JAMES WEBB TELESCOPE DATA",
                "description": "Network uplink failed. Switching to cached simulation banking.",
                "date": "CACHED DATA",
                "image_source": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/Hubble_ultra_deep_field_high_rez_edit1.jpg/800px-Hubble_ultra_deep_field_high_rez_edit1.jpg"
            },
            {
                 "title": "ARCHIVE: MARS PERSEVERANCE ROVER",
                 "description": "This is a simulated entry to verify UI formatting.",
                 "date": "ARCHIVE RECORD",
                 "image_source": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/NASA_Mars_Rover.jpg/800px-NASA_Mars_Rover.jpg"
            }
        ]
        
        final_items = []
        for item in sim_data:
            b64 = self._download_image_as_base64(item["image_source"])
            final_items.append({
                "title": item["title"],
                "description": item["description"],
                "date": item["date"],
                "image": b64
            })
            
        return final_items
