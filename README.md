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

## 참고

- 섹터 표시 순서의 기준은 `app.js`의 `sectorOrder` (백엔드 `SECTOR_ORDER`도 동일하게 유지).
- 자세한 작업 내역과 코드 포인트는 `HANDOFF.md` 참고.
