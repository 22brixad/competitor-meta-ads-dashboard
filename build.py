# -*- coding: utf-8 -*-
"""
경쟁사 메타 광고 소재 갤러리 — 정적 사이트 빌드
1) ads_all.json 의 이미지(fbcdn 서명 URL, 곧 만료)를 assets/ 로 내려받아 영구 보관
2) 로컬 이미지를 참조하는 self-contained index.html 생성 (필터/검색/신규배지/통계/반응형)
   - 이미지 로드 실패 시 Ad Library 링크로 폴백
사용: python build.py
"""
import json, os, html, hashlib, sys, time, datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

# 대행사 표시 순서 (HANDOFF 기준)
ORDER = [
    "카페24 (Cafe24)", "BAT (비에이티)", "매드업 (MADUP / LEVER)", "헬로맥스 (HELLOMAX)",
    "고위드 (Gowid)", "한결기획", "마곳간", "이노마케팅 (그로빗)", "애드포유",
    "메이드코퍼레이션", "에스앤에이 (S&A)", "클래스101 (CLASS101)", "marketing_fia",
    "아드리엘 (Adriel)",
]
PALETTE = ["#2563eb","#16a34a","#9333ea","#0891b2","#ea580c","#db2777","#ca8a04",
           "#0d9488","#dc2626","#7c3aed","#4f46e5","#e11d48","#059669","#64748b"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
}


def asset_name(ad_id, url, idx):
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{ad_id}_{idx}_{h}.jpg"


def download(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True, "cached"
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code == 200 and r.content and len(r.content) > 500:
            with open(dest, "wb") as f:
                f.write(r.content)
            return True, "ok"
        return False, f"http {r.status_code} / {len(r.content)}B"
    except Exception as e:
        return False, str(e)[:60]


def main():
    data = json.load(open(os.path.join(ROOT, "ads_all.json"), encoding="utf-8"))

    # 다운로드 작업 목록 구성: 각 ad 의 모든 이미지
    jobs = []
    for a in data:
        a["local_images"] = [None] * len(a.get("images", []))
        for i, url in enumerate(a.get("images", [])):
            if not url:
                continue
            fn = asset_name(a["ad_archive_id"], url, i)
            jobs.append((a, i, url, os.path.join(ASSETS, fn), fn))

    print(f"[1/3] 이미지 다운로드: {len(jobs)}개 …")
    ok = fail = 0
    fails = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(download, url, dest): (a, i, fn, url)
                for (a, i, url, dest, fn) in jobs}
        for fut in as_completed(futs):
            a, i, fn, url = futs[fut]
            success, msg = fut.result()
            if success:
                a["local_images"][i] = f"assets/{fn}"
                ok += 1
            else:
                fail += 1
                fails.append((a["agency"], a["ad_archive_id"], msg))
    print(f"      성공 {ok} / 실패 {fail}")
    if fails:
        print("      실패 샘플:", fails[:5])

    # 첫 유효 로컬 이미지를 대표 이미지로
    for a in data:
        locals_ = [p for p in a["local_images"] if p]
        a["main_local"] = locals_[0] if locals_ else None
        a["img_count"] = len(a.get("images", []))

    # ---------- index.html ----------
    print("[2/3] index.html 생성 …")
    color = {ag: PALETTE[i % len(PALETTE)] for i, ag in enumerate(ORDER)}
    # 데이터에 색/순서 부여
    oidx = {ag: i for i, ag in enumerate(ORDER)}
    for a in data:
        a["_color"] = color.get(a["agency"], "#64748b")
        a["_ord"] = oidx.get(a["agency"], 99)

    # 클라이언트로 넘길 슬림 레코드
    slim = []
    for a in sorted(data, key=lambda x: (x["_ord"], x["start_date"]), reverse=False):
        slim.append({
            "agency": a["agency"],
            "page": a.get("page_name", ""),
            "type": a.get("type", ""),
            "start": a.get("start_date", ""),
            "end": a.get("end_date", ""),
            "active": bool(a.get("is_active")),
            "platforms": a.get("platforms", ""),
            "fmt": a.get("display_format", ""),
            "cta": a.get("cta", ""),
            "copy": a.get("copy", ""),
            "link": a.get("link_url", ""),
            "lib": a.get("ad_archive_id") and
                   a.get("ad_library_url", ""),
            "img": a.get("main_local"),
            "imgs": [p for p in a["local_images"] if p],
            "n": a.get("img_count", 0),
            "color": a["_color"],
            "ord": a["_ord"],
        })

    agencies = [ag for ag in ORDER if any(s["agency"] == ag for s in slim)]
    meta = {
        "built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "colors": color,
        "order": agencies,
    }
    payload = json.dumps({"ads": slim, "meta": meta}, ensure_ascii=False)

    html_doc = TEMPLATE.replace("/*__DATA__*/", payload)
    out = os.path.join(ROOT, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_doc)

    # 빌드 산출 데이터도 별도 저장(자동화/디버그용)
    with open(os.path.join(ROOT, "ads_built.json"), "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=1)

    print(f"[3/3] 완료 → {out}")
    print(f"      광고 {len(slim)}건 · 대행사 {len(agencies)}개 · 로컬이미지 {ok}장")


TEMPLATE = r"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>경쟁사 메타 광고 소재 대시보드 — 22Brix</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;background:#f4f5f7;color:#1a1a2e}
header{background:linear-gradient(135deg,#1F3864,#2563eb);color:#fff;padding:24px 32px}
header h1{margin:0 0 6px;font-size:22px}
header p{margin:0;opacity:.85;font-size:13px}
.stats{display:flex;gap:14px;flex-wrap:wrap;max-width:1320px;margin:16px auto 0;padding:0 32px}
.stat{background:#fff;border:1px solid #e7e9ee;border-radius:12px;padding:12px 18px;min-width:120px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
.stat .v{font-size:24px;font-weight:700;color:#1F3864}
.stat .l{font-size:12px;color:#64748b;margin-top:2px}
.stat.new .v{color:#dc2626}
.bar{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid #e5e7eb;padding:10px 32px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.search{flex:1;min-width:180px;max-width:340px;border:1px solid #cbd5e1;border-radius:20px;padding:7px 14px;font-size:13px;outline:none}
.search:focus{border-color:#2563eb}
.fbtn{border:1px solid #cbd5e1;background:#fff;border-radius:20px;padding:5px 12px;font-size:12.5px;cursor:pointer;white-space:nowrap}
.fbtn.active{background:#1F3864;color:#fff;border-color:#1F3864}
.toggle{font-size:12.5px;color:#475569;display:flex;align-items:center;gap:5px;cursor:pointer;user-select:none}
.wrap{max-width:1320px;margin:0 auto;padding:18px 32px 60px}
.info{background:#fff7ed;border:1px solid #fed7aa;color:#7c2d12;padding:11px 15px;border-radius:10px;font-size:12.5px;margin:14px 0;line-height:1.6}
.empty{text-align:center;color:#94a3b8;padding:60px 0;font-size:14px}
section{margin:24px 0}
h2{font-size:17px;display:flex;align-items:center;gap:8px;border-bottom:2px solid #eef0f3;padding-bottom:8px}
h2 .dot{width:11px;height:11px;border-radius:50%}
h2 .n{font-size:12px;color:#64748b;font-weight:500}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-top:14px;align-items:start}
.card{background:#fff;border:1px solid #e7e9ee;border-radius:12px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 1px 2px rgba(0,0,0,.04);position:relative}
.imgwrap{position:relative;display:block;background:#0f172a;overflow:hidden;min-height:150px}
.imgwrap img{width:100%;height:auto;display:block}
.imgwrap .ph{display:none;position:absolute;inset:0;align-items:center;justify-content:center;text-align:center;color:#94a3b8;font-size:12px;line-height:1.5;padding:40px 12px}
.imgwrap.noimg{background:#1e293b;min-height:150px}
.imgwrap.noimg .ph{display:flex}
.cnt{position:absolute;right:8px;bottom:8px;background:rgba(0,0,0,.7);color:#fff;font-size:11px;padding:2px 8px;border-radius:10px}
.badge-new{position:absolute;left:8px;top:8px;background:#dc2626;color:#fff;font-size:10.5px;font-weight:700;padding:3px 8px;border-radius:6px;letter-spacing:.3px}
.badge-off{position:absolute;left:8px;top:8px;background:#64748b;color:#fff;font-size:10.5px;padding:3px 8px;border-radius:6px}
.body{padding:12px;display:flex;flex-direction:column;gap:8px;flex:1}
.meta{display:flex;justify-content:space-between;font-size:11px;color:#64748b;gap:6px}
.plat{text-align:right;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:55%}
.copy{margin:0;font-size:12.5px;line-height:1.5;color:#27303f;white-space:pre-wrap}
.chips{display:flex;gap:5px;flex-wrap:wrap;margin-top:auto}
.chip{font-size:10.5px;background:#eef2ff;color:#3730a3;padding:2px 7px;border-radius:6px}
.chip.type{background:#ecfdf5;color:#065f46}
.chip.cta{background:#fef3c7;color:#92400e}
.link{font-size:12px;color:#2563eb;text-decoration:none}
.link:hover{text-decoration:underline}
footer{text-align:center;color:#94a3b8;font-size:12px;padding:24px;line-height:1.7}
@media(max-width:640px){header,.bar,.wrap,.stats{padding-left:16px;padding-right:16px}.grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}}
</style></head><body>
<header>
  <h1>경쟁사 메타 광고 소재 대시보드</h1>
  <p id="sub">22Brix · Meta Ad Library 수집</p>
</header>
<div class="stats" id="stats"></div>
<div class="bar">
  <input class="search" id="q" placeholder="🔍 카피·대행사·CTA 검색…" autocomplete="off">
  <button class="fbtn active" data-f="all">전체</button>
  <span id="filters"></span>
  <label class="toggle"><input type="checkbox" id="onlyNew"> 신규(7일)만</label>
  <label class="toggle"><input type="checkbox" id="onlyActive"> 게재중만</label>
</div>
<div class="wrap">
  <div class="info"><b>참고</b> · 이미지는 빌드 시점에 로컬로 내려받아 보관(만료 무관). 누락분은 카드의 <b>Ad Library</b> 링크로 원본 확인. 플레이디·애드이피션시는 Meta 광고 없음. 채용 광고는 참고용 포함.</div>
  <div id="sections"></div>
  <div class="empty" id="empty" style="display:none">검색 결과가 없습니다.</div>
</div>
<footer id="foot"></footer>
<script>
const DATA = /*__DATA__*/;
const ADS = DATA.ads, META = DATA.meta;
const COLORS = META.colors, ORDER = META.order;
const esc = s => (s||"").replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const today = new Date();
const daysAgo = d => { if(!d) return 9999; const t=new Date(d+'T00:00:00'); return (today-t)/86400000; };
const isNew = a => daysAgo(a.start) <= 7;

// 통계
const total = ADS.length;
const nAg = ORDER.length;
const nNew = ADS.filter(isNew).length;
const nActive = ADS.filter(a=>a.active).length;
document.getElementById('sub').textContent =
  `22Brix · Meta Ad Library 수집 · 빌드 ${META.built} · ${nAg}개사 · ${total}건`;
document.getElementById('stats').innerHTML = [
  ['총 소재', total, ''],
  ['대행사', nAg, ''],
  ['신규 (7일)', nNew, 'new'],
  ['게재중', nActive, ''],
].map(([l,v,c])=>`<div class="stat ${c}"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');

// 필터 버튼
document.getElementById('filters').innerHTML = ORDER.map(ag=>
  `<button class="fbtn" data-f="${esc(ag)}">${esc(ag.split(' (')[0])}</button>`).join('');

let curFilter='all';
function card(a){
  const main=a.img;
  const cntBadge = a.n>1 ? `<span class="cnt">+${a.n-1}</span>` : '';
  const newBadge = isNew(a) ? `<span class="badge-new">NEW</span>` :
                   (!a.active ? `<span class="badge-off">종료</span>` : '');
  const img = main
    ? `<a href="${esc(a.lib)}" target="_blank" class="imgwrap"><img loading="lazy" src="${esc(main)}" onerror="this.parentElement.classList.add('noimg');this.remove();" alt="">${newBadge}${cntBadge}<span class="ph">이미지 없음<br>Ad Library에서 확인</span></a>`
    : `<a href="${esc(a.lib)}" target="_blank" class="imgwrap noimg">${newBadge}<span class="ph">이미지 없음<br>Ad Library에서 확인</span></a>`;
  const copy=esc(a.copy);
  const cs = copy.length>220 ? copy.slice(0,220)+'…' : copy;
  let chips=`<span class="chip">${esc(a.fmt)}</span>`;
  if(a.cta) chips+=`<span class="chip cta">${esc(a.cta)}</span>`;
  if(a.type) chips+=`<span class="chip type">${esc(a.type)}</span>`;
  return `<div class="card">${img}<div class="body">
    <div class="meta"><span>📅 ${esc(a.start)}${a.end&&a.end!==a.start?' ~ '+esc(a.end):''}</span><span class="plat">${esc((a.platforms||'').replace(/,/g,' · '))}</span></div>
    <p class="copy" title="${copy}">${cs}</p>
    <div class="chips">${chips}</div>
    <a class="link" href="${esc(a.lib)}" target="_blank">Ad Library 원본 →</a>
  </div></div>`;
}

function render(){
  const q = document.getElementById('q').value.trim().toLowerCase();
  const onlyNew = document.getElementById('onlyNew').checked;
  const onlyActive = document.getElementById('onlyActive').checked;
  const match = a => {
    if(curFilter!=='all' && a.agency!==curFilter) return false;
    if(onlyNew && !isNew(a)) return false;
    if(onlyActive && !a.active) return false;
    if(q){
      const hay=(a.copy+' '+a.agency+' '+a.cta+' '+a.type+' '+a.page+' '+a.fmt).toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  };
  const shown = ADS.filter(match);
  const byAg = {};
  shown.forEach(a=>{ (byAg[a.agency]=byAg[a.agency]||[]).push(a); });
  let htmlOut='';
  ORDER.forEach(ag=>{
    const items=(byAg[ag]||[]).sort((x,y)=>(y.start||'').localeCompare(x.start||''));
    if(!items.length) return;
    htmlOut += `<section><h2><span class="dot" style="background:${COLORS[ag]||'#64748b'}"></span>${esc(ag)} <span class="n">${items.length}건</span></h2><div class="grid">${items.map(card).join('')}</div></section>`;
  });
  document.getElementById('sections').innerHTML=htmlOut;
  document.getElementById('empty').style.display = shown.length? 'none':'block';
}

document.querySelectorAll('.fbtn').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.fbtn').forEach(x=>x.classList.remove('active'));
  b.classList.add('active'); curFilter=b.dataset.f; render();
});
['q','onlyNew','onlyActive'].forEach(id=>document.getElementById(id).addEventListener('input',render));
document.getElementById('foot').innerHTML =
  `이미지는 빌드 시점(${META.built})에 로컬 저장됨 · 원본은 Ad Library 링크 참조 · 22Brix 내부 레퍼런스`;
render();
</script>
</body></html>"""


if __name__ == "__main__":
    main()
