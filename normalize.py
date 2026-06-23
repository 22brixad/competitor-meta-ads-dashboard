# -*- coding: utf-8 -*-
"""
_raw/<page_id>.json (competitor_ads__search 의 meta 응답 원본) → ads_all.json 정규화/머지.

- DCO/캐러셀: 실제 카피는 cards[].body (body.text 가 {{product.brand}} 치환자일 때).
- 이미지: snapshot.images[].original_image_url + cards[].original_image_url + videos[].video_preview_image_url (중복 제거, 순서 보존).
- 날짜: ISO(...T..Z) → YYYY-MM-DD.
- 머지: 기존 ads_all.json 을 보존하고 ad_archive_id 로 upsert.
  라이브러리에서 사라진 과거 소재도 유지 → 만료 방지 + 히스토리 누적.
  (first_seen 최초 수집일 보존, last_seen 갱신.)

사용: python normalize.py        # _raw/ 전체 정규화 후 ads_all.json 머지 저장
"""
import json, os, glob, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "_raw")
CFG = json.load(open(os.path.join(ROOT, "agencies.json"), encoding="utf-8"))
ADS_PATH = os.path.join(ROOT, "ads_all.json")

# page_id -> {agency, type}
PMETA = {a["page_id"]: a for a in CFG["agencies"]}
TODAY = datetime.date.today().isoformat()


def d(iso):
    return (iso or "")[:10]


def uniq(seq):
    seen, out = set(), []
    for x in seq:
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out


def extract_images(snap):
    imgs = []
    for im in snap.get("images") or []:
        imgs.append(im.get("original_image_url"))
    for c in snap.get("cards") or []:
        imgs.append(c.get("original_image_url"))
    for v in snap.get("videos") or []:
        imgs.append(v.get("video_preview_image_url") or v.get("video_sd_url"))
    return uniq(imgs)


def extract_copy(snap):
    body = ((snap.get("body") or {}).get("text") or "").strip()
    # DCO/치환자면 카드 본문 사용
    if (not body) or "{{" in body:
        for c in snap.get("cards") or []:
            if c.get("body"):
                return c["body"].strip()
    return body


def to_record(ad, pmeta):
    snap = ad.get("snapshot") or {}
    imgs = extract_images(snap)
    plats = ad.get("publisher_platform") or []
    cta = snap.get("cta_text") or ""
    if not cta:
        for c in snap.get("cards") or []:
            if c.get("cta_text"):
                cta = c["cta_text"]; break
    link = snap.get("link_url") or ""
    if not link or "{{" in link:
        for c in snap.get("cards") or []:
            if c.get("link_url"):
                link = c["link_url"]; break
    return {
        "agency": pmeta["agency"],
        "page_name": ad.get("page_name", ""),
        "ad_archive_id": str(ad.get("ad_archive_id")),
        "ad_library_url": ad.get("ad_library_url")
            or f"https://www.facebook.com/ads/library/?id={ad.get('ad_archive_id')}",
        "start_date": d(ad.get("start_date")),
        "end_date": d(ad.get("end_date")),
        "is_active": bool(ad.get("is_active")),
        "platforms": ",".join(plats),
        "display_format": snap.get("display_format") or "",
        "cta": cta,
        "copy": extract_copy(snap),
        "link_url": link if "{{" not in (link or "") else "",
        "images": imgs,
        "type": pmeta.get("type", "자사홍보"),
    }


def main():
    # 기존 데이터 로드 (머지 기준)
    existing = {}
    if os.path.exists(ADS_PATH):
        for a in json.load(open(ADS_PATH, encoding="utf-8")):
            existing[str(a["ad_archive_id"])] = a

    raw_files = sorted(glob.glob(os.path.join(RAW, "*.json")))
    print(f"[normalize] _raw 파일 {len(raw_files)}개, 기존 {len(existing)}건")
    fresh = added = updated = 0
    for fp in raw_files:
        page_id = os.path.splitext(os.path.basename(fp))[0]
        pmeta = PMETA.get(page_id)
        if not pmeta:
            print(f"  ! page_id {page_id} 가 agencies.json 에 없음 — 건너뜀")
            continue
        try:
            resp = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            print(f"  ! {fp} 파싱 실패: {e}"); continue
        ads = resp.get("ads") or []
        for ad in ads:
            rec = to_record(ad, pmeta)
            aid = rec["ad_archive_id"]
            fresh += 1
            if aid in existing:
                old = existing[aid]
                rec["first_seen"] = old.get("first_seen", old.get("start_date", TODAY))
                # 기존 로컬 이미지가 있으면 이미지 URL은 새것으로 갱신하되 보존은 build가 처리
                rec["last_seen"] = TODAY
                # 이미지가 비면 기존 유지
                if not rec["images"]:
                    rec["images"] = old.get("images", [])
                existing[aid] = rec
                updated += 1
            else:
                rec["first_seen"] = rec["start_date"] or TODAY
                rec["last_seen"] = TODAY
                existing[aid] = rec
                added += 1

    out = list(existing.values())
    json.dump(out, open(ADS_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[normalize] 신규수집 {fresh} (신규 {added} / 갱신 {updated}) → 총 {len(out)}건 저장")


if __name__ == "__main__":
    main()
