import requests
import json
import re

# مصادر القنوات
URL = "https://iptv-org.github.io/iptv/countries/jo.m3u"
WANTED = ["Jordan TV", "Roya", "Al Mamlaka", "Al Jazeera", "Rotana", "Spacetoon"]

def update():
    channels = []
    try:
        content = requests.get(URL).text
        lines = content.split('\n')
        current_name = None
        
        for line in lines:
            if line.startswith("#EXTINF"):
                for w in WANTED:
                    if w.lower() in line.lower():
                        current_name = w
                        break
            elif line.startswith("http") and current_name:
                # التأكد من عدم تكرار القناة
                if not any(c['name'] == current_name for c in channels):
                    channels.append({"name": current_name, "url": line.strip()})
                current_name = None
    except:
        pass
        
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False)

if __name__ == "__main__":
    update()
    print("Channels Updated!")
