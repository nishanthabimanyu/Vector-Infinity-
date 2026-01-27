
import requests
from PySide6.QtCore import QObject, Signal, QByteArray
from PySide6.QtGui import QPixmap

class ImageWorker(QObject):
    """
    Worker to fetch thumbnail images from Wikipedia API.
    """
    finished = Signal(QPixmap, str) # Emits (Pixmap, Description/Title)

    def fetch_image(self, query):
        if not query:
            self.finished.emit(QPixmap(), "NO SIGNAL")
            return

        # Simple mapping for common tough queries if needed
        search_term = query
        
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "prop": "pageimages|description", # Get thumbnail and short desc
            "format": "json",
            "piprop": "thumbnail",
            "pithumbsize": 500, # Decent size
            "titles": search_term,
            "origin": "*"
        }
        
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            
            # Parse 'pages' dict
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id == "-1": # Not found
                    continue
                
                # Get Thumbnail URL
                thumb_info = page_data.get("thumbnail")
                if thumb_info:
                    img_url = thumb_info["source"]
                    img_resp = requests.get(img_url, timeout=5)
                    pixmap = QPixmap()
                    pixmap.loadFromData(QByteArray(img_resp.content))
                    
                    self.finished.emit(pixmap, page_data.get("title", query))
                    return

            # If loop finishes without return, nothing found
            self.finished.emit(QPixmap(), "DATA NOT FOUND")
            
        except Exception as e:
            print(f"Image Fetch Error: {e}")
            self.finished.emit(QPixmap(), "CONNECTION ERROR")
