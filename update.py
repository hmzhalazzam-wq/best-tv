import requests
import json
import re

# ==========================================
# مصادر مرتبة حسب "الثقة" (الأول هو الأصدق)
# ==========================================
SOURCES = [
    # 1. القوائم الرسمية للدول (لحل مشكلة تداخل القنوات)
    {"url": "https://iptv-org.github.io/iptv/countries/jo.m3u", "tag": "official"}, # الأردن
    {"url": "https://iptv-org.github.io/iptv/countries/eg.m3u", "tag": "official"}, # مصر (لحل مشكلة القناة الثانية)
    {"url": "https://iptv-org.github.io/iptv/countries/sa.m3u", "tag": "official"}, # السعودية
    {"url": "https://iptv-org.github.io/iptv/countries/ae.m3u", "tag": "official"}, # الإمارات
    {"url": "https://iptv-org.github.io/iptv/countries/qa.m3u", "tag": "official"}, # قطر
    
    # 2. القائمة العربية العامة
    {"url": "https://iptv-org.github.io/iptv/languages/ara.m3u", "tag": "general"},
    
    # 3. قوائم عالمية (وثائقي، أطفال، رياضة)
    {"url": "https://iptv-org.github.io/iptv/categories/documentary.m3u", "tag": "global"},
    {"url": "https://iptv-org.github.io/iptv/categories/kids.m3u", "tag": "global"},
    {"url": "https://iptv-org.github.io/iptv/categories/sports.m3u", "tag": "global"}
]

# كلمات مفتاحية للقنوات العالمية التي نريد التقاطها
GLOBAL_WANTED = ["national geo", "nat geo", "discovery", "animal planet", "investigation", "cartoon network", "disney", "beinsports"]

def clean_name(name):
    """تنظيف الاسم بدقة لمنع التشابه"""
    name = name.lower()
    # إزالة الجودة والكلمات الزائدة
    for w in ["hd", "sd", "fhd", "4k", "hevc", "tv", "channel", "live", "ar", "arabic"]:
        name = re.sub(rf'\b{w}\b', '', name)
    return re.sub(r'[^a-z0-9]', '', name) # إزالة الرموز

def get_cat(name, group):
    text = (name + " " + group).lower()
    if "sport" in text or "koora" in text: return "sports"
    if "news" in text or "jazeera" in text or "arabia" in text: return "news"
    if "kid" in text or "cartoon" in text or "spacetoon" in text: return "kids"
    if "movi" in text or "cinema" in text or "film" in text or "rotana" in text: return "movies"
    if "docu" in text or "geo" in text or "wild" in text: return "docu"
    if "relig" in text or "qura" in text: return "religious"
    return "general"

def update():
    channels_map = {}
    print("🚀 بدء المعالجة الذكية...")

    for source in SOURCES:
        try:
            url = source['url']
            tag = source['tag']
            print(f"📡 فحص: {url}")
            
            resp = requests.get(url, timeout=15)
            resp.encoding = 'utf-8'
            lines = resp.text.split('\n')
            
            current = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # استخراج البيانات
                    name_m = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    raw_name = name_m.group(1).strip() if name_m else "Unknown"
                    
                    logo_m = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_m.group(1) if logo_m else ""
                    
                    group_m = re.search(r'group-title="([^"]+)"', line)
                    group = group_m.group(1).lower() if group_m else ""

                    # --- الفلتر الذكي ---
                    should_add = False
                    
                    # 1. إذا المصدر رسمي (دولة عربية)، خذ القناة فوراً
                    if tag == "official":
                        should_add = True
                    # 2. إذا المصدر عام، خذها
                    elif tag == "general":
                        should_add = True
                    # 3. إذا المصدر عالمي، ابحث عن الكلمات المفتاحية
                    elif tag == "global":
                        if any(k in raw_name.lower() for k in GLOBAL_WANTED):
                            should_add = True

                    if should_add:
                        current = {
                            "name": raw_name,
                            "logo": logo,
                            "group": group,
                            "tag": tag
                        }
                    else:
                        current = {}

                elif line.startswith("http") and current:
                    # مفتاح القناة الفريد
                    # إذا كانت القناة من قائمة مصر، نضيف "eg" للاسم لتمييزها عن غيرها
                    clean_id = clean_name(current['name'])
                    
                    # تمييز القنوات المحلية لحل مشكلة "القناة الثانية"
                    if "channel2" in clean_id or "alula" in clean_id:
                        if "eg" in url: clean_id += "eg"
                        elif "sa" in url: clean_id += "sa"

                    if clean_id not in channels_map:
                        cat = get_cat(current['name'], current['group'])
                        
                        # تحسين الاسم
                        disp_name = current['name']
                        if "eg" in url and "Channel 1" in disp_name: disp_name = "القناة الأولى المصرية"
                        if "eg" in url and "Channel 2" in disp_name: disp_name = "القناة الثانية المصرية"

                        channels_map[clean_id] = {
                            "name": disp_name,
                            "logo": current['logo'],
                            "category": cat,
                            "urls": [],
                            "priority": 0 # نقاط الأولوية
                        }

                    # إضافة الرابط
                    if line not in channels_map[clean_id]['urls']:
                        # إذا القناة من مصدر رسمي، نضع الرابط في البداية
                        if current['tag'] == "official":
                             channels_map[clean_id]['urls'].insert(0, line)
                             # تحديث الشعار إذا كان من مصدر رسمي (غالباً أدق)
                             if current['logo']:
                                 channels_map[clean_id]['logo'] = current['logo']
                        else:
                             channels_map[clean_id]['urls'].append(line)

                    current = {}

        except Exception as e:
            print(f"Error: {e}")

    # تحويل ومراجعة
    final = list(channels_map.values())
    final = [c for c in final if len(c['urls']) > 0]
    
    # ترتيب: القنوات التي تحتوي على كلمات عربية أولاً
    def sort_key(c):
        priority_names = ["jordan", "mamlaka", "roya", "mbc", "jazeera", "bein", "rotana"]
        name = c['name'].lower()
        for i, p in enumerate(priority_names):
            if p in name: return i
        return 100

    final.sort(key=sort_key)
    
    print(f"✅ تم جمع {len(final)} قناة.")

    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update()
