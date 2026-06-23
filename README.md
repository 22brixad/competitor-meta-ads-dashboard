# 경쟁사 메타 광고 소재 대시보드 (22Brix)

경쟁 광고대행사 14개사의 Meta(Facebook/Instagram/Threads) 광고 소재를 모아
**이미지가 만료되지 않는 공개 갤러리**로 제공하고, **매일 자동 갱신**한다.

- 데이터 소스: Meta Ad Library (팡고뉴로/Pango MCP `competitor_ads__search`)
- 산출물: `index.html` (대행사 필터·검색·신규/종료 배지·통계·반응형) + `assets/` (로컬 보관 이미지)
- 핵심: fbcdn 서명 URL은 수일 내 만료 → 빌드 때 이미지를 `assets/`로 내려받아 **상대경로 참조**(만료 무관). 과거 소재도 누적 보존.

## 파일 구조

| 파일 | 역할 |
|---|---|
| `agencies.json` | 14개사 page_id·표시명·유형 설정 (workspace_id 포함) |
| `normalize.py` | `_raw/<page_id>.json`(MCP 응답 원본) → `ads_all.json` 정규화·머지(누적) |
| `build.py` | `ads_all.json`의 이미지 → `assets/` 다운로드 + `index.html` 생성 |
| `ads_all.json` | 정규화된 광고 데이터(누적). `first_seen`/`last_seen` 포함 |
| `index.html` | 배포되는 정적 대시보드 (self-contained, 데이터 inline) |
| `assets/` | 로컬 보관 이미지(영구) — 반드시 커밋 |
| `HANDOFF.md` | 최초 인수인계 브리프 |

## 로컬에서 보기

```bash
python -m http.server 8778
# http://127.0.0.1:8778/index.html
```

## 수동 갱신 (이미지 재다운로드 + 재빌드만)

```bash
python build.py
```

## 전체 갱신 (신규 광고 수집 → 재빌드) — Pango MCP 필요

MCP는 Python에서 직접 호출 불가. **Claude(MCP 연결됨)가** 다음을 수행한다:

1. `agencies.json`의 각 `page_id`에 대해 `competitor_ads__search` 호출:
   ```
   platform: "meta"
   query: <agency.query>           # 한글명 우선
   meta: { workspace_id, country:"KR", active_status:"all",
           sort_by:"most_recent", page_id:<agency.page_id>, limit:30 }
   ```
   다건 페이지(카페24 등)는 `time_period`를 월별로 나눠 추가 조회.
2. 각 응답(JSON 전체)을 `_raw/<page_id>.json`으로 저장.
3. `python normalize.py` → `ads_all.json` 머지(신규 추가, 기존 보존).
4. `python build.py` → 이미지 다운로드 + `index.html` 재생성.
5. `git add -A && git commit && git push` → GitHub Pages 자동 재배포.

> 상세 절차/프롬프트는 `REFRESH.md` 참고.

## 배포 (GitHub Pages)

저장소를 GitHub에 푸시하고 Settings → Pages → "Deploy from branch / main / root" 설정.
공개 URL: `https://<user>.github.io/<repo>/`

## 주의 (Pango 수집 특성)

- 요청당 최대 ~30건. 카페24처럼 많은 페이지는 기간 분할 후 `ad_archive_id`로 중복 제거.
- DCO 소재는 `body.text`가 `{{product.brand}}` 치환자 → 실제 카피는 `cards[].body`.
- Meta는 비정치 광고의 경우 현재 게재중·최근 중단 위주만 보관(과거 제한) → 누적 머지로 보완.
- 검색은 한글명 우선(영문 "Adriel"은 동명 페이지 오매칭 → "아드리엘").
- 플레이디·애드이피션시: Meta 광고 없음(확인됨).
