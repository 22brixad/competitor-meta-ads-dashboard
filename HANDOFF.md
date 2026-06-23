# 인수인계 브리프 — 경쟁사 메타 광고 소재 대시보드 (22Brix)

> Cowork에서 시작한 작업을 **Claude Code**로 이어받기 위한 문서.
> 목표: 경쟁사 메타(Facebook/Instagram) 광고 소재를 모아 **공개 URL 대시보드**로 만들고, **이미지가 만료되지 않게** 매일 자동 갱신.

---

## 1. 배경 / 목표
- 22Brix(퍼포먼스 광고대행사)가 경쟁 대행사들의 메타 광고 소재를 레퍼런스로 모니터링.
- 데이터 소스: **Meta Ad Library** (팡고뉴로/Pango MCP의 `competitor_ads__search` 도구).
- 최종 산출물: 팀원에게 URL로 공유 가능한 **이미지 갤러리형 대시보드** + **매일 자동 업데이트**.

## 2. Cowork에서 막혔던 점 (= Claude Code로 옮기는 이유)
1. **이미지 미표시**: 앱 내 라이브 아티팩트는 샌드박스라 외부 이미지(fbcdn) 로드 차단.
2. **이미지 만료**: Meta 이미지 URL은 서명형이라 수일 내 만료 → 정적 파일/시트에서 곧 깨짐.
3. **공개 URL 없음**: Cowork엔 호스팅 수단이 없음.
4. **이미지 다운로드 제약 / "앱 켜져 있을 때만" 스케줄 실행**.

→ Claude Code는 실제 셸·네트워크로 **이미지 다운로드+자체 호스팅**, **Netlify/Vercel/GitHub Pages 배포**, **GitHub Actions cron 자동화**가 가능.

## 3. 완료된 것 (재사용 가능)
- `ads_all.json` — 14개사 **93건** 정규화 데이터. 각 항목 필드:
  `agency, page_name, type, ad_archive_id, ad_library_url, start_date, end_date, is_active, platforms, display_format, cta, copy, link_url, images[]`
- `경쟁사_메타광고소재_갤러리_v2.html` — 대행사 필터/카드형 갤러리 (브라우저에서 이미지 표시됨, 디자인 참고용).
- `경쟁사_메타광고소재_레퍼런스_v2.xlsx` — 시트형 정리본(개요 + 목록).
- `competitor_ads_dashboard.html` — 라이브 조회용 JS 로직(아티팩트). MCP 호출/파싱/카드 렌더 코드 참고용.
- 위 파일들은 모두 이 outputs 폴더에 있음.

## 4. 데이터 소스 호출 사양 (팡고뉴로 MCP)
- 도구명: `mcp__27342b97-aa54-442c-b245-661263d5ce4b__competitor_ads__search`
  - (Claude Code에 **Pango MCP를 별도 연결**해야 실시간 재수집 가능. 미연결 시 `ads_all.json`로 빌드만.)
- workspace_id: `b76a18a7-33e0-44d0-a3ee-a9f4b215672c`
- 호출 예:
  ```json
  {
    "workspace_id": "b76a18a7-33e0-44d0-a3ee-a9f4b215672c",
    "platform": "meta",
    "query": "<대행사명>",
    "meta": {
      "country": "KR", "active_status": "all", "sort_by": "most_recent",
      "time_period": "<YYYY-MM-DD..YYYY-MM-DD>", "limit": 30, "page_id": "<page_id>"
    }
  }
  ```
- 응답: `search_information.total_results`, `ads[]`. 각 ad: `ad_archive_id, ad_library_url, start_date, end_date, is_active, publisher_platform[], snapshot{ body.text, cards[]{body, original_image_url, video_preview_image_url, link_url}, images[]{original_image_url}, videos[]{video_preview_image_url}, display_format, cta_text, link_url, title }`.
- 주의:
  - 요청당 **최대 ~30건** 반환. 다건 페이지는 기간을 나눠(예: 월별) 조회 후 `ad_archive_id`로 중복 제거.
  - **DCO** 소재는 `body.text`가 `{{product.brand}}` 치환자 → 실제 카피는 `cards[].body`에서 추출.
  - 이미지 = `snapshot.images[].original_image_url` + `cards[].original_image_url` + (영상은 `video_preview_image_url`).
  - Meta는 비정치 광고의 경우 **현재 게재 중·최근 중단 소재 위주**만 보관(과거 소재 제한).
  - 검색은 한글명 우선(예: 영문 "Adriel"은 동명 페이지 오매칭 → "아드리엘"이 정답).

## 5. 대상 14개사 · 공식 Meta page_id
| # | 대행사 | page_id | 비고 |
|---|--------|---------|------|
| 1 | 카페24 (Cafe24) | 209392889083022 | PRO마케팅/광고대행, 최다 |
| 2 | BAT (비에이티) | 112695639407016 | 수주공지 + 채용 |
| 3 | 매드업 LEVER | 1151942574672091 | 마케팅 솔루션 리드젠 |
| 3b | 매드업 MADUP(본계정) | 1001144700008162 | 채용 위주 |
| 4 | 아드리엘 (Adriel) | 460488137718424 | 광고분석/대시보드 |
| 5 | 헬로맥스 (HELLOMAX) | 875499838973709 | AI 검색광고 대행 |
| 6 | 고위드 (Gowid) | 108268404286774 | 대행사向 핀테크 |
| 7 | 한결기획 | 773706765820227 | 온라인/쿠팡 대행 |
| 8 | 마곳간 | 976365638899816 | 구독형 이커머스 마케팅 |
| 9 | 이노마케팅(그로빗) | 976196155567229 | 셀프 마케팅 플랫폼 |
| 10 | 애드포유 | 407133166516872 | 퍼포먼스 대행 |
| 11 | 메이드코퍼레이션 | 366166373910985 | 브랜드 프로젝트 |
| 12 | 에스앤에이 (S&A) | 1398492283704880 | 패션 광고 대행 |
| 13 | 클래스101 (CLASS101) | 1947160905536967 | 교육 플랫폼 |
| 14 | marketing_fia | 1179539301900128 | GFA/파워링크 대행 |

> 플레이디(PlayD)·애드이피션시: Meta 광고 라이브러리에 자사 집행 광고 없음(확인 완료).

## 6. 남은 작업 (Claude Code 권장 플랜)
1. **데이터 수집/갱신**: Pango MCP로 14개사 페이지 조회 → `ads_all.json` 갱신(중복 제거, DCO 카피 추출). MCP 미연결 시 기존 JSON 사용.
2. **이미지 자체 호스팅**: 각 소재 대표 이미지(영상은 프리뷰)를 `assets/<ad_archive_id>.jpg`로 다운로드 → HTML은 로컬 상대경로 참조 (만료 무관). 다운로드 실패 시 `ad_library_url`로 폴백.
3. **정적 사이트 빌드**: `index.html`(대행사 필터·검색·신규(7일) 하이라이트·통계·반응형). `경쟁사_메타광고소재_갤러리_v2.html` 디자인 재활용.
4. **배포**: Netlify(또는 Vercel/GitHub Pages) → **고정 공개 URL**. 팀 공유.
5. **매일 자동 갱신**: GitHub Actions cron(예: 매일 00:00 KST = `0 15 * * *` UTC)로 1~4 재실행 후 같은 사이트에 재배포. (선택) Slack/메일로 신규 소재 요약 알림.
6. **(선택) 접근제어**: Netlify 비밀번호 보호 또는 팀 전용.

## 7. 바로 쓸 수 있는 시작 프롬프트 (Claude Code에 붙여넣기)
```
이 폴더의 ads_all.json과 경쟁사_메타광고소재_갤러리_v2.html를 기반으로,
경쟁사 메타 광고 소재 갤러리 정적 사이트를 만들어 줘.
- 각 소재 대표 이미지를 assets/ 로 내려받아 상대경로로 참조(만료 방지), 실패 시 ad_library_url 링크 폴백.
- index.html: 대행사 필터, 텍스트 검색, 신규(start_date 최근 7일) 배지, 상단 통계(총건수/대행사수/신규/게재중), 반응형 카드.
- Netlify로 배포해 공개 URL 발급.
- GitHub Actions로 매일 1회 데이터 재수집(가능하면 Pango MCP, 아니면 스킵)→이미지 재다운로드→재빌드→재배포 자동화.
HANDOFF_경쟁사메타광고_대시보드.md의 page_id 목록과 호출 사양을 그대로 사용해.
```

---
작성: 2026-06-22 / Cowork 세션 인수인계
