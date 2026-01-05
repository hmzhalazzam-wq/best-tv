import requests
import json
import re

# ==========================================
# 1. قائمة المصادر العملاقة (المستودعات)
# ==========================================
SOURCES = [
    # القنوات العربية والأردنية (الأساس)
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    
    # القنوات الوثائقية العالمية (للبحث عن Nat Geo)
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    
    # قنوات الأطفال والأفلام العالمية
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/family.m3u",
    
    # قوائم خدمات البث العالمية (Samsung TV Plus, Pluto, etc)
    # هذه القوائم تحتوي على قنوات عالية الجودة ومجانية
    "https://iptv-org.github.io/iptv/index.m3u" 
]

# ==========================================
# 2. الكلمات المفتاحية للبحث (صائد القنوات)
# ==========================================
# سنبحث عن هذه الكلمات في القوائم العالمية حتى لو لم تكن عربية
IMPORTANT_KEYWORDS = [
    "national geographic", "nat geo", "wild", "adventure", # وثائقيات
    "mbc", "shahid", "rotana", "art ",                   # ترفيه عربي
    "beinsports", "alkass", "ad sports", "ssc",          # رياضة
    "samsung", "xumo", "pluto",                          # منصات عالمية
    "spacetoon", "cartoon network", "nickelodeon"        # أطفال
]

# ==========================================
# 3. الخوارزمية الذكية
# ==========================================

def normalize_name(name):
    """توحيد الأسماء لدمج المتشابهات"""
    name = name.lower()
    # إزالة الزوائد مثل HD, FHD, 4K, TV
    replacements = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "channel", "live"]
    for word in replacements:
        name = name.replace(word, "")
    
    # توحيد التسميات المشهورة
    if "national geographic" in name: name = "nat geo"
    if "mbc" in name and "drama" in name: name = "mbc drama"
    if "mbc" in name and "action" in name: name = "mbc action"
    if "mbc" in name and "2" in name: name = "mbc 2"
    if "mbc" in name and "3" in name: name = "mbc 3"
    if "mbc" in name and "4" in name: name = "mbc 4"
    if "jordan" in name: name = "jordan tv"
    
    # إزالة الرموز
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def get_category(name, group):
    """تحديد التصنيف تلقائياً بناءً على الاسم"""
    text = (name + " " + group).lower()
    
    if "sport" in text or "ball" in text or "koora" in text: return "sports"
    if "news" in text or "arabia" in text or "jazeera" in text: return "news"
    if "kid" in text or "cartoon" in text or "anime" in text or "spacetoon" in text: return "kids"
    if "movi" in text or "cinema" in text or "film" in text or "drama" in text or "rotana" in text: return "movies"
    if "docu" in text or "geo" in text or "wild" in text or "planet" in text: return "docu"
    if "relig" in text or "qura" in text or "sunna" in text: return "religious"
    
    return "general"

def update():
    channels_map = {}
    print("🚀 بدء تشغيل المحرك الذكي للبحث في آلاف القنوات...")

    for url in SOURCES:
        try:
            print(f"📡 جاري المسح: {url} ...")
            # نستخدم timeout قصير لتجاوز القوائم البطيئة
            response = requests.get(url, timeout=15)
            response.encoding = 'utf-8'
            lines = response.text.split('\n')
            
            current_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # استخراج البيانات
                    name_match = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    raw_name = name_match.group(1).strip() if name_match else "Unknown"
                    
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_match.group(1) if logo_match else ""
                    
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    group = group_match.group(1).lower() if group_match else ""
                    
                    # --- الفلتر الذكي ---
                    # نقبل القناة في حالتين:
                    # 1. القائمة هي قائمة عربية (ara.m3u أو jo.m3u)
                    # 2. القائمة عالمية، ولكن اسم القناة يحتوي على كلمة مهمة (مثل Nat Geo)
                    
                    is_target = False
                    
                    if "ara.m3u" in url or "jo.m3u" in url:
                        is_target = True
                    else:
                        # بحث في القوائم العالمية عن الكلمات المهمة
                        for keyword in IMPORTANT_KEYWORDS:
                            if keyword in raw_name.lower():
                                is_target = True
                                break
                    
                    if is_target:
                        current_info = {
                            "name": raw_name,
                            "logo": logo,
                            "group": group
                        }
                    else:
                        current_info = {} # تجاهل هذه القناة
                        
                elif line.startswith("http") and current_info:
                    # معالجة القناة المقبولة
                    clean_id = normalize_name(current_info['name'])
                    
                    if clean_id not in channels_map:
                        # قناة جديدة
                        cat = get_category(current_info['name'], current_info['group'])
                        
                        # تحسين الاسم للعرض (Capitalize)
                        display_name = current_info['name']
                        if "mbc" in clean_id: display_name = display_name.upper()
                        
                        channels_map[clean_id] = {
                            "name": display_name,
                            "logo": current_info['logo'],
                            "category": cat,
                            "urls": []
                        }
                    
                    # إضافة الرابط (إذا لم يكن مكرراً)
                    if line not in channels_map[clean_id]['urls']:
                        channels_map[clean_id]['urls'].append(line)
                        
                    current_info = {}

        except Exception as e:
            print(f"⚠️ تجاوز المصدر {url} بسبب خطأ: {e}")

    # تحويل القاموس لقائمة
    final_list = list(channels_map.values())
    
    # تنظيف القنوات التي ليس لها روابط
    final_list = [ch for ch in final_list if len(ch['urls']) > 0]
    
    # --- ترتيب الأولويات للعرض ---
    # نريد القنوات الأردنية والعربية الكبرى في المقدمة
    priority_words = ["Jordan", "Roya", "Mamlaka", "Jazeera", "MBC", "BeIN", "National Geo", "Rotana"]
    
    def sort_score(ch):
        name = ch['name'].lower()
        for index, word in enumerate(priority_words):
            if word.lower() in name:
                return index # كلما كان الرقم أقل، ظهرت أولاً
        return 100 # القنوات الأخرى تأتي لاحقاً
        
    final_list.sort(key=sort_score)

    print(f"✅ تم الانتهاء! تم تجميع {len(final_list)} قناة، وتم دمج الروابط المتشابهة.")

    # حفظ الملف
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    return final_list

if __name__ == "__main__":
    update()
