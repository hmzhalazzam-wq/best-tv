import requests
import json
import re

# مصادر ضخمة (عربي، أردني، قنوات دولية، وقنوات رياضية)
SOURCES = [
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/categories/news.m3u",   # أخبار عالمية
    "https://iptv-org.github.io/iptv/categories/movies.m3u" # أفلام عالمية
]

# دالة ذكية لتوحيد الأسماء (مثلاً: MBC 2 HD تصبح mbc2)
def normalize_name(name):
    name = name.lower()
    # إزالة الكلمات الزائدة لضمان التطابق
    for word in ["hd", "sd", "fhd", "4k", "tv", "live", "channel", "ar", "arabic"]:
        name = name.replace(word, "")
    # إزالة الرموز والمسافات
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def update():
    channels_map = {} # القاموس الذكي لدمج القنوات
    print("🚀 جاري تشغيل الخوارزمية الذكية لجلب القنوات...")

    for url in SOURCES:
        try:
            print(f"🔍 فحص المصدر: {url}")
            resp = requests.get(url, timeout=10)
            resp.encoding = 'utf-8'
            lines = resp.text.split('\n')
            
            current_info = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # استخراج الاسم الخام
                    name_match = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    raw_name = name_match.group(1).strip() if name_match else "Unknown"
                    
                    # استخراج الشعار
                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_match.group(1) if logo_match else ""
                    
                    # استخراج التصنيف
                    group_match = re.search(r'group-title="([^"]+)"', line)
                    group = group_match.group(1).lower() if group_match else "other"
                    
                    # الفلترة الذكية: نقبل القناة فقط إذا كانت عربية أو من المصادر العربية
                    # أو إذا كان اسمها يحتوي على كلمات عربية
                    is_arabic_source = "ara.m3u" in url or "jo.m3u" in url
                    
                    current_info = {
                        "raw_name": raw_name,
                        "logo": logo,
                        "group": group,
                        "is_valid": is_arabic_source # مبدئياً
                    }
                    
                elif line.startswith("http") and current_info:
                    # التحقق الإضافي للقنوات من مصادر عالمية (يجب أن تكون عربية)
                    if not current_info['is_valid']:
                        # إذا المصدر أجنبي، نفحص هل القناة عربية؟
                        if "arab" in current_info['raw_name'].lower() or "al " in current_info['raw_name'].lower():
                            current_info['is_valid'] = True

                    if current_info['is_valid']:
                        # التطبيع: تحويل الاسم لصيغة موحدة للكشف عن التكرار
                        clean_id = normalize_name(current_info['raw_name'])
                        
                        if clean_id not in channels_map:
                            # قناة جديدة
                            # تحديد التصنيف
                            cat = "general"
                            g = current_info['group'] + " " + current_info['raw_name'].lower()
                            if "sport" in g: cat = "sports"
                            elif "news" in g: cat = "news"
                            elif "kid" in g or "cartoon" in g: cat = "kids"
                            elif "movi" in g or "cinema" in g or "film" in g: cat = "movies"
                            elif "relig" in g or "qura" in g: cat = "religious"
                            
                            channels_map[clean_id] = {
                                "name": current_info['raw_name'], # نحتفظ بأول اسم وجدناه
                                "logo": current_info['logo'],
                                "category": cat,
                                "urls": [] # قائمة الروابط (نظام النسخ الاحتياطي)
                            }
                        
                        # إضافة الرابط للقائمة (إذا لم يكن موجوداً)
                        if line not in channels_map[clean_id]['urls']:
                            channels_map[clean_id]['urls'].append(line)
                            
                    current_info = {}

        except Exception as e:
            print(f"❌ خطأ في المصدر {url}: {e}")

    # تحويل القاموس إلى قائمة
    final_list = list(channels_map.values())
    
    # تنظيف القنوات التي ليس لها شعار أو التي تبدو وهمية
    final_list = [ch for ch in final_list if len(ch['urls']) > 0]

    # ترتيب الأولويات
    priority = ["Jordan", "Roya", "Mamlaka", "Jazeera", "MBC", "BeIN", "Abu Dhabi", "Rotana"]
    def sort_logic(ch):
        name = ch['name'].lower()
        for i, p in enumerate(priority):
            if p.lower() in name:
                return i
        return 100
        
    final_list.sort(key=sort_logic)

    print(f"✅ تم الانتهاء! دمجنا القنوات في {len(final_list)} قناة فريدة.")
    
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
        
    return final_list

if __name__ == "__main__":
    update()
