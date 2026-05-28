# Fundflow Dashboard Handoff

## 프로젝트 경로

- `/Users/minhonglee/Documents/fundflow-dashboard`

## 목표

- 일별 자금흐름 대시보드(히트맵 중심) 운영
- 기준일은 "모든 필수 항목이 채워진 마지막 날짜(`defaultDate`)"
- 최신 날짜(`latestDate`)가 더 뒤여도, 미완성 항목이면 `업데이트 필요`로 표시

## 핵심 데이터 소스

1. BOK(한국은행) "일일 금융시장 주요지표" 첨부 엑셀
2. FREESIS 요약 엑셀(투신 세부 항목 11개)
3. SEIBro Repo 일별거래현황(잔고금액) 웹 스크래핑

## 현재 반영된 주요 설계

- RP는 두 종류를 분리함
  - 증권 섹터 기존 항목: 대고객RP매도 (`itemCode: SEC_CUSTOMER_RP`)
  - REPO 섹터 신규 항목: 기관RP (`itemCode: REPO_INTERBANK`, SEIBro 기반)
- REPO/기관RP는 SEIBro의 "잔고금액(단위: 십억원)"에서 가져와 증감 계산
  - 조원 변환: `balanceValue = 잔고금액 / 100`
  - `changeValue = 당일 balanceValue - 직전 balanceValue`
  - 소수 처리는 반올림 적용

## 수정된 파일

- `/Users/minhonglee/Documents/fundflow-dashboard/scripts/fetch_bok_market_indicator.py`
  - BOK 수집 + FREESIS 병합 + SEIBro 병합까지 총괄
  - 추가 옵션:
    - `--skip-seibro-repo`
    - `--seibro-repo-limit` (기본 7)
- `/Users/minhonglee/Documents/fundflow-dashboard/scripts/fetch_seibro_repo.js`
  - Playwright로 SEIBro 화면 렌더 후 표 데이터 추출
  - 출력: JSON 배열(`date`, `tradeAmountBillion`, `balanceAmountBillion`)
- `/Users/minhonglee/Documents/fundflow-dashboard/data/fundflow.json`
  - 최종 웹 데이터

## 실행 명령(현재 파이프라인)

```bash
cd /Users/minhonglee/Documents/fundflow-dashboard
python3 scripts/fetch_bok_market_indicator.py 'https://www.bok.or.kr/portal/bbs/P0002018/view.do?nttId=10098154&menuNo=200366' --days 7 --write-web-data data/fundflow.json --freesis-summary-xlsx 'freesis_크레딧채권운용_20260528_1303.xlsx'
```

## SEIBro 스크립트 단독 테스트

```bash
node /Users/minhonglee/Documents/fundflow-dashboard/scripts/fetch_seibro_repo.js --limit 5
```

## 주의사항

- SEIBro 수집은 Playwright 브라우저 설치 필요
- 현재 데이터 구조는 하드코딩 최소화 방향이지만, 일부 `itemCode`/표시순서는 스크립트에 정의되어 있음
- UI는 `data/fundflow.json`의 `meta.defaultDate`를 기준일로 사용하도록 맞춰져 있음
- `latestDate`가 더 최신이어도 필수 항목 미완이면 `defaultDate`를 유지하고 `업데이트 필요` 표시

## 현재 상태 요약

- `sectors`: 은행, REPO, 투신, 증권
- REPO/기관RP가 정상 반영되어 있음
- `defaultDate`는 완전입력 기준으로 유지되는 로직 정상

## TODO

### 1. 용어와 항목명 확정

- `REPO/기관RP` 항목명을 최종 확정
  - 후보: `기관RP`, `기관간Repo`, `기관간 RP`
- `증권/대고객RP매도`와 `REPO/기관RP`가 서로 다른 데이터임을 UI나 문서에서 구분
- `SEC_CUSTOMER_RP`의 링크가 현재 SEIBro로 되어 있는데, 나중에 더 적절한 출처가 있으면 교체

### 2. 데이터 소스 안정화

- BOK "금융시장 주요지표" 최신 게시글을 사용자가 매번 URL로 넣지 않아도 되게 자동 탐색 개선
- FREESIS 엑셀 생성 스크립트와 `fetch_bok_market_indicator.py`를 하나의 실행 흐름으로 묶기
- SEIBro 수집은 현재 Playwright 렌더링 방식이므로, 가능하면 실제 백엔드 호출/API 형태를 찾아 더 가볍게 전환
- SEIBro 페이지 구조가 바뀌었을 때 실패 원인을 알 수 있도록 에러 메시지와 로그 보강

### 3. 날짜 정합성 규칙 정리

- 현재 `defaultDate`는 모든 필수 항목이 채워진 마지막 날짜
- `latestDate`는 일부 항목만 있어도 최신 날짜로 잡힘
- 앞으로 항목별 데이터 시차가 달라질 수 있으므로, 항목별 최신일과 전체 기준일을 함께 보여줄지 검토
- 주말/공휴일처럼 특정 소스만 날짜가 없는 경우를 `미입력`과 구분할 방법 검토

### 4. 대시보드 UI 개선

- 날짜가 계속 쌓일 때 히트맵이 너무 길어지지 않도록 기본 표시 기간 유지
  - 현재는 최근 기간 선택 방식
  - 추후 월별/주별 접기 또는 날짜 슬라이더 검토
- `업데이트 필요` 날짜를 선택했을 때 어떤 항목이 빠졌는지 더 보기 쉽게 표시
- 항목 수가 늘어나면 섹터별 접기/펼치기 또는 섹터 탭 도입 검토
- `REPO` 섹터가 새로 추가되었으므로 화면에서 순서와 카드 표시가 자연스러운지 확인

### 5. 자동화 준비

- 매일 한 번 데이터 갱신하는 실행 명령을 별도 스크립트로 만들기
  - 예: `scripts/update_all_data.sh` 또는 `scripts/update_all_data.py`
- GitHub Pages로 배포할 경우, 데이터 갱신 후 `data/fundflow.json`만 커밋/푸시하면 되는 흐름으로 정리
- GitHub Actions에서 매일 자동 실행할지 검토
  - Playwright 설치가 필요하므로 Actions 설정에 브라우저 설치 단계 포함 필요
- API 키가 필요한 소스가 생기면 공개 repo에 직접 넣지 않고 GitHub Secrets로 관리

### 6. 테스트와 검증

- `python3 -m py_compile scripts/fetch_bok_market_indicator.py`
- `node --check scripts/fetch_seibro_repo.js`
- `node scripts/fetch_seibro_repo.js --limit 5`
- 데이터 생성 후 `data/fundflow.json`에서 확인할 것
  - `sectors`에 `REPO` 포함
  - `items`에 `REPO_INTERBANK` 포함
  - `records`에 `REPO_INTERBANK` 날짜별 값 포함
  - `meta.defaultDate`가 완전 입력일로 유지

### 7. 중장기 구조 개선

- 항목 정의(`itemCode`, `sector`, `displayOrder`, 링크)를 Python 코드에서 별도 JSON/YAML 설정 파일로 분리
- 모든 원천 데이터를 최종적으로 같은 정규화 구조로 통일
  - `date`
  - `sector`
  - `itemCode`
  - `itemName`
  - `changeValue`
  - `balanceValue`
  - `link`
  - `source`
- 엑셀 기반 MVP보다 웹 자동화에 더 가까운 구조로 이동
- 향후 은행/투신/증권/REPO 외 섹터가 늘어나도 코드 수정 없이 설정 추가만으로 반영되게 개선
