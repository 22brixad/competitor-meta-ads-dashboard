# 매일 자동 갱신 런북 (Claude 예약작업용)

이 문서는 **Claude Code 예약작업(또는 수동 실행)** 이 매일 수행할 절차다.
Pango MCP(`competitor_ads__search`)는 Claude 세션에서만 호출되므로, 신규 광고 수집은
GitHub Actions가 아니라 **Claude가 직접** 수행해야 한다.

## 작업 디렉터리
`D:\Claude\Project\competitor-meta-ads-dashboard`

## 절차

### 1. 신규 소재 수집 (Pango MCP)
`agencies.json`을 읽어 각 항목의 `page_id`마다 호출:

```
도구: mcp__27342b97-...__competitor_ads__search
인자:
  workspace_id: "b76a18a7-33e0-44d0-a3ee-a9f4b215672c"
  platform: "meta"
  query: <agencies[i].query>
  meta: { country:"KR", active_status:"all", sort_by:"most_recent",
          page_id:<agencies[i].page_id>, limit:30 }
```

- 응답 JSON **전체**를 `_raw/<page_id>.json`으로 저장(Write 또는 Bash heredoc).
- `total_results > 30`이면 `time_period`를 최근→과거 월별로 나눠 추가 호출하고
  같은 파일의 `ads` 배열에 합치거나 `_raw/<page_id>_<n>.json`으로 분할 저장
  (normalize는 `<page_id>` prefix만 보므로 분할 시 파일명을 `<page_id>.json` 하나로 병합 권장).

### 2. 정규화·머지
```bash
python normalize.py
```
- `ads_all.json`에 신규 upsert, 기존 보존(누적). 콘솔에 "신규 N / 갱신 M" 출력.

### 3. 이미지 다운로드 + 사이트 빌드
```bash
python build.py
```
- 새 이미지를 `assets/`로 내려받고 `index.html` 재생성. 실패 0 확인.

### 4. 배포 (커밋·푸시 → Pages 자동 반영)
```bash
git add -A
git commit -m "data: 일일 갱신 $(date +%Y-%m-%d) (신규 N건)"
git push
```

### 5. (선택) 신규 요약 알림
`normalize.py` 출력의 신규 건수가 0보다 크면, 신규 항목(대행사·카피 첫 줄·Ad Library 링크)을
Slack/메일로 요약 전송.

## 실패 대응
- 특정 page_id 응답 비어도 중단하지 말 것(해당 대행사 신규 없음일 수 있음).
- 이미지 다운로드 일부 실패는 카드의 Ad Library 링크 폴백으로 처리됨 — 치명적 아님.
- `git push` 인증 실패 시: 원격 URL의 PAT 만료 점검.

## 정리 권장
- `_raw/`는 `.gitignore`에 포함(전이성). 누적 디버그가 필요하면 날짜 폴더로 보관.
