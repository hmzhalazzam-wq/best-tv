import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 1. المصادر العملاقة (المستودعات الذكية)
# ==========================================
URLS = [
    # قوائم رسمية (لضمان الجودة)
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    
    # قوائم ضخمة جداً (للبحث عن Xtream و القنوات المشفرة المفتوحة)
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    
    # قوائم عالمية (سنبحث بداخلها عن قنوات محددة)
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u"
]

# الكلمات المفتاحية للقنوات التي نريد "صيدها" من القوائم العالمية
TARGETS = [
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc",
    "national geo", "nat geo", "discovery", "animal planet",
    "spacetoon", "cartoon network", "cn arabia", "nickelodeon",
    "jordan", "roya", "mamlaka", "jazeera", "alarabiya"
]

# ==========================================
# 2. إعدادات الفحص (المحرك)
# ==========================================
MAX_WORKERS = 30  # عدد الروبوتات الصغيرة التي تفحص في نفس الوقت (لزيادة السرعة)
TIMEOUT = 4       # مدة الصبر على الرابط قبل اعتباره ميتاً (ثواني)

# تمويه الطلب (وكأنه متصفح حقيقي)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 3. الوظائف الذكية
# ==========================================

def check_stream(url):
    """وظيفة فحص الرابط: هل يعمل أم لا؟"""
    try:
        # طلب خفيف (Stream) دون تحميل الفيديو كاملاً
        with requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT) as r:
            # نقبل الرابط إذا كان الكود 200 (OK) وكان المحتوى فيديو
            if r.status_code == 200:
                return True
    except:
        return False
    return False

def clean_name(name):
    """تنظيف وتوحيد أسماء القنوات"""
    name = name.lower()
    # إزالة الكلمات الزائدة
    for w in ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "channel", "live", "stream", "+"]:
        name = name.replace(w, "")
    # إزالة الرموز
    name = re.sub(r'[^a-z0-9]', '', name)
    
    # توحيد الأسماء المشهورة
    if "mbc" in name:
        if "drama" in name: return "mbcdrama"
        if "action" in name: return "mbcaction"
        if "2" in name: return "mbc2"
        if "3" in name: return "mbc3"
        if "4" in name: return "mbc4"
        if "masr" in name: return "mbcmasr"
        if "iraq" in name: return "mbciraq"
        if "booly" in name: return "mbcbollywood"
    
    if "national" in name or "nat" in name: return "natgeo"
    if "jordan" in name: return "jordantv"
    
    return name

def get_cat(name):
    n = name.lower()
    if "sport" in n or "koora" in n or "bein" in n: return "sports"
    if "news" in n or "jazeera" in n or "arabia" in n: return "news"
    if "kid" in n or "cartoon" in n or "spacetoon" in n: return "kids"
    if "movi" in n or "cinema" in n or "film" in n or "rotana" in n or "mbc 2" in n: return "movies"
    if "docu" in n or "geo" in n or "wild" in n or "planet" in n: return "docu"
    return "general"

# ==========================================
# 4. المحرك الرئيسي
# ==========================================
def update():
    all_candidates = []
    print("📡 جاري سحب القوائم الضخمة والبحث عن القنوات...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            resp.encoding = 'utf-8'
            lines = resp.text.split('\n')
            
            meta = {}
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # استخراج البيانات
                    name_m = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    name = name_m.group(1).strip() if name_m else "Unknown"
                    
                    logo_m = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_m.group(1) if logo_m else ""
                    
                    # هل القناة عربية أو من القنوات المستهدفة؟
                    is_arab_source = "ara.m3u" in url or "jo.m3u" in url or "eg.m3u" in url or "sa.m3u" in url
                    is_target = any(t in name.lower() for t in TARGETS)
                    
                    if is_arab_source or is_target:
                        meta = {"name": name, "logo": logo}
                    else:
                        meta = {} # تجاهل القنوات غير المهمة
                        
                elif line.startswith("http") and meta:
                    if not line.endswith(".ts"): # نتجنب ملفات التقطيع الصغيرة
                        all_candidates.append({
                            "name": meta['name'],
                            "logo": meta['logo'],
                            "url": line
                        })
                    meta = {}
        except Exception as e:
            print(f"⚠️ خطأ في المصدر {url}: {e}")

    print(f"📦 وجدنا {len(all_candidates)} رابط محتمل. بدء الفحص الذكي (هذا سيأخذ وقتاً)...")

    # تجميع الروابط الفريدة للفحص (لعدم فحص نفس الرابط مرتين)
    unique_links = set(c['url'] for c in all_candidates)
    working_links = set()

    # --- الفحص المتوازي (Multi-threading) ---
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_stream, url): url for url in unique_links}
        
        checked_count = 0
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            checked_count += 1
            if checked_count % 50 == 0: print(f"⏳ تم فحص {checked_count}/{len(unique_links)}...")
            
            try:
                if future.result():
                    working_links.add(url)
            except:
                pass

    print(f"✅ انتهى الفحص. الروابط العاملة فعلياً: {len(working_links)}")

    # بناء القائمة النهائية
    final_channels = {}
    
    for item in all_candidates:
        if item['url'] in working_links:
            cid = clean_name(item['name'])
            
            if cid not in final_channels:
                final_channels[cid] = {
                    "name": item['name'],
                    "logo": item['logo'],
                    "category": get_category(item['name']),
                    "urls": []
                }
            
            # إضافة الرابط للقناة
            if item['url'] not in final_channels[cid]['urls']:
                final_channels[cid]['urls'].append(item['url'])
                # تحديث اللوجو إذا كان القديم فارغاً
                if not final_channels[cid]['logo'] and item['logo']:
                    final_channels[cid]['logo'] = item['logo']

    # تحويل لقائمة وترتيب
    output_list = list(final_channels.values())
    
    # تنظيف القنوات بدون روابط (احتياط)
    output_list = [c for c in output_list if c['urls']]

    # ترتيب الأولويات
    priority = ["Jordan", "Roya", "Mamlaka", "MBC", "Jazeera", "BeIN", "Nat Geo"]
    def sort_logic(c):
        n = c['name'].lower()
        for i, p in enumerate(priority):
            if p.lower() in n: return i
        return 100

    output_list.sort(key=sort_logic)

    print(f"🎉 تم حفظ {len(output_list)} قناة مؤكدة.")
    
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(output_list, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update()
