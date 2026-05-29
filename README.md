# Fundflow Dashboard

국내 자금 흐름(펀드플로우)의 **일별 증감·잔액**을 한 화면에서 보여주는 정적 웹 대시보드입니다. 데이터 파이프라인으로 매일 갱신해 GitHub Pages로 서빙합니다.

- 🌐 **배포 주소**: https://leeminhong.github.io/fundflow-dashboard/
- 🧩 **기술 스택**: 순수 HTML/CSS/JS(빌드 도구 없음) + Python 데이터 파이프라인
- 📦 **데이터 단위**: 조원.

---

## 목차

1. [한눈에 보기](#1-한눈에-보기)
2. [화면 사용법](#2-화면-사용법)
3. [프로젝트 구조](#3-프로젝트-구조)
4. [데이터 출처](#4-데이터-출처)
5. [데이터 파이프라인 동작 원리](#5-데이터-파이프라인-동작-원리)
6. [데이터 갱신하기](#6-데이터-갱신하기)
7. [로컬에서 띄워 보기](#7-로컬에서-띄워-보기)
8. [개발 · 검사](#8-개발--검사)
9. [자주 묻는 질문](#9-자주-묻는-질문)
10. [커스터마이징 포인트](#10-커스터마이징-포인트)

---

## 1. 한눈에 보기

이 프로젝트는 크게 **두 부분**으로 나뉩니다.

| 부분 | 무엇 | 어디서 도나 |
|------|------|-------------|
| **프론트엔드** | 브라우저에서 보이는 대시보드 (`index.html`, `styles.css`, `app.js`) | 사용자의 웹 브라우저 |
| **데이터 파이프라인** | 외부 사이트에서 데이터를 받아 `data/*.json`으로 가공하는 파이썬 스크립트 | 로컬 PC 또는 CI |

흐름을 한 줄로 요약하면:

> 외부 사이트(한국은행·금융투자협회·예탁결제원) → 파이썬 파이프라인이 받아서 정규화 → `data/fundflow.json` → 브라우저가 그 JSON을 읽어 화면에 그림

프론트엔드는 **서버가 필요 없습니다.** `data/fundflow.json` 한 개만 읽어서 모든 화면(히트맵·추이 차트·요약)을 그립니다. 그래서 GitHub Pages 같은 정적 호스팅으로 충분합니다.

---

## 2. 화면 사용법

대시보드는 세 영역으로 구성됩니다.

- **상단 요약** — 기준일과 섹터별(REPO·투신·증권·은행) 증감/잔액 한 줄 요약.
- **섹터별 히트맵** — 항목 × 날짜 격자. 색이 진할수록 증감이 큽니다(녹색=증가, 빨강=감소). 색의 기준은 절대 증감액이 아니라 **증감률**입니다.
  - `기준일` / `섹터` / `표시 기간`(7·15·30·전체) / `비교 기준`(전일·전주·전월) 필터로 보고 싶은 범위를 조절합니다.
  - `간단히 보기`는 하위 항목을 접어 부모 항목만 보여주고, `초기화`는 모든 필터를 기본값으로 되돌립니다.
  - 처음 열면 스크롤이 **가장 최근 날짜(오른쪽 끝)** 로 맞춰집니다.
- **추이 차트** — 선택한 항목의 시계열. `잔액 추이`(기본) ↔ `증감 추이` 버튼으로 전환하며, `상세` 링크는 해당 항목의 **원본 출처 페이지**로 연결됩니다.

> **기준일이 "잠정치"로 표시될 수 있음**: 메인 소스(FREESIS)가 다른 소스(BOK 등)보다 최신일 때, 그 날짜는 일부 소스가 아직 안 채워진 상태라 "잠정치"로 표시됩니다. 자세한 건 [자주 묻는 질문](#기준일은-어떻게-정해지나요)을 참고하세요.

---

## 3. 프로젝트 구조

```
fundflow-dashboard/
├── index.html                # 페이지 셸 (마크업)
├── styles.css                # 대시보드 스타일
├── app.js                    # 필터 · 히트맵 · 추이 차트 렌더링
│
├── data/
│   ├── fundflow.json         # ★ 프론트가 읽는 최종 웹 데이터 (파이프라인 산출물)
│   └── freesis_db.json       # FREESIS·RP 원천 누적 DB (파이프라인 입력 버퍼)
│
├── scripts/
│   ├── update.sh             # 한 번에 갱신하는 진입점 (FREESIS → BOK 병합)
│   ├── check.sh              # lint(pyflakes) + 테스트(pytest)
│   ├── freesis_final_4.py    # FREESIS 크롤러 → freesis_db.json 누적
│   ├── fetch_bok_market_indicator.py   # 얇은 진입점 (fundflow_pipeline.cli.main 호출)
│   ├── fetch_seibro_repo.js   # SEIBro RP 스크래핑 (Node + Playwright)
│   └── fundflow_pipeline/     # 데이터 가공 메인 패키지
│       ├── cli.py             #   argparse 진입점 main()
│       ├── config.py          #   상수·항목정의(TARGET_ITEMS, FREESIS_*, SECTOR_ORDER)
│       ├── httpfetch.py       #   HTTP + BOK 게시글/RSS 탐색
│       ├── parsing.py         #   값/날짜 변환, 엑셀 워크북 파싱
│       ├── freesis.py         #   예탁금·펀드합산·freesis_db 주입
│       ├── seibro.py          #   SEIBro RP 수집/주입
│       └── webdata.py         #   상태 재계산, build/merge web data, 기준일 산정
│
├── tests/                    # pytest 단위 테스트
└── requirements.txt          # 파이썬 의존성 (openpyxl, requests, pandas)
```

**두 개의 JSON을 구분하세요:**

- `data/freesis_db.json` — FREESIS에서 받은 **원천 데이터를 날짜키로 쌓아두는 버퍼**. 파이프라인의 *입력*입니다.
- `data/fundflow.json` — 모든 소스를 병합·정규화한 **최종 웹 데이터**. 프론트가 읽는 *출력*입니다.

둘 다 **날짜별로 누적**되며, 갱신 시 새 날짜만 추가/덮어쓰기 되고 과거 데이터는 보존됩니다.

---

## 4. 데이터 출처

| 소스 | 사이트 | 가져오는 항목 | 수집 방식 |
|------|--------|---------------|-----------|
| **BOK** (한국은행) | 일일 금융시장 주요지표 | 은행 예금(실세총예금·실세요구불·저축성)·금전신탁, 증권 고객RP·CMA | 게시글의 **엑셀 첨부**를 내려받아 파싱 |
| **FREESIS** (금융투자협회) | 유형별 설정/일임, 증시자금추이 | 투신 펀드/일임 11종 + 합산 3종, 증권 고객예탁금 | **단일 JSON 요청**(`getMetaDataList.do`에 POST, 날짜 범위 지정) |
| **SEIBro** (예탁결제원) | RP 시장현황 | REPO 기관RP | **Playwright**로 페이지 로드 후 테이블 읽기 |

> FREESIS는 공식 공개 API가 아니라 FreeSIS 웹앱의 내부 조회 엔드포인트입니다. JSON을 POST로 보내면 JSON으로 응답하는 구조라, 코드에서는 한 번의 HTTP 요청으로 날짜 범위 전체를 받습니다.

각 소스는 갱신 시점이 서로 다릅니다(특히 BOK는 며칠씩 늦을 수 있음). 그래서 화면의 **기준일은 메인 소스인 FREESIS의 최종 영업일**로 잡습니다([상세](#기준일은-어떻게-정해지나요)).

---

## 5. 데이터 파이프라인 동작 원리

```
[1단계] FREESIS 데이터 조회 (JSON POST)
   scripts/freesis_final_4.py
        └─> data/freesis_db.json  (펀드/일임·고객예탁금·RP를 날짜키로 누적)

[2단계] BOK 엑셀 + freesis_db + SEIBro 를 병합
   scripts/fetch_bok_market_indicator.py
        ├─ BOK 게시글에서 엑셀 첨부 파싱        (은행·증권 일부)
        ├─ data/freesis_db.json 주입            (투신·고객예탁금)
        └─ SEIBro 스크래핑으로 RP 보강          (REPO)
              └─> data/fundflow.json  (기존 파일과 머지: 새 날짜만 추가)
                      └─> index.html + app.js 가 읽어서 렌더링
```

**핵심 포인트**

- **누적 구조**: 매 실행은 "최근 며칠"만 받아도 됩니다. 과거치는 두 DB에 그대로 남고, 증감값은 DB 전체 날짜를 기준으로 다시 계산되므로 짧게 받아도 정확합니다.
- **fetch 창을 짧게 두는 이유**: 자주 돌리는 전제라 속도가 중요합니다.
  - FREESIS는 한 번의 JSON 요청(POST)으로 날짜 범위 전체를 받으므로 범위가 넓어도 빠릅니다 → `freesis_final_4.py`의 `LOOKBACK_DAYS = 10`(최근 10일).
  - BOK는 **날짜마다 엑셀을 받아 파싱**하므로 날짜 수가 곧 소요 시간입니다 → 보통 `--days 1`(최신 1영업일만).
  - SEIBro는 페이지를 한 번만 로드해 테이블을 읽으므로 limit이 커도 느리지 않습니다.
- **머지 규칙**: `fundflow.json`은 기존 레코드를 보존하고 같은 날짜는 덮어써서 stale한 증감값을 교정합니다.

---

## 6. 데이터 갱신하기

### 가장 쉬운 방법 — 한 번에 갱신

```bash
scripts/update.sh
```

이 스크립트가 1·2단계를 순서대로 실행해 `data/fundflow.json`을 재생성합니다. BOK 시드는 고정된 목록 URL을 쓰고 최신 글은 RSS로 자동 탐색하므로, **매번 게시글 번호를 바꿀 필요가 없습니다.**

> 기본 fetch 창: FREESIS 최근 10일 + BOK 최신 1영업일. 노는 날(주말·공휴일)에는 값이 없고 영업일에만 갱신됩니다.

### 단계별로 실행하기

```bash
# 1) FREESIS 누적 수집 (펀드/일임 + 투자자예탁금)
python3 scripts/freesis_final_4.py
#    → data/freesis_db.json 에 날짜키로 누적 머지

# 2) 전체 병합 (BOK + freesis_db + SEIBro → fundflow.json)
python3 scripts/fetch_bok_market_indicator.py \
  'https://www.bok.or.kr/portal/bbs/P0002018/list.do?menuNo=200366' \
  --write-web-data data/fundflow.json \
  --days 1
```

**주요 옵션**

| 옵션 | 설명 |
|------|------|
| `--days N` | BOK 최근 N영업일치 fetch. CLI 기본값은 7이지만 `update.sh`는 **`--days 1`**. BOK는 날짜 수 = 소요시간이라 보통 작게 둡니다. |
| `--freesis-db-json <path>` | `freesis_db.json` 경로 (기본: 자동 탐지) |
| `--skip-seibro-repo` | SEIBro RP 수집 건너뛰기 (`node` 없는 환경 등) |

### 과거치 백필 (가끔 한 번)

기본 창이 짧아서 과거 데이터가 비면, 해당 값만 **일시적으로** 키워서 한 번 돌립니다. 누적 DB라 기존 데이터는 보존됩니다.

```bash
# 예: BOK 약 한 달치를 한 번만 채우기
python3 scripts/fetch_bok_market_indicator.py \
  'https://www.bok.or.kr/portal/bbs/P0002018/list.do?menuNo=200366' \
  --write-web-data data/fundflow.json --days 22

# 예: FREESIS 1년치 백필이 필요하면 freesis_final_4.py 의
#     LOOKBACK_DAYS 값을 365로 잠시 바꿔서 1회 실행 후 되돌리기
```

### 갱신 결과 커밋

```bash
git add data/fundflow.json data/freesis_db.json
git commit -m "chore: update fundflow data"
git push
```

---

## 7. 로컬에서 띄워 보기

빌드가 필요 없습니다. 정적 서버만 하나 띄우면 됩니다.

```bash
python3 -m http.server 4173
```

→ 브라우저에서 http://127.0.0.1:4173/ 접속.

(브라우저가 `styles.css`/`app.js`를 캐시할 수 있으니, 수정이 안 보이면 강력 새로고침하세요.)

---

## 8. 개발 · 검사

파이프라인 코드를 고친 뒤에는 회귀를 막기 위해 검사를 돌립니다.

```bash
scripts/check.sh
```

- `pyflakes` — undefined name / unused import 검사 (패키지 분할 때 났던 import 누락류를 잡음)
- `pytest` — 순수 헬퍼 단위 테스트(`tests/`) 실행

### 커밋 전 자동 검사 (선택)

매 커밋 전에 위 검사를 자동으로 돌리려면 git 훅을 한 번 설치합니다.

```bash
printf '#!/usr/bin/env bash\nexec "$(git rev-parse --show-toplevel)/scripts/check.sh"\n' \
  > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

(긴급 시 우회: `git commit --no-verify`)

---

## 9. 자주 묻는 질문

### 기준일은 어떻게 정해지나요?

화면 상단의 **기준일(default date)** 은 메인 소스인 **FREESIS의 최종 영업일**입니다(`webdata.py`의 `freesis_default_date`).

- BOK·SEIBro는 FREESIS와 갱신 시점이 어긋날 수 있습니다.
- 만약 "모든 소스가 다 채워진 날짜"를 기준으로 잡으면, 가장 늦는 소스(보통 BOK)에 끌려가 기준일이 과거로 후퇴합니다.
- 그래서 메인 데이터인 FREESIS 기준으로 잡고, 아직 다른 소스가 안 채워졌으면 그 날짜를 "잠정치"로 표시합니다.

### SEIBro RP는 어떻게 누적되나요?

SEIBro는 과거 이력을 주지 않아 **초기 1주일치만 수동 백필**했고, 이후 새 날짜는 자동으로 채워집니다(`apply_seibro_repo`의 forward-merge). `node`(Playwright)가 없는 환경에서는 그 단계만 건너뛰고 기존 RP를 그대로 유지합니다.

### 데이터가 일부 날짜에 비어 있어요.

주말·공휴일에는 원본 자체에 값이 없습니다(영업일에만 갱신). 또 소스별 갱신 시차로 최신 날짜 일부가 비어 보일 수 있는데, 다음 실행에서 채워집니다.

---

## 10. 커스터마이징 포인트

| 바꾸고 싶은 것 | 어디를 수정 |
|----------------|-------------|
| 섹터 표시 순서 | `app.js`의 `sectorOrder` (현재 `REPO → 투신 → 증권 → 은행`). 백엔드 `config.py`의 `SECTOR_ORDER`도 동일하게 유지하세요. 표시 순서의 최종 결정권은 `app.js`에 있습니다. |
| FREESIS 수집 기간 | `scripts/freesis_final_4.py`의 `LOOKBACK_DAYS` |
| BOK 수집 일수 | `scripts/update.sh`의 `--days` 값 |
| 항목 정의 / 출처 링크 | `fundflow_pipeline/config.py`의 `TARGET_ITEMS`, `FREESIS_*`, `ITEM_LINK_OVERRIDES` |
