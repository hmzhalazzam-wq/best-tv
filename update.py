import requests
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 1. المصادر العملاقة (شاملة المنتديات والمجتمعات)
# ==========================================
URLS = [
    # --- القوائم الرسمية والموثوقة ---
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/kw.m3u",
    
    # --- قوائم التجميع الكبرى (يتم تحديثها من المنتديات) ---
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u",
    
    # --- قوائم المنصات العالمية (Samsung TV+, Pluto, Roku) ---
    # هذه تحتوي على قنوات وثائقية وأطفال بجودة عالية جداً
    "https://i.mjh.nz/SamsungTVPlus/all.m3u8",
    "https://i.mjh.nz/PlutoTV/all.m3u8",
    
    # --- قوائم الفئات العالمية ---
    "https://iptv-org.github.io/iptv/categories/documentary.m3u",
    "https://iptv-org.github.io/iptv/categories/kids.m3u",
    "https://iptv-org.github.io/iptv/categories/sports.m3u",
    "https://iptv-org.github.io/iptv/categories/movies.m3u",
    "https://iptv-org.github.io/iptv/categories/music.m3u"
]

# الكلمات المفتاحية للقنوات (Targets)
# تم توسيعها لتشمل قنوات أكثر تنوعاً
TARGETS = [
    # قنوات عربية كبرى
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc", "abudhabi", "dubai",
    # قنوات وثائقية وعالمية
    "national geo", "nat geo", "discovery", "animal planet", "history", "tlc", "investigation",
    # أطفال
    "spacetoon", "cartoon network", "cn arabia", "nickelodeon", "nick", "disney", "majid",
    # أخبار وقنوات وطنية
    "jordan", "roya", "mamlaka", "jazeera", "alarabiya", "skynews", "bbc",
    # منصات
    "samsung", "pluto", "rakuten"
]

# ==========================================
# 2. إعدادات الفحص
# ==========================================
MAX_WORKERS = 40  # زدنا عدد الروبوتات للسرعة
TIMEOUT = 5       # زدنا وقت الانتظار قليلاً للقنوات البطيئة

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ==========================================
# 3. الوظائف الذكية
# ==========================================

def check_stream(url):
    """فحص ذكي: يتأكد أن الرابط يعمل وأنه فيديو فعلاً"""
    try:
        with requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT) as r:
            if r.status_code == 200:
                # تحقق إضافي: هل المحتوى فيديو؟
                content_type = r.headers.get('Content-Type', '').lower()
                if 'video' in content_type or 'mpegurl' in content_type or 'octet-stream' in content_type:
                    return True
    except:
        return False
    return False

def extract_quality(name):
    """استخراج جودة القناة من الاسم"""
    name = name.upper()
    if "4K" in name: return "4K"
    if "FHD" in name: return "FHD"
    if "HD" in name: return "HD"
    return "SD"

def clean_name(name):
    """تنظيف وتوحيد الأسماء"""
    name = name.lower()
    
    # تنظيف الكلمات الزائدة
    junk = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "channel", "live", "stream", "+", "(", ")", "[", "]"]
    for w in junk:
        name = name.replace(w, "")
    
    # إزالة الرموز
    name = re.sub(r'[^a-z0-9]', '', name)
    
    # توحيد المسميات (Mapping)
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
        "rotanaclassic": ["rotanaclassic"]
    }
    
    for unified, variants in mappings.items():
        if any(v in name for v in variants):
            return unified
            
    return name

def get_cat(name, url=""):
    """تحديد التصنيف بناءً على الاسم والرابط"""
    n = name.lower()
    u = url.lower()
    
    # تحليل الرابط (ميزة جديدة)
    if "samsung" in u: return "samsung"
    
    # تحليل الاسم
    if "sport" in n or "koora" in n or "bein" in n or "alkass" in n or "ssc" in n: return "sports"
    if "news" in n or "jazeera" in n or "arabia" in n or "bbc" in n or "sky" in n: return "news"
    if "kid" in n or "cartoon" in n or "spacetoon" in n or "nick" in n or "disney" in n: return "kids"
    if "movi" in n or "cinema" in n or "film" in n or "rotana" in n or "mbc 2" in n or "drama" in n: return "movies"
    if "docu" in n or "geo" in n or "wild" in n or "planet" in n or "history" in n: return "docu"
    if "music" in n or "radio" in n: return "music"
    if "quran" in n or "sunna" in n: return "religious"
    
    return "general"

# ==========================================
# 4. المحرك الرئيسي
# ==========================================
def update():
    all_candidates = []
    print("🚀 بدء تشغيل المحرك الذكي (V5.0)... البحث في المصادر المجتمعية والرسمية...")

    for url in URLS:
        try:
            resp = requests.get(url, timeout=20) # زيادة الوقت للقوائم الكبيرة
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
                    
                    # فلترة ذكية
                    is_arab_list = "ara.m3u" in url or "jo.m3u" in url or "eg.m3u" in url or "sa.m3u" in url
                    is_target_keyword = any(t in name.lower() for t in TARGETS)
                    
                    # نقبل القناة إذا كانت من قائمة عربية، أو إذا كان اسمها مطلوباً
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
                            "quality": extract_quality(meta['name']) # ميزة جديدة
                        })
                    meta = {}
        except Exception as e:
            print(f"⚠️ تجاوز المصدر {url}: {e}")

    print(f"📦 تم تجميع {len(all_candidates)} رابط. بدء الفحص الدقيق...")

    # تجميع وفحص الروابط
    unique_links = set(c['url'] for c in all_candidates)
    working_links = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_stream, url): url for url in unique_links}
        
        checked = 0
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            checked += 1
            if checked % 100 == 0: print(f"✨ تم فحص {checked}/{len(unique_links)}...")
            
            try:
                if future.result():
                    working_links.add(url)
            except:
                pass

    print(f"✅ تم تأكيد عمل {len(working_links)} رابط.")

    # بناء الهيكل النهائي
    final_channels = {}
    
    for item in all_candidates:
        if item['url'] in working_links:
            cid = clean_name(item['name'])
            
            if cid not in final_channels:
                # تحسين الاسم للعرض
                display_name = item['name']
                # إذا كان الاسم بالانجليزي، نجعله Capitalized
                if re.match(r'^[a-zA-Z0-9\s]+$', display_name):
                    display_name = display_name.title()
                
                # تصحيح خاص لـ MBC
                if "mbc" in cid and "drama" not in cid and "action" not in cid: display_name = display_name.upper()

                final_channels[cid] = {
                    "name": display_name,
                    "logo": item['logo'],
                    "category": get_cat(item['name'], item['url']),
                    "urls": [],
                    "quality": item['quality']
                }
            
            if item['url'] not in final_channels[cid]['urls']:
                final_channels[cid]['urls'].append(item['url'])
                if not final_channels[cid]['logo'] and item['logo']:
                    final_channels[cid]['logo'] = item['logo']

    # تحويل للقائمة النهائية
    output = list(final_channels.values())
    output = [c for c in output if c['urls']]

    # ترتيب الأولويات (الأردنية والعربية أولاً)
    priority = ["Jordan", "Roya", "Mamlaka", "MBC", "Al Jazeera", "BeIN", "Nat Geo"]
    def sort_logic(c):
        n = c['name'].lower()
        for i, p in enumerate(priority):
            if p.lower() in n: return i
        return 100

    output.sort(key=sort_logic)

    print(f"🎉 الإنجاز: {len(output)} قناة جاهزة للبث.")
    
    with open("channels.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    update()
