import requests
import json
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# ⚙️ إعدادات المحرك الاستخباراتي (V10.0 - Final)
# ==========================================
MAX_WORKERS = 100      # سرعة فحص فائقة
TIMEOUT = 7           # مهلة فحص متوازنة

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "OTT-Player/1.1 (Linux; tvOS 13.4) AppleWebkit/605.1.15",
    "VLC/3.0.18 LibVLC/3.0.18",
    "IPTV Smarters Pro/3.1.5"
]

BLACKLIST = ["adult", "xxx", "porn", "18+", "sex", "uncensored", "exotic"]

# ==========================================
# 📡 المصادر الشاملة (GitHub, GitLab, Pastebin, Gist, Forums)
# ==========================================
URLS = [
    # --- مستودعات GitHub ---
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u",
    
    # --- مصادر مخفية (GitLab, Gist, Pastebin) ---
    "https://gitlab.com/kh_m_m/iptv/-/raw/master/arabic.m3u",
    "https://gist.githubusercontent.com/Youssef-Aroub/c0f82d0b67a29e4b7e9c5c0c8b0e5d1a/raw/arabic.m3u",
    "https://pastebin.com/raw/88uK1VzD", # مثال لقائمة متجددة
    
    # --- منصات البث العالمية (Samsung, Pluto) ---
    "https://i.mjh.nz/SamsungTVPlus/all.m3u8",
    "https://i.mjh.nz/PlutoTV/all.m3u8",
    
    # --- فئات وثائقية ورياضية ---
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u"
]

TARGETS = [
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc", "abudhabi", "dubai",
    "jordan", "roya", "mamlaka", "jazeera", "alarabiya", "skynews",
    "national geo", "nat geo", "discovery", "animal planet", "spacetoon", "cartoon network",
    "cn arabia", "majid", "toyor", "mickey", "quran", "sunnah"
]

# شعارات عالية الجودة
LOGO_FIXER = {
    "mbc1": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MBC_1_Logo.svg/512px-MBC_1_Logo.svg.png",
    "mbc2": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/MBC_2_Logo.svg/512px-MBC_2_Logo.svg.png",
    "mbc3": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/MBC_3_Logo.svg/512px-MBC_3_Logo.svg.png",
    "mbcaction": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/MBC_Action_Logo.svg/512px-MBC_Action_Logo.svg.png",
    "roya": "https://upload.wikimedia.org/wikipedia/commons/7/77/Roya_TV_Logo.png",
    "almamlaka": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/AlMamlakaTV.svg/512px-AlMamlakaTV.svg.png",
    "jordantv": "https://upload.wikimedia.org/wikipedia/en/2/22/Jordan_Radio_and_Television_Corporation_logo.png",
    "spacetoon": "https://upload.wikimedia.org/wikipedia/ar/d/d4/Spacetoon_logo_2015.png",
    "natgeo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/National_Geographic_Logo.svg/512px-National_Geographic_Logo.svg.png",
    "beinsports": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/BeIN_Sports_logo.svg/512px-BeIN_Sports_logo.svg.png"
}

# ==========================================
# 🧠 المنطق المتقدم (The Brain)
# ==========================================

def extract_xtream_and_m3u(text):
    """استخراج الروابط المباشرة وروابط Xtream المخفية"""
    extracted = []
    # البحث عن نمط Xtream (Host, Port, User, Pass)
    xtream_pattern = r'(http?://[a-zA-Z0-9.-]+:[0-9]+)/(?:get\.php|enigma2|m3u_plus)\?username=([a-zA-Z0-9_-]+)&password=([a-zA-Z0-9_-]+)'
    matches = re.findall(xtream_pattern, text)
    for host, user, pw in matches:
        extracted.append({
            "name": "سيرفر خاص",
            "url": f"{host}/get.php?username={user}&password={pw}&type=m3u_plus&output=ts"
        })
    return extracted

def check_link(url):
    """فحص حي للرابط مع قياس زمن الاستجابة"""
    start = time.time()
    try:
        h = {"User-Agent": random.choice(USER_AGENTS)}
        # نستخدم HEAD للفحص السريع
        with requests.get(url, headers=h, stream=True, timeout=TIMEOUT) as r:
            if r.status_code == 200:
                ct = r.headers.get('Content-Type', '').lower()
                if any(t in ct for t in ['video', 'mpegurl', 'stream', 'octet-stream']):
                    return (True, time.time() - start)
    except: pass
    return (False, 999)

def clean_name(name):
    name = name.lower()
    if any(b in name for b in BLACKLIST): return None
    junk = ["hd", "sd", "fhd", "4k", "ar", "arabic", "tv", "live", "stream", "|", "[", "]", "(", ")"]
    for w in junk: name = name.replace(w, "")
    name = re.sub(r'[^a-z0-9]', '', name)
    
    maps = {
        "mbc1": ["mbc1", "mbcone"], "mbc2": ["mbc2"], "mbc3": ["mbc3"], "mbcaction": ["mbcaction"],
        "mbcdrama": ["mbcdrama"], "mbcmax": ["mbcmax"], "natgeo": ["natgeo", "nationalgeo"],
        "roya": ["roya"], "almamlaka": ["mamlaka"], "jordantv": ["jordan", "aljordon"],
        "spacetoon": ["spacetoon"], "beinsports": ["bein"], "quran": ["quran", "makkah"]
    }
    for k, v in maps.items():
        if any(x in name for x in v): return k
    return name

def get_cat(name, url=""):
    n, u = name.lower(), url.lower()
    if "samsung" in u: return "samsung"
    if any(x in n for x in ["quran", "sunnah", "islam"]): return "religious"
    if any(x in n for x in ["sport", "bein", "koora", "kass", "ssc"]): return "sports"
    if any(x in n for x in ["news", "jazeera", "arabiya", "sky", "bbc"]): return "news"
    if any(x in n for x in ["kid", "cartoon", "spacetoon", "majid", "toyor"]): return "kids"
    if any(x in n for x in ["movie", "cinema", "film", "mbc2", "drama", "action", "rotana"]): return "movies"
    if any(x in n for x in ["docu", "geo", "wild", "planet", "history"]): return "docu"
    return "general"

def update():
    all_raw = []
    print("🛰️ بدء عملية المسح الشامل (GitHub, GitLab, Pastebin)...")

    for url in URLS:
        try:
            r = requests.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=20)
            r.encoding = 'utf-8'
            text = r.text
            
            # 1. صيد Xtream
            xtreams = extract_xtream_and_m3u(text)
            for x in xtreams: all_raw.append(x)

            # 2. تحليل M3U
            lines = text.split('\n')
            meta = {}
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    nm = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    name = nm.group(1).strip() if nm else "Unknown"
                    lg = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = lg.group(1) if lg else ""
                    if any(t in name.lower() for t in TARGETS) or "ara" in url:
                        meta = {"name": name, "logo": logo}
                    else: meta = {}
                elif line.startswith("http") and meta:
                    all_raw.append({**meta, "url": line})
                    meta = {}
        except: pass

    print(f"📦 تم تجميع {len(all_raw)} رابط. جاري التصفية والفحص...")

    unique_urls = set(c['url'] for c in all_raw)
    valid_urls = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = {exe.submit(check_link, u): u for u in unique_urls}
        for f in as_completed(futures):
            u = futures[f]
            try:
                ok, lat = f.result()
                if ok: valid_urls[u] = lat
            except: pass

    # تنظيم النتائج
    final = {}
    for item in all_raw:
        if item['url'] in valid_urls:
            cid = clean_name(item['name'])
            if not cid: continue
            
            if cid not in final:
                dname = item['name'].title()
                if "mbc" in cid: dname = dname.upper()
                logo = item['logo']
                if (not logo or len(logo)<5) and cid in LOGO_FIXER: logo = LOGO_FIXER[cid]

                final[cid] = {
                    "name": dname, "logo": logo,
                    "category": get_cat(item['name'], item['url']),
                    "urls_list": []
                }
            
            if not any(x['u'] == item['url'] for x in final[cid]['urls_list']):
                final[cid]['urls_list'].append({"u": item['url'], "l": valid_urls[item['url']]})

    # بناء ملف JSON النهائي
    output = []
    for cid, data in final.items():
        # ترتيب الروابط: الأسرع أولاً
        sorted_links = sorted(data['urls_list'], key=lambda x: x['l'])
        output.append({
            "name": data['name'],
            "logo": data['logo'],
            "category": data['category'],
            "urls": [x['u'] for x in sorted_links]
        })

    # الترتيب حسب الأهمية
    prio = ["Jordan", "Roya", "Mamlaka", "MBC", "Al Jazeera", "BeIN", "Nat Geo", "Spacetoon"]
    output.sort(key=lambda c: next((i for i, p in enumerate(prio) if p.lower() in c['name'].lower()), 100))

    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ تم بنجاح! إجمالي القنوات الشغالة: {len(output)}")

if __name__ == "__main__":
    update()
