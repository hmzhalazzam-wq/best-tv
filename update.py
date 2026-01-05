import requests
import json
import re

# مصادر القنوات (أردن، عربي عام)
URLS = [
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u"
]

# قائمة القنوات التي نريدها فقط (لتجنب القنوات غير المرغوبة)
WANTED = {
    "Jordan TV": "general", "Roya": "general", "Al Mamlaka": "news", 
    "Al Jazeera": "news", "Al Arabiya": "news", "Sky News Arabia": "news",
    "Rotana Cinema": "movies", "Rotana Classic": "movies", "MBC 2": "movies",
    "Spacetoon": "kids", "Majid Kids": "kids", "Cartoon Network Arabic": "kids",
    "beIN Sports News": "sports", "AD Sports 1": "sports", "Dubai Sports 1": "sports"
}

def update():
    channels = []
    seen_urls = set() # لمنع تكرار الروابط

    print("جاري سحب القنوات وتصنيفها...")
    
    for url in URLS:
        try:
            content = requests.get(url).text
            lines = content.split('\n')
            current_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # محاولة استخراج الاسم والشعار
                    # البحث عن الاسم
                    name_match = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    # البحث عن الشعار
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    
                    if name_match:
                        raw_name = name_match.group(1).strip() if name_match.group(1) else "Unknown"
                        # التحقق هل القناة في قائمة المطلوب؟
                        for wanted_name, category in WANTED.items():
                            if wanted_name.lower() in raw_name.lower():
                                current_info = {
                                    "name": wanted_name,
                                    "logo": logo_match.group(1) if logo_match else "",
                                    "category": category
                                }
                                break
                        else:
                            current_info = {} # قناة غير مطلوبة
                            
                elif line.startswith("http") and current_info:
                    if line not in seen_urls:
                        # إضافة القناة للقائمة النهائية
                        channels.append({
                            "name": current_info['name'],
                            "logo": current_info['logo'],
                            "category": current_info['category'],
                            "url": line
                        })
                        seen_urls.add(line)
                    current_info = {} # تصفير
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            
    # حفظ الملف
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(channels, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update()
    print(f"تم تحديث {len(channels)} قناة بنجاح!")
