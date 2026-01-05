import requests
import json
import re
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# ==========================================
# 🕷️ إعدادات الزاحف العنكبوتي (V13 - HTTPS Priority)
# ==========================================
MAX_WORKERS = 50       # سرعة عالية للفحص
TIMEOUT = 5            # مهلة قصيرة لتجاوز السيرفرات الميتة بسرعة
MIN_CHANNELS = 15      # أمان لعدم تحديث الملف إذا فشل النت

# تمويه المتصفح (ضروري جداً لتجاوز الحجب)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "VLC/3.0.20 LibVLC/3.0.20",
    "TiviMate/4.7.0"
]

# الكلمات المحظورة
BLACKLIST = ["adult", "xxx", "porn", "18+", "sex", "uncensored", "exotic", "hot", "xx"]

# ==========================================
# 🌐 مصادر الزحف (ديناميكية ومتجددة)
# ==========================================
SEARCH_SOURCES = [
    # المصادر العربية الأساسية (GitHub Raw)
    "https://iptv-org.github.io/iptv/countries/jo.m3u",
    "https://iptv-org.github.io/iptv/countries/sa.m3u",
    "https://iptv-org.github.io/iptv/countries/ae.m3u",
    "https://iptv-org.github.io/iptv/countries/eg.m3u",
    "https://iptv-org.github.io/iptv/languages/ara.m3u",
    
    # مستودعات يتم تحديثها أوتوماتيكياً (Raw Links - كنز للقنوات)
    "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8",
    "https://raw.githubusercontent.com/jnk22/kodirpo/master/iptv/arab.m3u",
    "https://raw.githubusercontent.com/yousf/tv/main/ar.m3u",
    "https://raw.githubusercontent.com/gielj/iptv-2/master/Ar.m3u",
    
    # مصادر عالمية قد تحتوي على قنوات عربية
    "https://i.mjh.nz/SamsungTVPlus/all.m3u8",
    "https://i.mjh.nz/PlutoTV/all.m3u8"
]

# القنوات المستهدفة (الأكثر طلباً)
TARGETS = [
    "mbc", "bein", "osn", "rotana", "art ", "shahid", "alkass", "ssc", "abudhabi", "dubai",
    "jordan", "roya", "mamlaka", "jazeera", "alarabiya", "skynews",
    "national geo", "nat geo", "spacetoon", "cartoon network", "majid", "quran", "sunnah"
]

# إصلاح الشعارات المفقودة
LOGO_FIXER = {
    "mbc1": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/MBC_1_Logo.svg/512px-MBC_1_Logo.svg.png",
    "mbc2": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/MBC_2_Logo.svg/512px-MBC_2_Logo.svg.png",
    "mbcaction": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/MBC_Action_Logo.svg/512px-MBC_Action_Logo.svg.png",
    "mbc3": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/MBC_3_Logo.svg/512px-MBC_3_Logo.svg.png",
    "roya": "https://upload.wikimedia.org/wikipedia/commons/7/77/Roya_TV_Logo.png",
    "almamlaka": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/AlMamlakaTV.svg/512px-AlMamlakaTV.svg.png",
    "beinsports": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/BeIN_Sports_logo.svg/512px-BeIN_Sports_logo.svg.png"
}

# ==========================================
# 🧠 وظائف الزحف والتحليل
# ==========================================

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.google.com/",
        "Accept": "*/*"
    }

def clean_name(name):
    """تنظيف وتوحيد أسماء القنوات"""
    name = name.lower()
    if any(b in name for b in BLACKLIST): return None
    
    # تنظيف الرموز والكلمات الزائدة
    junk = ["hd", "sd", "fhd", "4k", "hevc", "ar", "arabic", "tv", "live", "stream", "|", "[", "]", "(", ")", "vip", "new", "update", "channel"]
    for w in junk: name = name.replace(w, "")
    
    # إزالة الأرقام والرموز في البداية والنهاية
    name = name.strip(" .-0123456789")
    name = re.sub(r'[^a-z0-9]', '', name)
    
    # توحيد الأسماء (Mapping) لضمان عدم تكرار القناة بأسماء مختلفة
    maps = {
        "mbc1": ["mbc1", "mbcone"], 
        "mbc2": ["mbc2"], 
        "mbc3": ["mbc3"], 
        "mbc4": ["mbc4"],
        "mbcaction": ["mbcaction", "action"], 
        "mbcdrama": ["mbcdrama"], 
        "mbcmasr": ["mbcmasr"],
        "mbciraq": ["mbciraq"],
        "mbc5": ["mbc5"],
        "roya": ["roya"], 
        "almamlaka": ["mamlaka"], 
        "jordantv": ["jordan", "aljordon"],
        "spacetoon": ["spacetoon"], 
        "beinsports": ["bein", "beinsport"], 
        "rotanacinema": ["rotanacinema"], 
        "osn": ["osn"], 
        "art": ["artmovies", "arthekayat"]
    }
    
    for k, v in maps.items():
        if any(x in name for x in v): return k
    
    if len(name) < 2: return None
    return name

def check_stream(url):
    """فحص ذكي للسيرفر مع تفضيل HTTPS"""
    start = time.time()
    try:
        # نظام النقاط: نعطي 50 نقطة إضافية للرابط الآمن HTTPS
        # هذا يحل مشكلة التشغيل على اللابتوب والمتصفحات الحديثة
        priority_bonus = 0
        if url.startswith("https"): priority_bonus = 50
        
        with requests.get(url, headers=get_headers(), stream=True, timeout=TIMEOUT, verify=False) as r:
            if r.status_code == 200:
                ct = r.headers.get('Content-Type', '').lower()
                # التأكد من نوع المحتوى
                if any(t in ct for t in ['video', 'mpegurl', 'stream', 'octet', 'application/x-mpegurl']):
                    latency = time.time() - start
                    # المعادلة: السرعة - البونص (كلما قل الرقم كان أفضل)
                    final_score = latency - (priority_bonus / 10) 
                    return (True, final_score)
    except:
        pass
    return (False, 999)

def fetch_and_parse():
    """الزحف لجلب الروابط"""
    print("🕸️ بدء الزاحف العنكبوتي...")
    found_streams = []

    def fetch_url(source_url):
        try:
            r = requests.get(source_url, headers=get_headers(), timeout=10, verify=False)
            if r.status_code == 200:
                return r.text
        except: return ""
        return ""

    # جلب القوائم بالتوازي
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(fetch_url, SEARCH_SOURCES)

    for text in results:
        if not text: continue
        
        lines = text.split('\n')
        current_name = ""
        current_logo = ""
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            if line.startswith("#EXTINF"):
                # استخراج البيانات بمرونة
                nm_match = re.search(r'tvg-name="([^"]+)"', line) or re.search(r',(.*)', line)
                lg_match = re.search(r'tvg-logo="([^"]+)"', line)
                
                if nm_match: 
                    raw_name = nm_match.group(1).split(',')[-1].strip()
                    # تنظيف أولي سريع
                    current_name = raw_name
                
                if lg_match: current_logo = lg_match.group(1)
            
            elif line.startswith("http"):
                # فلترة مبدئية لتسريع العملية
                is_target = any(t in current_name.lower() for t in TARGETS)
                is_arabic = "ar" in line or "arab" in current_name.lower()
                
                if (is_target or is_arabic) and current_name:
                    found_streams.append({
                        "name": current_name,
                        "logo": current_logo,
                        "url": line
                    })
                
                current_name = "" 
                current_logo = ""

    print(f"💰 تم العثور على {len(found_streams)} رابط. جاري الفحص الدقيق...")
    return found_streams

def main():
    raw_data = fetch_and_parse()
    
    # إزالة التكرار
    unique_links = {item['url']: item for item in raw_data}
    urls_to_check = list(unique_links.keys())
    
    valid_channels = {}
    
    # فحص الروابط
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
        futures = {exe.submit(check_stream, u): u for u in urls_to_check}
        
        for f in as_completed(futures):
            u = futures[f]
            try:
                is_working, score = f.result()
                if is_working:
                    item = unique_links[u]
                    cid = clean_name(item['name'])
                    if cid:
                        if cid not in valid_channels:
                            # تنسيق الاسم للعرض
                            d_name = cid
                            # إصلاحات الأسماء
                            if "mbc" in cid: d_name = cid.upper().replace("MBC", "MBC ")
                            elif "bein" in cid: d_name = "beIN Sports " + cid.replace("beinsports", "")
                            elif "roya" in cid: d_name = "Roya TV"
                            else: d_name = cid.title()
                            
                            # استخدام شعار ثابت إذا كان متاحاً لتحسين المظهر
                            logo = item['logo']
                            if cid in LOGO_FIXER: logo = LOGO_FIXER[cid]
                            elif not logo: logo = "https://via.placeholder.com/100?text=TV"

                            valid_channels[cid] = {
                                "name": d_name,
                                "logo": logo,
                                "category": "general",
                                "urls": []
                            }
                            
                            # تصنيف بسيط
                            n_low = cid
                            if "sport" in n_low or "bein" in n_low: valid_channels[cid]["category"] = "sports"
                            elif "news" in n_low or "jazeera" in n_low: valid_channels[cid]["category"] = "news"
                            elif "kid" in n_low or "spacetoon" in n_low: valid_channels[cid]["category"] = "kids"
                            elif "quran" in n_low: valid_channels[cid]["category"] = "religious"
                            elif "movie" in n_low or "osn" in n_low: valid_channels[cid]["category"] = "movies"

                        valid_channels[cid]['urls'].append({"u": u, "s": score})
            except: pass

    # بناء القائمة النهائية
    output = []
    for cid, data in valid_channels.items():
        # ترتيب الروابط حسب الأفضلية (Score الأقل هو الأفضل)
        sorted_urls = sorted(data['urls'], key=lambda x: x['s'])
        final_urls = [x['u'] for x in sorted_urls[:8]] # نحتفظ بأفضل 8 سيرفرات
        
        output.append({
            "name": data['name'],
            "logo": data['logo'],
            "category": data['category'],
            "urls": final_urls
        })

    # ترتيب القنوات بالأهمية
    prio_list = ["jordan", "roya", "mbc", "bein", "news"]
    output.sort(key=lambda x: next((i for i, p in enumerate(prio_list) if p in clean_name(x['name']) or ""), 99))

    if len(output) >= MIN_CHANNELS:
        with open("channels.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"✅ تم التحديث بنجاح! {len(output)} قناة تعمل.")
    else:
        print("⚠️ عدد القنوات قليل جداً، لم يتم تحديث الملف لتجنب حذف القنوات القديمة.")

if __name__ == "__main__":
    main()
