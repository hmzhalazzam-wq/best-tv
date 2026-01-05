import requests
import json
import re

# المصدر: كل القنوات العربية + القنوات الأردنية
URLS = [
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://iptv-org.github.io/iptv/countries/jo.m3u"
]

def update():
    channels = []
    seen_names = set() # لمنع تكرار القنوات بنفس الاسم

    print("جاري سحب كافة القنوات العربية...")
    
    for url in URLS:
        try:
            response = requests.get(url)
            response.encoding = 'utf-8' # ضمان قراءة اللغة العربية صح
            lines = response.text.split('\n')
            
            current_ch = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # استخراج المعلومات
                    name_match = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    name = name_match.group(1).strip() if name_match else "Unknown Channel"
                    
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_match.group(1) if logo_match else ""
                    
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    group = group_match.group(1).lower() if group_match else "other"
                    
                    # تنظيف التصنيفات
                    if "news" in group: category = "news"
                    elif "sport" in group: category = "sports"
                    elif "movie" in group or "cinema" in group or "film" in group: category = "movies"
                    elif "kid" in group or "cartoon" in group: category = "kids"
                    elif "religious" in group or "islam" in group: category = "religious"
                    elif "music" in group: category = "music"
                    elif "documentary" in group: category = "docu"
                    else: category = "general"

                    current_ch = {
                        "name": name,
                        "logo": logo,
                        "category": category
                    }
                    
                elif line.startswith("http") and current_ch:
                    if current_ch['name'] not in seen_names:
                        current_ch['url'] = line
                        channels.append(current_ch)
                        seen_names.add(current_ch['name'])
                    current_ch = {} 

        except Exception as e:
            print(f"Error reading {url}: {e}")

    # ترتيب القنوات
    priority = ["Jordan TV", "Al Mamlaka", "Roya", "Al Jazeera", "MBC", "Spacetoon"]
    
    def sort_key(ch):
        for index, p in enumerate(priority):
            if p.lower() in ch['name'].lower():
                return index
        return 999 

    channels.sort(key=sort_key)

    # حفظ الملف
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)
        
    return channels # هذا هو التعديل المهم

if __name__ == "__main__":
    channels = update() # استقبال النتيجة هنا
    print(f"تمت العملية! تم جلب {len(channels)} قناة عربية.")
