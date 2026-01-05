import requests
import json
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# ⚙️ إعدادات المحرك الاستخباراتي (V11.0 - Stable)
# ==========================================
MAX_WORKERS = 25       # تم التخفيض لضمان استقرار GitHub Actions
TIMEOUT = 5            # مهلة استجابة أسرع

# تمويه المتصفح ليبدو كأنه مستخدم حقيقي
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "VLC/3.0.20 LibVLC/3.0.20",
    "IPTV Smarters Pro/4.0"
]

# كلمات مفتاحية لحجب القنوات غير اللائقة
BLACKLIST = ["adult", "xxx", "porn", "18+", "sex", "uncensored", "exotic", "hot", "brazzers"]

# ==========================================
# 📡 المصادر (تم تحديث المصادر لتكون أكثر دقة)
# ==========================================
URLS = [
    # مصادر GitHub الموثوقة
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    
    # مصادر البث المفتوح
    "https://i.mjh.nz/SamsungTVPlus/all.m3u8",
    "https://i.mjh.nz/PlutoTV/all.m3u8",
    
    # قوائم عامة (يتم تصفيتها)
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u"
]

# القنوات المستهدفة (التي نريد البحث عنها تحديداً)
TARGETS = [
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc", "abudhabi", "dubai",
    "jordan", "roya", "mamlaka", "jazeera", "alarabiya", "skynews",
    "national geo", "nat geo", "discovery", "animal planet", "spacetoon", "cartoon network",
    "cn arabia", "majid", "toyor", "mickey", "quran", "sunnah", "on time", "dmc"
]

# إصلاح الشعارات المفقودة
LOGO_FIXER = {
    "mbc1": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MBC_1_Logo.svg/512px-MBC_1_Logo.svg.png",
    "mbc2": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/MBC_2_Logo.svg/512px-MBC_2_Logo.svg.png",
    "mbcaction": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/MBC_Action_Logo.svg/512px-MBC_Action_Logo.svg.png",
    "roya": "https://upload.wikimedia.org/wikipedia/commons/7/77/Roya_TV_Logo.png",
    "almamlaka": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/AlMamlakaTV.svg/512px-AlMamlakaTV.svg.png",
    "beinsports": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/BeIN_Sports_logo.svg/512px-BeIN_Sports_logo.svg.png"
}

# ==========================================
# 🧠 المنطق البرمجي (The Engine)
# ==========================================

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

def extract_xtream_and_m3u(text):
    """استخراج روابط السيرفرات الخاصة"""
    extracted = []
    xtream_pattern = r'(http?://[a-zA-Z0-9.-]+:[0-9]+)/(?:get\.php|enigma2|m3u_plus)\?username=([a-zA-Z0-9_-]+)&password=([a-zA-Z0-9_-]+)'
    matches = re.findall(xtream_pattern, text)
    for host, user, pw in matches:
        extracted.append({
            "name": "سيرفر خاص VIP",
            "url": f"{host}/get.php?username={user}&password={pw}&type=m3u_plus&output=ts"
        })
    return extracted

def check_link(url):
    """فحص الرابط للتأكد من أنه يعمل"""
    start = time.time()
    try:
        # نستخدم verify=False لتجاهل مشاكل شهادات الأمان في بعض سيرفرات IPTV
        with requests.get(url, headers=get_headers(), stream=True, timeout=TIMEOUT, verify=False) as r:
            if r.status_code == 200:
                ct = r.headers.get('Content-Type', '').lower()
                # التأكد من أنه ملف فيديو
                if any(t in ct for t in ['video', 'mpegurl', 'stream', 'octet-stream', 'application/vnd.apple.mpegurl']):
                    return (True, time.time() - start)
    except:
        pass
    return (False, 999)

def clean_name(name):
    """تنظيف اسم القناة وتوحيده"""
    original_name = name
    name = name.lower()
    
    if any(b in name for b in BLACKLIST): return None
    
    # إزالة الكلمات الزائدة
    junk = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "live", "stream", "|", "[", "]", "(", ")", "vip", "new"]
    for w in junk: name = name.replace(w, "")
    name = re.sub(r'[^a-z0-9]', '', name)
    
    # توحيد الأسماء المشهورة
    maps = {
        "mbc1": ["mbc1", "mbcone"], 
        "mbc2": ["mbc2"], 
        "mbcaction": ["mbcaction"],
        "mbcdrama": ["mbcdrama"], 
        "roya": ["roya"], 
        "almamlaka": ["mamlaka"], 
        "jordantv": ["jordan", "aljordon"],
        "spacetoon": ["spacetoon"], 
        "beinsports": ["bein", "beinsport"], 
        "quran": ["quran", "makkah"],
        "rotanacinema": ["rotanacinema"],
        "osn": ["osn"]
    }
    
    for k, v in maps.items():
        if any(x in name for x in v): return k
    
    # إذا لم يكن اسم مشهور، أعد الاسم المنظف
    if len(name) < 2: return None
    return name

def get_cat(name, url=""):
    """تصنيف القناة تلقائياً"""
    n, u = name.lower(), url.lower()
    if "samsung" in u: return "samsung"
    if any(x in n for x in ["quran", "sunnah", "islam", "iqra", "makkah"]): return "religious"
    if any(x in n for x in ["sport", "bein", "koora", "kass", "ssc", "ad sport"]): return "sports"
    if any(x in n for x in ["news", "jazeera", "arabiya", "sky", "bbc", "cnn", "hadath"]): return "news"
    if any(x in n for x in ["kid", "cartoon", "spacetoon", "majid", "toyor", "cn"]): return "kids"
    if any(x in n for x in ["movie", "cinema", "film", "mbc2", "drama", "action", "rotana", "osn"]): return "movies"
    if any(x in n for x in ["docu", "geo", "wild", "planet", "history"]): return "docu"
    return "general"

def update():
    all_raw = []
    print("🛰️ بدء عملية المسح الشامل...")

    for url in URLS:
        try:
            print(f"جاري جلب: {url}")
            r = requests.get(url, headers=get_headers(), timeout=15, verify=False)
            r.encoding = 'utf-8' # فرض ترميز UTF-8
            text = r.text
            
            # 1. استخراج Xtream
            xtreams = extract_xtream_and_m3u(text)
            for x in xtreams: all_raw.append(x)

            # 2. استخراج M3U
            lines = text.split('\n')
            meta = {}
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # محاولة استخراج الاسم بذكاء
                    nm_match = re.search(r'tvg-name="([^"]+)"', line)
                    title_match = re.search(r',(.*)', line)
                    
                    name = nm_match.group(1).strip() if nm_match else (title_match.group(1).strip() if title_match else "Unknown")
                    
                    # استخراج الشعار
                    lg = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = lg.group(1) if lg else ""
                    
                    # حفظ البيانات مؤقتاً
                    meta = {"name": name, "logo": logo}
                
                elif line.startswith("http") and meta:
                    # فلترة سريعة: نأخذ فقط القنوات التي في قائمتنا المستهدفة أو الملفات العربية
                    if any(t in meta['name'].lower() for t in TARGETS) or "ara" in url or "jo" in url or "eg" in url or "sa" in url:
                        all_raw.append({**meta, "url": line})
                    meta = {}
        except Exception as e:
            print(f"خطأ في قراءة المصدر {url}: {e}")

    print(f"📦 تم تجميع {len(all_raw)} رابط محتمل. جاري الفحص (هذا سيستغرق وقتاً)...")

    # إزالة التكرار
    unique_entries = {}
    for item in all_raw:
        if item['url'] not in unique_entries:
            unique_entries[item['url']] = item
    
    urls_to_check = list(unique_entries.keys())
    valid_urls = {}

    # الفحص المتوازي
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = {exe.submit(check_link, u): u for u in urls_to_check}
        completed = 0
        total = len(urls_to_check)
        
        for f in as_completed(futures):
            u = futures[f]
            completed += 1
            if completed % 50 == 0: print(f"تم فحص {completed}/{total}...")
            
            try:
                ok, lat = f.result()
                if ok: valid_urls[u] = lat
            except: pass

    print(f"✅ انتهى الفحص. الروابط العاملة: {len(valid_urls)}")

    # تجميع النتائج النهائية
    final_channels = {}
    
    for url, latency in valid_urls.items():
        original_data = unique_entries[url]
        clean_id = clean_name(original_data['name'])
        
        if not clean_id: continue

        if clean_id not in final_channels:
            # تنسيق الاسم للعرض
            display_name = original_data['name'].replace('_', ' ').title()
            # إصلاحات الأسماء اليدوية
            if "Mbc" in display_name: display_name = display_name.replace("Mbc", "MBC")
            
            logo = original_data['logo']
            if (not logo or len(logo)<5) and clean_id in LOGO_FIXER:
                logo = LOGO_FIXER[clean_id]

            final_channels[clean_id] = {
                "name": display_name,
                "logo": logo,
                "category": get_cat(display_name, url),
                "urls_list": []
            }
        
        final_channels[clean_id]['urls_list'].append({"u": url, "l": latency})

    # بناء ملف JSON
    output_list = []
    for cid, data in final_channels.items():
        # ترتيب الروابط حسب السرعة
        sorted_links = sorted(data['urls_list'], key=lambda x: x['l'])
        output_list.append({
            "name": data['name'],
            "logo": data['logo'],
            "category": data['category'],
            "urls": [x['u'] for x in sorted_links]
        })

    # ترتيب القنوات: الأردنية أولاً، ثم MBC، ثم البقية
    def sort_prio(chan):
        n = chan['name'].lower()
        if "jordan" in n or "roya" in n or "mamlaka" in n: return 1
        if "mbc" in n: return 2
        if "bein" in n: return 3
        if "news" in n: return 4
        return 10

    output_list.sort(key=sort_prio)

    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(output_list, f, ensure_ascii=False, indent=2)

    print("تم حفظ التحديث بنجاح.")

if __name__ == "__main__":
    update()
