# Fundflow Dashboard Handoff

## 프로젝트 경로

`/Users/minhonglee/Documents/fundflow-dashboard`

---

## 이번 세션에서 한 일

### 1. FREESIS 1년 확장 + JSON DB 누적 저장

- `freesis_final_4.py`: 기간 7일 → 365일(1년)로 확장
- 증시자금 기간도 90일 → 365일로 통일
- `data/freesis_db.json`에 날짜키로 누적 저장 로직 추가
  - `fundSummary`: 11개 펀드/일임 조합 (억원 단위)
  - `fundChanges`: 일별 증감 (억원 단위)
  - `stockDeposit`: 투자자예탁금 (백만원 단위)
  - `stockDepositChanges`: 일별 증감 (백만원 단위)
  - `repoBalance`: RP 잔고금액 (조원 단위, 수동 입력)
  - `repoChanges`: RP 일별 증감 (조원 단위)
  - `lastUpdated`: 최종 업데이트 시각

### 2. freesis_db.json 자동 탐지 + 증분 업데이트

- `fetch_bok_market_indicator.py`에 `apply_freesis_db()` 함수 추가
  - freesis_db.json에서 펀드/일임 + 투자자예탁금 + RP 데이터 자동 주입
- `merge_web_data()` 함수 추가
  - 기존 fundflow.json과 새 데이터를 날짜별로 머지
  - 새 레코드는 덮어쓰기 (stale change 값 교정)
- `--freesis-db-json` CLI 인자 추가, 자동탐지 기본값
- `--days` 기본값 1 → 7로 변경

### 3. 단위 오류 수정

- **FREESIS change 값**: `freesis_db.json`에 `fundChanges`/`stockDepositChanges` 필드 추가
  - 이전: balance만 저장 → 나중에 재계산 시 날짜 간 간격 달라서 연간 누적값 나옴
  - 이후: 일별 증감을 직접 저장 → `apply_freesis_db()`에서 그대로 사용
- **SEIBro 기관RP**: 변환 계수 `/100` → `/1000` 수정
  - SEIBro 페이지 확인: "단위: 십억원" (10억원 단위)
  - 275,207 십억원 = 275.2조원 (기존 2,752조원은 10배 과대)

### 4. RP 잔고금액 DB 저장

- 사용자가 제공한 RP 잔고 데이터(4/29~5/22)를 `freesis_db.json`에 수동 입력
- `apply_freesis_db()`에서 RP 데이터 자동 주입 로직 추가
- DB에 REPO 데이터 있으면 SEIBro 자동 fetch 건너뛰기
- 5/16 → 5/18 데이터 수정 (사용자 확인)

### 5. 섹터 순서 시도 (원복)

- REPO→투신→증권→은행 순서 시도했으나 UI에 반영 안 됨
- 원래대로 은행→REPO→투신→증권으로 복구

---

## 현재 파일 구조

```
fundflow-dashboard/
├── index.html                  # 대시보드 HTML
├── styles.css                  # 스타일 (계층 표시 포함)
├── app.js                      # 프론트엔드 로직
├── data/
│   ├── fundflow.json           # 최종 웹 데이터 (22개 항목, 244일)
│   └── freesis_db.json         # FREESIS + RP 누적 DB
├── scripts/
│   ├── fetch_bok_market_indicator.py   # 메인 파이프라인 (BOK+FREESIS DB+SEIBro)
│   ├── freesis_final_4.py              # FREESIS API 크롤러 → freesis_db.json
│   └── fetch_seibro_repo.js            # SEIBro Repo 스크래핑 (Playwright)
# 레거시 MVP 스크립트(extract_fundflow_source.py, build_web_data.py, freesis_final_3.py)는 제거됨
└── outputs/
    ├── bok_market_indicator/    # BOK 엑셀/JSON 다운로드
    └── fundflow_mvp/            # MVP 빌더 출력물
```

---

## 실행 방법

### 1. FREESIS 데이터 수집 (1년치 누적)

```bash
cd /Users/minhonglee/Documents/fundflow-dashboard
python3 scripts/freesis_final_4.py
```

출력:
- `freesis_크레딧채권운용_YYYYMMDD_HHMM.xlsx` (타임스탬프 Excel)
- `data/freesis_db.json` (누적 DB, 매번 머지)

### 2. 전체 파이프라인 (BOK + FREESIS DB + RP DB → fundflow.json)

```bash
python3 scripts/fetch_bok_market_indicator.py \
  'https://www.bok.or.kr/portal/bbs/P0002018/view.do?nttId=...&menuNo=200366' \
  --write-web-data data/fundflow.json
```

- `--days 7` (기본값): BOK 최근 7일치 fetch
- `--freesis-db-json`: freesis_db.json 경로 (자동탐지 가능)
- `--skip-seibro-repo`: SEIBro 건너뛰기
- 기존 fundflow.json과 자동 머지 (새 날짜만 추가)

### 3. 로컬 프리뷰

```bash
python3 -m http.server 8080
```

→ http://localhost:8080/

---

## 데이터 흐름

```
freesis_final_4.py (FREESIS API)
    ↓
data/freesis_db.json (누적 DB)
  - fundSummary/fundChanges: 11개 펀드/일임 조합 (1년)
  - stockDeposit/stockDepositChanges: 투자자예탁금 (1년)
  - repoBalance/repoChanges: RP 잔고금액 (수동/자동)

BOK 웹사이트 (한국은행 일일 금융시장 주요지표)
    ↓
fetch_bok_market_indicator.py
    ↓
  + freesis_db.json 자동 읽기 → 투신 11개 child + 3개 calculated parent
  + freesis_db.json → 증권 고객예탁금
  + freesis_db.json → REPO 기관RP (있으면 SEIBro 자동 fetch 건너뜀)
    ↓
  merge_web_data() ← 기존 fundflow.json과 머지
    ↓
data/fundflow.json (22개 항목, 244일)
    ↓
index.html + app.js (정적 대시보드)
```

---

## 핵심 코드 포인트

### `fetch_bok_market_indicator.py`

| 위치 | 내용 |
|------|------|
| `FREESIS_CALCULATED_PARENTS` | MMF/채권/주식 부모 정의, children 목록 |
| `FREESIS_FUND_ITEMS` | 11개 child 항목 정의 (`parentCode`, `displayOrder`) |
| `TARGET_ITEMS` | BOK 기반 항목 정의 |
| `SECTOR_ORDER` | 섹터 정렬 순서 (은행→REPO→투신→증권) |
| `apply_freesis_db()` | freesis_db.json에서 펀드+예탁금+RP 자동 주입 |
| `merge_web_data()` | 기존 JSON과 새 데이터 머지 (덮어쓰기) |
| `apply_seibro_repo()` | SEIBro RP 데이터 주입 (DB에 없을 때만) |
| `recompute_status_summary()` | dateStatus 재계산 (calculated 항목 skip) |

### `freesis_final_4.py`

| 위치 | 내용 |
|------|------|
| `START_DATE` / `END_DATE` | 365일(1년) 범위 |
| `save_to_db()` | freesis_db.json 누적 저장 (fundSummary + fundChanges + stockDeposit + stockDepositChanges) |
| `EXTRACT` | 11개 조합 (채권/MMF/주식 × 공모/사모/일임 × 국내/해외) |

### `app.js`

| 위치 | 내용 |
|------|------|
| `byDisplayOrder()` | displayOrder → itemName 순 정렬 |
| `renderHeatmap()` | level/parentCode 기반 계층 렌더링, `heatmap-parent`/`heatmap-child` CSS 클래스 |

### `styles.css`

| 클래스 | 내용 |
|--------|------|
| `.heatmap-parent` | font-weight: 800 (부모 항목 볼드) |
| `.heatmap-child` | color: muted, padding-left, `└ ` prefix via ::before |

---

## 알려진 이슈

1. ~~**섹터 순서 변경**: `SECTOR_ORDER`를 바꿔도 UI에 반영 안 됨~~ → **해결됨**: 원인은 `app.js`의 하드코딩된 `sectorOrder`가 표시 순서를 최종 결정하기 때문. 백엔드 `SECTOR_ORDER`는 JSON의 `sectors` 배열/정렬에만 영향을 주고 프론트가 재정렬하므로 무시됨. 현재는 `app.js`와 `fetch_bok_market_indicator.py` 모두 `REPO→투신→증권→은행`으로 통일(레거시 `build_web_data.py`는 제거됨). 표시 순서를 바꾸려면 `app.js`의 `sectorOrder`를 수정할 것.
2. **FREESIS 데이터 시차**: 투신 데이터는 FREESIS API 기준. BOK 데이터와 날짜가 안 맞을 수 있음
3. **REPO 수동 입력**: RP 잔고금액은 `freesis_db.json`에 수동으로 넣어야 함 (SEIBro 자동 fetch도 가능하나 현재 DB 우선)

---

## 남은 작업 (TODO)

### UI 리디자인

유저 피드백: "지금은 너무 AI스럽다"
- 폰트, 색상, 레이아웃, 카드 스타일 등 전반적 리디자인 필요

### 기타

- `.gitignore`에 `__pycache__/` 추가
- GitHub Pages 배포 자동화
- 항목 정의를 별도 설정 파일로 분리
- RP 데이터 수동 입력 → 자동화 (SEIBro fetch 개선)

---

## Git 커밋 히스토리

```
49ed45f revert: 섹터 순서 원래대로 복구 (은행→REPO→투신→증권)
6c882a8 fix: 섹터 순서 변경 REPO→투신→증권→은행
57534a9 fix: fundflow.json에서 RP 5/16 중복 데이터 삭제
18d7164 fix: RP 5/16→5/18 데이터 수정
2f9d0e3 feat: RP 잔고금액 DB 저장 + 자동 적용
78b4751 fix: SEIBro 기관RP 단위 수정 (십억원→조원 변환 계수 /100→/1000)
a88f36b fix: FREESIS change 값 단위 오류 수정
9a3d440 feat: FREESIS DB 자동탐지 + 증분 업데이트 (merge) 지원
2386a85 feat: FREESIS 기간 1년 확장 + JSON DB 누적 저장
373035c Restructure dashboard items into parent-child hierarchy with auto-summing parents
254318e Regenerate fundflow.json with FREESIS final4 data
16dc3f3 Initial commit: fundflow dashboard with FREESIS 증시자금추이 → 고객예탁금 integration
```
