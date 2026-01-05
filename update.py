import requests
import json
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 0. إعدادات المحرك (Engine Settings)
# ==========================================
MAX_WORKERS = 60      # سرعة قصوى (عدد الروبوتات المتزامنة)
TIMEOUT = 5           # مهلة فحص الرابط

# قائمة التخفي (لخداع السيرفرات)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "VLC/3.0.20 LibVLC/3.0.20",
    "Kodi/19.0 (Matrix) Libreelec/10.0",
    "IPTV Smarters Pro"
]

BLACKLIST = ["adult", "xxx", "porn", "18+", "sex", "uncensored", "exotic", "babes"]

# ==========================================
# 1. المصادر الذكية (Smart Sources)
# ==========================================
URLS = [
    # --- المصادر الرسمية (حجر الأساس) ---
    "https://iptv-org.github.io/iptv/countries/jo.m3u", # الأردن
    "https://iptv-org.github.io/iptv/countries/eg.m3u", # مصر
    "https://iptv-org.github.io/iptv/countries/sa.m3u", # السعودية
    "https://iptv-org.github.io/iptv/countries/ae.m3u", # الإمارات
    "https://iptv-org.github.io/iptv/countries/kw.m3u", # الكويت
    "https://iptv-org.github.io/iptv/countries/lb.m3u", # لبنان
    
    # --- مصادر المجتمع (Community Lists) - كنز القنوات ---
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u",
    "https://raw.githubusercontent.com/vthanby/EPG/main/lists/arabic.m3u", # مصدر جديد قوي
    
    # --- المنصات العالمية (Samsung TV+, Pluto) ---
    "https://i.mjh.nz/SamsungTVPlus/all.m3u8",
    "https://i.mjh.nz/PlutoTV/all.m3u8",
    
    # --- الفئات الخاصة ---
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/religious.m3u"
]

# الكلمات المفتاحية (Targets)
TARGETS = [
    # عربية
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc", "abudhabi", "dubai", "sharjah",
    "jordan", "roya", "mamlaka", "jazeera", "alarabiya", "skynews", "bbc", "alhurra", "ltv", "mtv",
    # عالمية
    "national geo", "nat geo", "discovery", "animal planet", "history", "tlc", "investigation", "nasa",
    # أطفال
    "spacetoon", "cartoon network", "cn arabia", "nickelodeon", "nick", "disney", "majid", "baraem",
    # دينية
    "quran", "sunnah", "iqraa", "majalis", "resala"
]

# ==========================================
# 2. طبيب الشعارات (Logo Doctor)
# ==========================================
# قاعدة بيانات صور عالية الدقة للقنوات المهمة (في حال عدم توفرها)
LOGO_FIXER = {
    "mbc1": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MBC_1_Logo.svg/512px-MBC_1_Logo.svg.png",
    "mbc2": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/MBC_2_Logo.svg/512px-MBC_2_Logo.svg.png",
    "mbc3": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/MBC_3_Logo.svg/512px-MBC_3_Logo.svg.png",
    "mbc4": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/MBC_4_Logo.svg/512px-MBC_4_Logo.svg.png",
    "mbcaction": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/MBC_Action_Logo.svg/512px-MBC_Action_Logo.svg.png",
    "mbcmax": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/MBC_Max_Logo.svg/512px-MBC_Max_Logo.svg.png",
    "mbcdrama": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/00/MBC_Drama_Logo.svg/512px-MBC_Drama_Logo.svg.png",
    "mbcmasr": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/MBC_Masr_Logo.svg/512px-MBC_Masr_Logo.svg.png",
    "roya": "https://upload.wikimedia.org/wikipedia/commons/7/77/Roya_TV_Logo.png",
    "almamlaka": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/AlMamlakaTV.svg/512px-AlMamlakaTV.svg.png",
    "jordantv": "https://upload.wikimedia.org/wikipedia/en/2/22/Jordan_Radio_and_Television_Corporation_logo.png",
    "aljazeera": "https://upload.wikimedia.org/wikipedia/en/thumb/f/f2/Aljazeera_eng.svg/512px-Aljazeera_eng.svg.png",
    "alarabiya": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Al_Arabiya.svg/512px-Al_Arabiya.svg.png",
    "spacetoon": "https://upload.wikimedia.org/wikipedia/ar/d/d4/Spacetoon_logo_2015.png",
    "rotanacinema": "https://upload.wikimedia.org/wikipedia/commons/8/88/Rotana_Cinema_Logo.png",
    "natgeo": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/National_Geographic_Logo.svg/512px-National_Geographic_Logo.svg.png",
    "beinsports": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/BeIN_Sports_logo.svg/512px-BeIN_Sports_logo.svg.png"
}

# ==========================================
# 3. المنطق الذكي (Smart Logic)
# ==========================================

def check_stream(url):
    """اختبار ذكي: سرعة + نوع المحتوى"""
    start_time = time.time()
    try:
        agent = random.choice(USER_AGENTS)
        headers = {"User-Agent": agent}
        
        with requests.get(url, headers=headers, stream=True, timeout=TIMEOUT) as r:
            if r.status_code == 200:
                # التأكد من أن الرابط هو فيديو وليس صفحة خطأ
                ctype = r.headers.get('Content-Type', '').lower()
                valid_types = ['video', 'mpegurl', 'octet-stream', 'application/x-mpegurl', 'vnd.apple.mpegurl']
                
                if any(t in ctype for t in valid_types):
                    latency = time.time() - start_time
                    return (True, latency)
    except:
        pass
    return (False, 999)

def extract_quality(name):
    name = name.upper()
    if "4K" in name or "UHD" in name: return "4K"
    if "FHD" in name: return "FHD"
    if "HD" in name: return "HD"
    return "SD"

def clean_name(name):
    """تنظيف وتوحيد الأسماء بدقة عالية"""
    original = name
    name = name.lower()
    
    # فلترة المحتوى السيء
    if any(b in name for b in BLACKLIST): return None

    # تنظيف الكلمات الزائدة
    junk = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "channel", "live", "stream", "+", "(", ")", "[", "]", "|", "usa:", "uk:"]
    for w in junk:
        name = name.replace(w, "")
    
    name = re.sub(r'[^a-z0-9]', '', name) # إبقاء الحروف والأرقام فقط
    
    # الخريطة الذهنية لتوحيد الأسماء (Mapping)
    mappings = {
        "mbc1": ["mbc1", "mbcone"],
        "mbc2": ["mbc2", "mbctwo"],
        "mbc3": ["mbc3"],
        "mbc4": ["mbc4"],
        "mbc5": ["mbc5"],
        "mbcdrama": ["mbcdrama"],
        "mbcaction": ["mbcaction"],
        "mbcmax": ["mbcmax"],
        "mbcmasr": ["mbcmasr"],
        "mbcmasr2": ["mbcmasr2"],
        "mbciraq": ["mbciraq"],
        "mbcbollywood": ["mbcbollywood", "mbcbooly"],
        "natgeo": ["nationalgeographic", "natgeo", "nationalgeo"],
        "natgeowild": ["natgeowild", "wild"],
        "natgeokids": ["natgeokids"],
        "jordantv": ["jordan", "aljordon", "alurdun"],
        "roya": ["roya"],
        "almamlaka": ["almamlaka", "mamlaka"],
        "spacetoon": ["spacetoon"],
        "cartoonnetwork": ["cartoonnetwork", "cn"],
        "cnarabia": ["cnarabia", "cartoonnetworkarabic"],
        "beinsports": ["bein", "beinsport"],
        "beinsportsnews": ["beinnews", "beinsportnews"],
        "rotanacinema": ["rotanacinema"],
        "rotanaclassic": ["rotanaclassic"],
        "rotanacomedy": ["rotanacomedy"],
        "rotanamusic": ["rotanamusic"],
        "qurankareem": ["quran", "makkah"],
        "sunnah": ["sunnah", "madinah"]
    }
    
    for unified, variants in mappings.items():
        if any(v in name for v in variants):
            return unified
            
    # إذا لم يكن في القائمة، نعيد الاسم منظفاً
    return name

def get_cat(name, url=""):
    n = name.lower()
    u = url.lower()
    
    if "samsung" in u: return "samsung"
    if "pluto" in u: return "movies"
    if "quran" in n or "sunnah" in n or "iqraa" in n or "islam" in n or "majalis" in n: return "religious"
    if "sport" in n or "koora" in n or "bein" in n or "alkass" in n or "ssc" in n or "ad sport" in n: return "sports"
    if "news" in n or "jazeera" in n or "arabia" in n or "bbc" in n or "sky" in n or "alhurra" in n: return "news"
    if "kid" in n or "cartoon" in n or "spacetoon" in n or "nick" in n or "disney" in n or "majid" in n: return "kids"
    if "movi" in n or "cinema" in n or "film" in n or "rotana" in n or "mbc 2" in n or "drama" in n or "action" in n: return "movies"
    if "docu" in n or "geo" in n or "wild" in n or "planet" in n or "history" in n: return "docu"
    
    return "general"

# ==========================================
# 4. المحرك الرئيسي (Main Execution)
# ==========================================
def update():
    all_candidates = []
    print("🚀 بدء المحرك الذكي V7.0 (مع ميزة طبيب الشعارات)...")

    # 1. جمع الروابط
    for url in URLS:
        try:
            resp = requests.get(url, timeout=20)
            resp.encoding = 'utf-8'
            lines = resp.text.split('\n')
            
            meta = {}
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    # استخراج الاسم
                    name_m = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                    name = name_m.group(1).strip() if name_m else "Unknown"
                    
                    # استخراج الشعار
                    logo_m = re.search(r'tvg-logo="([^"]+)"', line)
                    logo = logo_m.group(1) if logo_m else ""
                    
                    # الفلترة: هل القناة عربية أو مستهدفة؟
                    is_arab = "ara.m3u" in url or "jo.m3u" in url or "eg.m3u" in url or "sa.m3u" in url or "kw.m3u" in url or "lb.m3u" in url
                    is_target = any(t in name.lower() for t in TARGETS)
                    
                    if is_arab or is_target:
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

    print(f"📦 تم تجميع {len(all_candidates)} رابط محتمل. بدء قياس السرعة...")

    # 2. فحص الروابط (Multi-threading)
    unique_links = set(c['url'] for c in all_candidates)
    working_stats = {}

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
                    working_stats[url] = latency
            except:
                pass

    print(f"✅ تم تأكيد {len(working_stats)} رابط.")

    # 3. بناء القائمة النهائية
    final_channels = {}
    
    for item in all_candidates:
        if item['url'] in working_stats:
            cid = clean_name(item['name'])
            
            if cid is None: continue 

            if cid not in final_channels:
                # تحسين الاسم للعرض
                display_name = item['name']
                if re.match(r'^[a-zA-Z0-9\s]+$', display_name): display_name = display_name.title()
                if "mbc" in cid and "drama" not in cid and "action" not in cid: display_name = display_name.upper()

                # استخدام طبيب الشعارات إذا لم يوجد شعار
                final_logo = item['logo']
                if (not final_logo or len(final_logo) < 5) and cid in LOGO_FIXER:
                    final_logo = LOGO_FIXER[cid]

                final_channels[cid] = {
                    "name": display_name,
                    "logo": final_logo,
                    "category": get_cat(item['name'], item['url']),
                    "urls_stats": [],
                    "quality": item['quality']
                }
            
            # إضافة الرابط (إذا لم يكن مكرراً)
            if not any(u['url'] == item['url'] for u in final_channels[cid]['urls_stats']):
                final_channels[cid]['urls_stats'].append({
                    "url": item['url'],
                    "latency": working_stats[item['url']]
                })
                
                # تحديث الشعار إذا وجدنا شعاراً أفضل في مصدر آخر
                if not final_channels[cid]['logo'] and item['logo']:
                     final_channels[cid]['logo'] = item['logo']
                # إذا وجدنا شعاراً في "طبيب الشعارات"، نعتمده فوراً لأنه الأفضل
                if cid in LOGO_FIXER:
                    final_channels[cid]['logo'] = LOGO_FIXER[cid]

    # 4. الترتيب والتصدير
    output = []
    stats_counter = {} # للإحصائيات

    for cid, data in final_channels.items():
        if not data['urls_stats']: continue
        
        # ترتيب الروابط حسب السرعة (الأسرع أولاً)
        sorted_links = sorted(data['urls_stats'], key=lambda x: x['latency'])
        final_urls = [x['url'] for x in sorted_links]
        
        # إحصائيات
        cat = data['category']
        stats_counter[cat] = stats_counter.get(cat, 0) + 1
        
        output.append({
            "name": data['name'],
            "logo": data['logo'],
            "category": cat,
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

    # طباعة التقرير النهائي
    print("-" * 30)
    print("📊 تقرير القنوات المكتشفة:")
    for cat, count in stats_counter.items():
        print(f"   - {cat}: {count} قناة")
    print("-" * 30)
    print(f"🎉 المجموع الكلي: {len(output)} قناة جاهزة.")
    
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update()
