import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 1. المصادر الذكية (Smart Sources)
# ==========================================
# قمنا بإضافة مصادر تتجدد يومياً وتحتوي على سيرفرات Xtream محولة
URLS = [
    # المصادر الرسمية (قاعدة بيانات صلبة)
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    
    # مصادر عالمية ضخمة (قد تحتوي على MBC وسيرفرات خاصة)
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u",
    
    # مصادر القنوات العالمية (وثائقي، أطفال، رياضة)
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u"
]

# القنوات التي نريد التركيز عليها (VIP)
TARGET_CHANNELS = [
    "mbc", "bein", "osn", "rotana", "art ", "shahid", 
    "national geo", "nat geo", "discovery", "animal planet",
    "spacetoon", "cartoon network", "cn arabia",
    "jordan", "roya", "mamlaka", "jazeera"
]

# ==========================================
# 2. إعدادات الفحص الذكي
# ==========================================
# عدد المحاولات المتزامنة (كلما زاد الرقم زادت السرعة لكن زاد الضغط)
MAX_THREADS = 20 
# مهلة الانتظار قبل اعتبار الرابط ميتاً (ثواني)
TIMEOUT = 4

# هيدر لتمويه الطلب وكأنه متصفح حقيقي (لتجاوز الحماية)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# ==========================================
# 3. الوظائف الذكية
# ==========================================

def check_link(url):
    """
    وظيفة تقوم بفحص الرابط هل هو حي أم ميت؟
    ترجع True إذا كان الرابط شغال، و False إذا خربان.
    """
    try:
        # نرسل طلب HEAD (خفيف جداً) أو GET لأول بايتات فقط
        with requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT) as response:
            if response.status_code == 200:
                return True
    except:
        return False
    return False

def clean_name(name):
    """تنظيف الاسم لتوحيد القنوات"""
    name = name.lower()
    # إزالة الكلمات التي لا تؤثر في هوية القناة
    replacements = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "channel", "live", "stream"]
    for word in replacements:
        name = re.sub(rf'\b{word}\b', '', name)
    return re.sub(r'[^a-z0-9]', '', name)

def get_category(name):
    """تحديد نوع القناة ذكياً"""
    n = name.lower()
    if "sport" in n or "koora" in n or "bein" in n: return "sports"
    if "news" in n or "jazeera" in n or "arabia" in n: return "news"
    if "kid" in n or "cartoon" in n or "spacetoon" in n: return "kids"
    if "movi" in n or "cinema" in n or "film" in n or "rotana" in n or "mbc 2" in n or "mbc action" in n: return "movies"
    if "docu" in n or "geo" in n or "wild" in n or "planet" in n: return "docu"
    return "general"

def fetch_all_channels():
    """جلب القنوات من جميع المصادر وتصفيتها مبدئياً"""
    raw_channels = []
    print("📡 جاري سحب القوائم الضخمة...")
    
    for url in URLS:
        try:
            resp = requests.get(url, timeout=10)
            resp.encoding = 'utf-8'
            lines = resp.text.split('\n')
            
            current_meta = {}
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # استخراج الاسم
                    name_m = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    name = name_m.group(1).strip() if name_m else "Unknown"
                    
                    # استخراج اللوجو
                    logo_m = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_m.group(1) if logo_m else ""
                    
                    # هل القناة من القنوات المستهدفة؟
                    is_target = any(k in name.lower() for k in TARGET_CHANNELS)
                    
                    # إذا القائمة عربية خذ كل شيء، إذا عالمية خذ فقط المستهدف
                    if "ara.m3u" in url or "jo.m3u" in url or "arab" in url or is_target:
                        current_meta = {"name": name, "logo": logo}
                    else:
                        current_meta = {}
                        
                elif line.startswith("http") and current_meta:
                    if not line.endswith(".ts"): # نتجنب ملفات ts القصيرة ونركز على m3u8
                        raw_channels.append({
                            "name": current_meta['name'],
                            "logo": current_meta['logo'],
                            "url": line
                        })
                    current_meta = {}
        except Exception as e:
            print(f"⚠️ خطأ في المصدر {url}: {e}")
            
    return raw_channels

# ==========================================
# 4. المحرك الرئيسي (Main Engine)
# ==========================================

def update():
    all_raw = fetch_all_channels()
    print(f"📦 تم جمع {len(all_raw)} رابط محتمل. البدء في الفحص الذكي (قد يستغرق وقتاً)...")
    
    # تجميع القنوات حسب الاسم
    grouped_channels = {}
    
    # 1. التجميع أولاً لتقليل عدد مرات الفحص (اذا الرابط مكرر)
    unique_urls_to_check = set()
    
    for ch in all_raw:
        clean_id = clean_name(ch['name'])
        
        # تصحيح خاص لـ MBC
        if "mbc" in clean_id:
            if "drama" in clean_id: clean_id = "mbcdrama"
            elif "action" in clean_id: clean_id = "mbcaction"
            elif "max" in clean_id: clean_id = "mbcmax"
            elif "bollywood" in clean_id: clean_id = "mbcbollywood"
            elif "2" in clean_id: clean_id = "mbc2"
            elif "3" in clean_id: clean_id = "mbc3"
            elif "4" in clean_id: clean_id = "mbc4"
            elif "iraq" in clean_id: clean_id = "mbciraq"
            elif "masr" in clean_id: clean_id = "mbcmasr"
        
        if clean_id not in grouped_channels:
            grouped_channels[clean_id] = {
                "name": ch['name'],
                "logo": ch['logo'],
                "category": get_category(ch['name']),
                "potential_urls": set()
            }
        
        grouped_channels[clean_id]['potential_urls'].add(ch['url'])
        unique_urls_to_check.add(ch['url'])

    print(f"🔍 لدينا {len(unique_urls_to_check)} رابط فريد للفحص. تشغيل التيربو...")

    # 2. الفحص المتوازي (Multi-threading Link Checker)
    valid_urls = set()
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # إرسال المهام
        future_to_url = {executor.submit(check_link, url): url for url in unique_urls_to_check}
        
        completed = 0
        total = len(unique_urls_to_check)
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            completed += 1
            if completed % 50 == 0: print(f"⏳ تم فحص {completed}/{total}...")
            
            try:
                is_working = future.result()
                if is_working:
                    valid_urls.add(url)
            except:
                pass

    print(f"✅ انتهى الفحص. الروابط الشغالة: {len(valid_urls)}")

    # 3. بناء القائمة النهائية
    final_list = []
    
    for key, data in grouped_channels.items():
        # نأخذ فقط الروابط التي نجحت في الاختبار
        working_urls = [u for u in data['potential_urls'] if u in valid_urls]
        
        if working_urls:
            # ترتيب الأولويات: الروابط الرسمية أولاً
            official_urls = [u for u in working_urls if "shahid" in u or "viaplay" in u]
            other_urls = [u for u in working_urls if u not in official_urls]
            sorted_urls = official_urls + other_urls
            
            final_list.append({
                "name": data['name'],
                "logo": data['logo'],
                "category": data['category'],
                "urls": sorted_urls
            })

    # ترتيب نهائي للعرض (الأردنية والعربية المهمة في المقدمة)
    priority = ["Jordan", "Roya", "Mamlaka", "MBC", "Jazeera", "BeIN", "Nat Geo"]
    def sort_key(item):
        n = item['name'].lower()
        for i, p in enumerate(priority):
            if p.lower() in n: return i
        return 100

    final_list.sort(key=sort_key)

    # الحفظ
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(final_list, f, ensure_ascii=False, indent=2)
    
    print(f"🎉 تم حفظ {len(final_list)} قناة مؤكدة العمل 100%!")

if __name__ == "__main__":
    update()
