import requests
import json
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 0. إعدادات متقدمة (Advanced Settings)
# ==========================================
MAX_WORKERS = 50   # زدنا العدد لسرعة صاروخية
TIMEOUT = 6        # مهلة انتظار معقولة

# قائمة هويات وهمية (للتخفي وتجنب الحظر)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "VLC/3.0.20 LibVLC/3.0.20"
]

# كلمات محظورة (لضمان محتوى نظيف)
BLACKLIST = ["adult", "xxx", "porn", "18+", "sex", "uncensored", "exotic"]

# ==========================================
# 1. المصادر العملاقة (شاملة ومحدثة)
# ==========================================
URLS = [
    # قوائم رسمية وموثوقة
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/kw.m3u",
    
    # قوائم ضخمة (مجتمع)
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u",
    
    # منصات عالمية (جودة عالية)
    "https://i.mjh.nz/SamsungTVPlus/all.m3u8",
    "https://i.mjh.nz/PlutoTV/all.m3u8",
    
    # تصنيفات
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/religious.m3u"
]

# الكلمات المستهدفة (تمت إضافة قنوات إسلامية ووثائقية)
TARGETS = [
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc", "abudhabi", "dubai",
    "national geo", "nat geo", "discovery", "animal planet", "history", "tlc", "investigation",
    "spacetoon", "cartoon network", "cn arabia", "nickelodeon", "nick", "disney", "majid",
    "jordan", "roya", "mamlaka", "jazeera", "alarabiya", "skynews", "bbc",
    "samsung", "pluto", "rakuten", "quran", "sunnah", "iqraa", "majalis"
]

# ==========================================
# 3. الوظائف الذكية (الجيل الجديد)
# ==========================================

def check_stream(url):
    """
    فحص ذكي جداً: يقيس السرعة (Latency) ويتأكد من المحتوى.
    يرجع: (هل يعمل؟, زمن الاستجابة)
    """
    start_time = time.time()
    try:
        # اختيار هوية عشوائية
        agent = random.choice(USER_AGENTS)
        headers = {"User-Agent": agent}
        
        with requests.get(url, headers=headers, stream=True, timeout=TIMEOUT) as r:
            if r.status_code == 200:
                # التحقق أن المحتوى فيديو فعلاً
                ctype = r.headers.get('Content-Type', '').lower()
                if any(x in ctype for x in ['video', 'mpegurl', 'octet-stream', 'application/x-mpegurl']):
                    latency = time.time() - start_time
                    return (True, latency)
    except:
        pass
    return (False, 999)

def extract_quality(name):
    name = name.upper()
    if "4K" in name: return "4K"
    if "FHD" in name: return "FHD"
    if "HD" in name: return "HD"
    return "SD"

def clean_name(name):
    original = name
    name = name.lower()
    
    # التحقق من القائمة السوداء
    if any(b in name for b in BLACKLIST):
        return None # رفض القناة

    # تنظيف
    junk = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "channel", "live", "stream", "+", "(", ")", "[", "]", "|"]
    for w in junk:
        name = name.replace(w, "")
    
    name = re.sub(r'[^a-z0-9]', '', name)
    
    # توحيد الأسماء (Mapping)
    mappings = {
        "mbc": ["mbc1", "mbcone"],
        "mbcdrama": ["mbcdrama"],
        "mbcaction": ["mbcaction"],
        "mbc2": ["mbc2", "mbctwo"],
        "mbc3": ["mbc3", "mbcthree"],
        "mbc4": ["mbc4", "mbcfour"],
        "mbcmasr": ["mbcmasr"],
        "mbciraq": ["mbciraq"],
        "mbcbollywood": ["mbcbollywood", "mbcbooly"],
        "natgeo": ["nationalgeographic", "natgeo", "nationalgeo"],
        "natgeowild": ["natgeowild", "wild"],
        "jordantv": ["jordan", "aljordon", "alurdun"],
        "roya": ["roya"],
        "almamlaka": ["almamlaka", "mamlaka"],
        "spacetoon": ["spacetoon"],
        "beinsports": ["bein", "beinsport"],
        "rotanacinema": ["rotanacinema"],
        "qurankareem": ["quran", "makkah"],
        "sunnah": ["sunnah", "madinah"]
    }
    
    for unified, variants in mappings.items():
        if any(v in name for v in variants):
            return unified
            
    return name

def get_cat(name, url=""):
    n = name.lower()
    u = url.lower()
    
    if "samsung" in u: return "samsung"
    if "quran" in n or "sunnah" in n or "iqraa" in n or "islam" in n: return "religious"
    if "sport" in n or "koora" in n or "bein" in n or "alkass" in n or "ssc" in n: return "sports"
    if "news" in n or "jazeera" in n or "arabia" in n or "bbc" in n or "sky" in n: return "news"
    if "kid" in n or "cartoon" in n or "spacetoon" in n or "nick" in n or "disney" in n: return "kids"
    if "movi" in n or "cinema" in n or "film" in n or "rotana" in n or "mbc 2" in n or "drama" in n: return "movies"
    if "docu" in n or "geo" in n or "wild" in n or "planet" in n or "history" in n: return "docu"
    
    return "general"

# ==========================================
# 4. المحرك الرئيسي
# ==========================================
def update():
    all_candidates = []
    print("🚀 بدء المحرك الذكي V6.0 (اختبار السرعة + التخفي)...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=20)
            resp.encoding = 'utf-8'
            lines = resp.text.split('\n')
            
            meta = {}
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    name_m = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    name = name_m.group(1).strip() if name_m else "Unknown"
                    
                    logo_m = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_m.group(1) if logo_m else ""
                    
                    is_arab_list = "ara.m3u" in url or "jo.m3u" in url or "eg.m3u" in url or "sa.m3u" in url or "kw.m3u" in url
                    is_target_keyword = any(t in name.lower() for t in TARGETS)
                    
                    if is_arab_list or is_target_keyword:
                        meta = {"name": name, "logo": logo}
                    else:
                        meta = {} 
                        
                elif line.startswith("http") and meta:
                    if not line.endswith(".ts"):
                        all_candidates.append({
                            "name": meta['name'],
                            "logo": meta['logo'],
                            "url": line,
                            "quality": extract_quality(meta['name'])
                        })
                    meta = {}
        except Exception as e:
            print(f"⚠️ تجاوز المصدر {url}: {e}")

    print(f"📦 تم تجميع {len(all_candidates)} رابط. بدء قياس السرعة...")

    unique_links = set(c['url'] for c in all_candidates)
    # القاموس سيحفظ: {الرابط: سرعة_الاستجابة}
    working_links_stats = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_stream, url): url for url in unique_links}
        
        checked = 0
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            checked += 1
            if checked % 100 == 0: print(f"✨ تم فحص {checked}/{len(unique_links)}...")
            
            try:
                is_working, latency = future.result()
                if is_working:
                    working_links_stats[url] = latency
            except:
                pass

    print(f"✅ تم تأكيد {len(working_links_stats)} رابط.")

    final_channels = {}
    
    for item in all_candidates:
        if item['url'] in working_links_stats:
            cid = clean_name(item['name'])
            
            if cid is None: continue # تم رفض القناة (Blacklist)

            if cid not in final_channels:
                display_name = item['name']
                if re.match(r'^[a-zA-Z0-9\s]+$', display_name): display_name = display_name.title()
                if "mbc" in cid and "drama" not in cid and "action" not in cid: display_name = display_name.upper()

                final_channels[cid] = {
                    "name": display_name,
                    "logo": item['logo'],
                    "category": get_cat(item['name'], item['url']),
                    "urls_stats": [], # سنحفظ الرابط مع سرعته
                    "quality": item['quality']
                }
            
            # نضيف الرابط وسرعته للقائمة
            # نتأكد من عدم تكرار الرابط
            if not any(u['url'] == item['url'] for u in final_channels[cid]['urls_stats']):
                final_channels[cid]['urls_stats'].append({
                    "url": item['url'],
                    "latency": working_links_stats[item['url']]
                })
                
                if not final_channels[cid]['logo'] and item['logo']:
                    final_channels[cid]['logo'] = item['logo']

    # تحويل للقائمة النهائية وتنظيف الهيكل
    output = []
    for cid, data in final_channels.items():
        if not data['urls_stats']: continue
        
        # ترتيب الروابط حسب السرعة (الأسرع أولاً)
        # هذا هو السحر! سيضع السيرفر الأسرع كأول خيار للمشغل
        sorted_links = sorted(data['urls_stats'], key=lambda x: x['latency'])
        
        # استخراج الروابط فقط للقائمة النهائية
        final_urls = [x['url'] for x in sorted_links]
        
        output.append({
            "name": data['name'],
            "logo": data['logo'],
            "category": data['category'],
            "urls": final_urls,
            "quality": data['quality']
        })

    # ترتيب الأولويات
    priority = ["Jordan", "Roya", "Mamlaka", "MBC", "Al Jazeera", "BeIN", "Nat Geo", "Quran"]
    def sort_logic(c):
        n = c['name'].lower()
        for i, p in enumerate(priority):
            if p.lower() in n: return i
        return 100

    output.sort(key=sort_logic)

    print(f"🎉 الإنجاز: {len(output)} قناة، مرتبة حسب سرعة السيرفر.")
    
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update()
