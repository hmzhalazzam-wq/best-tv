import requests
import json
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# إعدادات المحرك
# ==========================================
MAX_WORKERS = 50      # سرعة الفحص
TIMEOUT = 5           # مهلة الاستجابة

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "VLC/3.0.20 LibVLC/3.0.20",
    "IPTV Smarters Pro"
]

BLACKLIST = ["adult", "xxx", "porn", "18+", "sex", "uncensored"]

# ==========================================
# المصادر (تم اختيار الأفضل والأسرع)
# ==========================================
URLS = [
    # الرسمية
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/kw.m3u",
    
    # المجتمعية والشاملة
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u",
    
    # المنصات والفئات
    "https://i.mjh.nz/SamsungTVPlus/all.m3u8",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u"
]

# الكلمات المفتاحية
TARGETS = [
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc", "abudhabi", "dubai",
    "national geo", "nat geo", "discovery", "animal planet", "spacetoon", "cartoon network",
    "cn arabia", "jordan", "roya", "mamlaka", "jazeera", "alarabiya", "skynews", "bbc",
    "samsung", "quran", "sunnah"
]

# ==========================================
# إصلاح الشعارات (Logo Doctor)
# ==========================================
LOGO_FIXER = {
    "mbc1": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MBC_1_Logo.svg/512px-MBC_1_Logo.svg.png",
    "mbc2": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/MBC_2_Logo.svg/512px-MBC_2_Logo.svg.png",
    "mbcaction": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/MBC_Action_Logo.svg/512px-MBC_Action_Logo.svg.png",
    "mbcdrama": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/MBC_Drama_Logo.svg/512px-MBC_Drama_Logo.svg.png",
    "mbcmasr": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/MBC_Masr_Logo.svg/512px-MBC_Masr_Logo.svg.png",
    "roya": "https://upload.wikimedia.org/wikipedia/commons/7/77/Roya_TV_Logo.png",
    "almamlaka": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/AlMamlakaTV.svg/512px-AlMamlakaTV.svg.png",
    "jordantv": "https://upload.wikimedia.org/wikipedia/en/2/22/Jordan_Radio_and_Television_Corporation_logo.png",
    "aljazeera": "https://upload.wikimedia.org/wikipedia/en/thumb/f/f2/Aljazeera_eng.svg/512px-Aljazeera_eng.svg.png",
    "alarabiya": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Al_Arabiya.svg/512px-Al_Arabiya.svg.png",
    "spacetoon": "https://upload.wikimedia.org/wikipedia/ar/d/d4/Spacetoon_logo_2015.png",
    "beinsports": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/BeIN_Sports_logo.svg/512px-BeIN_Sports_logo.svg.png"
}

# ==========================================
# المنطق
# ==========================================
def check_stream(url):
    """فحص سرعة وصلاحية الرابط"""
    start = time.time()
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        with requests.get(url, headers=headers, stream=True, timeout=TIMEOUT) as r:
            if r.status_code == 200:
                ctype = r.headers.get('Content-Type', '').lower()
                if any(t in ctype for t in ['video', 'mpegurl', 'octet-stream']):
                    return (True, time.time() - start)
    except:
        pass
    return (False, 999)

def get_quality(name):
    name = name.upper()
    if "4K" in name: return "4K"
    if "FHD" in name: return "FHD"
    if "HD" in name: return "HD"
    return "SD"

def clean_name(name):
    name = name.lower()
    if any(b in name for b in BLACKLIST): return None
    
    # تنظيف
    junk = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "channel", "live", "stream", "+", "(", ")", "[", "]"]
    for w in junk: name = name.replace(w, "")
    name = re.sub(r'[^a-z0-9]', '', name)
    
    # توحيد
    maps = {
        "mbc1": ["mbc1", "mbcone"], "mbc2": ["mbc2"], "mbc3": ["mbc3"], "mbc4": ["mbc4"],
        "mbcaction": ["mbcaction"], "mbcdrama": ["mbcdrama"], "mbcmasr": ["mbcmasr"],
        "natgeo": ["nationalgeographic", "natgeo"], "natgeowild": ["wild", "natgeowild"],
        "jordantv": ["jordan", "aljordon"], "roya": ["roya"], "almamlaka": ["mamlaka", "almamlaka"],
        "spacetoon": ["spacetoon"], "beinsports": ["bein"], "quran": ["quran", "makkah"]
    }
    for k, v in maps.items():
        if any(x in name for x in v): return k
    return name

def get_cat(name, url=""):
    n, u = name.lower(), url.lower()
    if "samsung" in u: return "samsung"
    if "quran" in n or "sunnah" in n: return "religious"
    if "sport" in n or "koora" in n or "bein" in n: return "sports"
    if "news" in n or "jazeera" in n or "arabia" in n: return "news"
    if "kid" in n or "cartoon" in n or "spacetoon" in n: return "kids"
    if "movi" in n or "cinema" in n or "film" in n or "mbc 2" in n: return "movies"
    if "docu" in n or "geo" in n or "wild" in n: return "docu"
    return "general"

def update():
    print("🚀 بدء المحرك المتكامل...")
    candidates = []

    # 1. التجميع
    for url in URLS:
        try:
            resp = requests.get(url, timeout=15)
            resp.encoding = 'utf-8'
            for line in resp.text.split('\n'):
                line = line.strip()
                if line.startswith("#EXTINF"):
                    name_m = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    name = name_m.group(1).strip() if name_m else "Unknown"
                    logo_m = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_m.group(1) if logo_m else ""
                    
                    is_arab = any(x in url for x in ["ara", "jo", "eg", "sa", "kw", "lb"])
                    is_target = any(t in name.lower() for t in TARGETS)
                    
                    if is_arab or is_target:
                        meta = {"name": name, "logo": logo}
                    else: meta = {}
                elif line.startswith("http") and meta:
                    if not line.endswith(".ts"):
                        candidates.append({**meta, "url": line, "q": get_quality(meta['name'])})
                    meta = {}
        except: pass

    print(f"📦 تم جمع {len(candidates)} قناة. الفحص الذكي...")

    # 2. الفحص
    valid_links = {}
    unique_urls = set(c['url'] for c in candidates)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(check_stream, u): u for u in unique_urls}
        for f in as_completed(futures):
            try:
                ok, lat = f.result()
                if ok: valid_links[futures[f]] = lat
            except: pass

    print(f"✅ القنوات العاملة: {len(valid_links)}")

    # 3. البناء
    final = {}
    for c in candidates:
        if c['url'] in valid_links:
            cid = clean_name(c['name'])
            if not cid: continue
            
            if cid not in final:
                dname = c['name'].title()
                if "mbc" in cid and "drama" not in cid: dname = dname.upper()
                
                my_logo = c['logo']
                if (not my_logo or len(my_logo)<5) and cid in LOGO_FIXER:
                    my_logo = LOGO_FIXER[cid]

                final[cid] = {
                    "name": dname, "logo": my_logo,
                    "category": get_cat(c['name'], c['url']),
                    "urls": [], "quality": c['q']
                }
            
            # نضيف الرابط مع سرعته
            if not any(u['url'] == c['url'] for u in final[cid]['urls']):
                final[cid]['urls'].append({"url": c['url'], "lat": valid_links[c['url']]})
                if not final[cid]['logo'] and c['logo']: final[cid]['logo'] = c['logo']

    # 4. التصدير
    output = []
    for k, v in final.items():
        # ترتيب الروابط: الأسرع أولاً
        sorted_urls = sorted(v['urls'], key=lambda x: x['lat'])
        clean_urls = [u['url'] for u in sorted_urls]
        
        output.append({
            "name": v['name'],
            "logo": v['logo'],
            "category": v['category'],
            "urls": clean_urls,
            "quality": v['quality']
        })

    # ترتيب الأولويات
    prio = ["Jordan", "Roya", "Mamlaka", "MBC", "Jazeera", "BeIN", "Nat Geo"]
    output.sort(key=lambda x: next((i for i, p in enumerate(prio) if p.lower() in x['name'].lower()), 100))

    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("🎉 تم التحديث بنجاح!")

if __name__ == "__main__":
    update()
