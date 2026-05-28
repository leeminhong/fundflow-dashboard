# Fundflow Dashboard

일별 펀드플로우 증감 현황을 보여주는 정적 대시보드 (부서 내부용).

## 구성

| 파일 | 역할 |
|------|------|
| `index.html` | 페이지 셸 |
| `styles.css` | 대시보드 스타일 |
| `app.js` | 필터 / 히트맵 / 추이 차트 |
| `data/fundflow.json` | 프론트가 읽는 최종 웹 데이터 (빌드 산출물) |
| `data/freesis_db.json` | FREESIS + RP 누적 DB (파이프라인 입력) |

## 데이터 파이프라인

```
freesis_final_4.py (FREESIS API)
    └─> data/freesis_db.json (펀드/예탁금/RP 누적)
                │
BOK 일일 금융시장 주요지표 (웹 엑셀) ─┐
SEIBro RP 스크래핑 ─────────────────┤
                                    └─> fetch_bok_market_indicator.py (병합·정규화)
                                            └─> data/fundflow.json
                                                    └─> index.html + app.js
```

### 데이터 갱신

1. FREESIS 누적 데이터 수집 (펀드/일임 + 투자자예탁금):

   ```bash
   python3 scripts/freesis_final_4.py
   ```

   → `data/freesis_db.json`에 날짜키로 누적 머지됨.

2. 전체 파이프라인 실행 (BOK + freesis_db + RP → fundflow.json):

   ```bash
   python3 scripts/fetch_bok_market_indicator.py \
     '<BOK 금융시장 주요지표 게시글 URL>' \
     --write-web-data data/fundflow.json
   ```

   주요 옵션:
   - `--days 7` (기본): BOK 최근 N일치 fetch
   - `--freesis-db-json <path>`: freesis_db.json 경로 (기본 자동탐지)
   - `--skip-seibro-repo`: SEIBro RP fetch 건너뛰기

   기존 `fundflow.json`과 자동 머지(새 날짜만 추가)됩니다.

3. 커밋:

   ```bash
   git add data/fundflow.json data/freesis_db.json
   git commit -m "Update fundflow data"
   ```

## 로컬 프리뷰

```bash
python3 -m http.server 4173
```

→ http://127.0.0.1:4173/

## 매일 자동 업데이트

데이터는 **날짜별로 누적**됩니다. 매 실행마다 새 날짜만 추가/갱신되어 `data/freesis_db.json`(원천 누적 DB)과 `data/fundflow.json`(웹 데이터)에 계속 쌓입니다 — 과거 데이터는 지워지지 않습니다.

한 번에 갱신하는 명령:

```bash
scripts/update.sh
```

(FREESIS 누적 수집 → BOK + freesis_db + SEIBro 병합 → `data/fundflow.json` 재생성. BOK 시드는 고정 목록 URL을 쓰고 최신 글은 RSS로 자동 탐색하므로 매번 글 번호를 바꿀 필요 없음.)

### 자동화 옵션

**A. GitHub Actions (클라우드)** — `.github/workflows/daily-update.yml`
- 매일 cron으로 `update.sh` 실행 → 갱신된 `data/*.json`을 자동 커밋/푸시 → GitHub Pages가 서빙
- 사전 준비: 리포를 GitHub에 푸시, Settings → Pages에서 브랜치 서빙 활성화, Actions 활성화
- ⚠️ 주의: GitHub 러너는 해외(미국) IP라 BOK/FREESIS/SEIBro(국내 금융 사이트) 접속이 막히거나 불안정할 수 있음. 실패해도 SEIBro 단계는 기존 RP를 유지함

**B. 로컬 스케줄 (권장, 부서 PC가 한국에 있을 때)** — macOS `launchd` 또는 `cron`
- 국내 IP라 사이트 접속이 안정적이고, `node`/Playwright도 이미 설치돼 있음
- 예) crontab에 매일 19시 실행: `0 19 * * * cd /path/to/fundflow-dashboard && scripts/update.sh`

### Playwright / SEIBro 관련 (자주 묻는 질문)

- **GitHub Pages**는 정적 파일만 서빙 — Python/Node/Playwright를 **실행하지 않음**. 그래서 파이프라인은 Pages "위에서" 도는 게 아님.
- 실제 실행은 **GitHub Actions**(또는 로컬 cron)가 담당. Actions에서는 워크플로가 `npx playwright install`로 Playwright를 설치하므로 **동작함**.
- 즉 "Pages에서 Playwright가 안 되는 것"은 정상 — Actions가 데이터를 만들어 커밋하면 Pages는 그 결과만 보여줌.
- SEIBro RP는 과거 이력을 안 줘서 초기 1주일치만 수동 백필했고, 이후 새 날짜는 자동으로 채워짐(`apply_seibro_repo` forward-merge). `node`가 없으면 그 단계만 건너뛰고 기존 RP를 유지.

## 검사 (lint + 테스트)

파이프라인 코드를 고친 뒤 회귀를 막으려면:

```bash
scripts/check.sh
```

- `pyflakes`로 undefined name / unused import 검사 (패키지 분할 때 났던 import 누락류를 잡음)
- `pytest`로 순수 헬퍼 단위 테스트(`tests/`) 실행

### 커밋 시 자동 실행 (선택)

매 커밋 전에 위 검사를 자동으로 돌리려면 git 훅을 한 번 설치:

```bash
printf '#!/usr/bin/env bash\nexec "$(git rev-parse --show-toplevel)/scripts/check.sh"\n' \
  > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

(긴급 시 우회: `git commit --no-verify`)

## 참고

- 섹터 표시 순서의 기준은 `app.js`의 `sectorOrder` (백엔드 `SECTOR_ORDER`도 동일하게 유지).
- 자세한 작업 내역과 코드 포인트는 `HANDOFF.md` 참고.
