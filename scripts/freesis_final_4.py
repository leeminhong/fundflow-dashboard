"""
FREESIS 크레딧채권 운용 + 증시자금 크롤러 (최종)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] 유형별기간설정 - 9개 조합
    펀드(설정원본): 공모국내채권/사모국내채권/공모국내주식/공모해외주식/사모국내주식/사모해외주식
    투자일임(계약금액): 일임국내채권/일임국내주식/일임해외주식

[2] 증시자금추이
    투자자예탁금(장내파생상품거래예수금제외)

사용법:
  pip install requests pandas openpyxl
  python freesis_final.py
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END_DATE   = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
# 증시자금도 동일하게 1년
STOCK_START = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
OUTPUT     = f"freesis_크레딧채권운용_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
DB_JSON    = Path(__file__).resolve().parent.parent / "data" / "freesis_db.json"

API_URL  = "https://freesis.kofia.or.kr/meta/getMetaDataList.do"
INIT_URL = ("https://freesis.kofia.or.kr/stat/FreeSIS.do"
            "?parentDivId=MSIS40100000000000"
            "&serviceId=STATFND0100100260")

# 유형별기간설정 컬럼 매핑
FUND_COL_MAP = {
    "TMPV1": "기준일자", "TMPV2": "주식", "TMPV3": "혼합주식",
    "TMPV4": "혼합채권", "TMPV5": "채권", "TMPV6": "재간접",
    "TMPV7": "단기금융", "TMPV8": "파생형", "TMPV9": "부동산",
    "TMPV10": "실물", "TMPV11": "특별자산", "TMPV12": "혼합자산",
    "TMPV13": "기관전용사모", "TMPV14": "투자일임기타", "TMPV15": "합계",
    "TMPV16": "전일대비", "TMPV17": "전월대비", "TMPV18": "전년대비",
    "TMPV19": "투자계약", "TMPV20": "기업성장",
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  세션
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
session = requests.Session()
session.headers.update({
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":      INIT_URL,
    "Origin":       "https://freesis.kofia.or.kr",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept":       "application/json, text/plain, */*",
})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Payload 빌더
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def payload_fund(region, pub_priv):
    """펀드 탭 (설정원본)"""
    return {"dmSearch": {
        "tmpV40": "100000000", "tmpV41": "1",
        "tmpV30": START_DATE,  "tmpV31": END_DATE,
        "tmpV6":  "1",            # 설정원본
        "tmpV10": "0",            # 일간
        "tmpV4":  region,         # 1=국내, 4=해외
        "tmpV7":  pub_priv,       # 1=공모, 2=사모
        "tmpV5":  "", "tmpV11": "",
        "OBJ_NM": "STATFND0100100020BO",
    }}


def payload_disc(region):
    """투자일임 탭 (계약금액)"""
    return {"dmSearch": {
        "tmpV40": "100000000", "tmpV41": "1",
        "tmpV30": START_DATE,  "tmpV31": END_DATE,
        "tmpV101": "1",           # 계약금액
        "tmpV10":  "0",           # 일간
        "tmpV102": region,        # 1=국내, 2=해외
        "tmpV11":  "",
        "OBJ_NM":  "STATFND0100100270BO",
    }}


def payload_stock_fund():
    """증시자금추이 (투자자예탁금)"""
    return {"dmSearch": {
        "tmpV40":  "1000000",       # 백만원 단위
        "tmpV41":  "1",
        "tmpV1":   "D",             # 일간
        "tmpV45":  STOCK_START,     # 시작일
        "tmpV46":  END_DATE,        # 종료일
        "OBJ_NM":  "STATSCU0100000060BO",
    }}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API 호출
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def call_api(label, payload, col_map=None):
    """API 호출 -> 한글 컬럼 DataFrame"""
    print(f"  -> {label}")
    resp = session.post(API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    records = data if isinstance(data, list) else \
              next((v for v in data.values() if isinstance(v, list)), [])

    if not records:
        print(f"     ! 데이터 없음")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    if col_map:
        df.rename(columns=col_map, inplace=True)

    # 기준일자 포맷 (YYYYMMDD -> YYYY/MM/DD)
    date_col = "기준일자" if "기준일자" in df.columns else df.columns[0]
    if date_col in df.columns:
        df[date_col] = df[date_col].astype(str).apply(
            lambda x: f"{x[:4]}/{x[4:6]}/{x[6:]}" if len(x) == 8 else x
        )

    print(f"     OK {len(df)}행 x {len(df.columns)}열")
    return df


def save_to_db(df_fund_summary, df_deposit):
    """기존 DB JSON을 로드하고, 새 데이터를 날짜 키로 머지한 뒤 저장."""
    DB_JSON.parent.mkdir(parents=True, exist_ok=True)

    # 기존 데이터 로드
    if DB_JSON.exists():
        db = json.loads(DB_JSON.read_text(encoding="utf-8"))
    else:
        db = {"fundSummary": {}, "stockDeposit": {}, "lastUpdated": None}

    # 새 키 보장
    db.setdefault("fundChanges", {})
    db.setdefault("stockDepositChanges", {})

    # 펀드/일임 요약 누적 (기준일자가 키)
    if not df_fund_summary.empty:
        for _, row in df_fund_summary.iterrows():
            date_key = str(row["기준일자"])
            db["fundSummary"][date_key] = {
                col: (None if pd.isna(row[col]) else row[col])
                for col in df_fund_summary.columns
                if col != "기준일자"
            }

        # 일별 증감 계산 (날짜순 정렬 후 인접 차이)
        sorted_dates = sorted(db["fundSummary"].keys())
        fund_cols = [c for c in df_fund_summary.columns if c != "기준일자"]
        prev = {}
        for d in sorted_dates:
            changes = {}
            for col in fund_cols:
                val = db["fundSummary"][d].get(col)
                if val is not None and col in prev:
                    changes[col] = round(val - prev[col], 4)
                else:
                    changes[col] = None
                if val is not None:
                    prev[col] = val
            db["fundChanges"][d] = changes

    # 투자자예탁금 누적
    if not df_deposit.empty:
        date_col = "기준일자" if "기준일자" in df_deposit.columns else df_deposit.columns[0]
        val_col = [c for c in df_deposit.columns if c != date_col][0] if len(df_deposit.columns) > 1 else None
        for _, row in df_deposit.iterrows():
            date_key = str(row[date_col])
            if val_col:
                val = row[val_col]
                db["stockDeposit"][date_key] = None if pd.isna(val) else val

        # 투자자예탁금 일별 증감 계산
        sorted_dep = sorted(db["stockDeposit"].keys())
        prev_dep = None
        for d in sorted_dep:
            val = db["stockDeposit"][d]
            if val is not None and prev_dep is not None:
                db["stockDepositChanges"][d] = round(val - prev_dep, 4)
            else:
                db["stockDepositChanges"][d] = None
            if val is not None:
                prev_dep = val

    db["lastUpdated"] = datetime.now().isoformat(timespec="seconds")

    DB_JSON.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  OK DB 저장: {DB_JSON}")
    print(f"     펀드일임: {len(db['fundSummary'])}일, 투자자예탁금: {len(db['stockDeposit'])}일")


def main():
    print("=" * 60)
    print(f"  FREESIS 크레딧채권 운용 + 증시자금 크롤러")
    print(f"  펀드/일임: {START_DATE} ~ {END_DATE} (1년)")
    print(f"  증시자금:  {STOCK_START} ~ {END_DATE} (1년)")
    print("=" * 60)

    # 세션
    print("\n[1] 세션 초기화")
    try:
        session.get(INIT_URL, timeout=15)
        print("  OK")
    except:
        print("  ! 쿠키 없이 진행")

    # ─── Part A: 유형별기간설정 (6 API 호출) ───
    print("\n[2] 유형별기간설정 API 호출 (6건)")
    fund_results = {
        "펀드_공모_국내": call_api("펀드 공모 국내", payload_fund("1", "1"), FUND_COL_MAP),
        "펀드_공모_해외": call_api("펀드 공모 해외", payload_fund("4", "1"), FUND_COL_MAP),
        "펀드_사모_국내": call_api("펀드 사모 국내", payload_fund("1", "2"), FUND_COL_MAP),
        "펀드_사모_해외": call_api("펀드 사모 해외", payload_fund("4", "2"), FUND_COL_MAP),
        "일임_국내":     call_api("투자일임 국내",  payload_disc("1"), FUND_COL_MAP),
        "일임_해외":     call_api("투자일임 해외",  payload_disc("2"), FUND_COL_MAP),
    }

    # 11개 조합 요약
    EXTRACT = [
        ("공모_국내_채권", "펀드_공모_국내", "채권"),
        ("사모_국내_채권", "펀드_사모_국내", "채권"),
        ("일임_국내_채권", "일임_국내",     "채권"),
        ("공모_국내_MMF",  "펀드_공모_국내", "단기금융"),
        ("사모_국내_MMF",  "펀드_사모_국내", "단기금융"),
        ("공모_국내_주식", "펀드_공모_국내", "주식"),
        ("공모_해외_주식", "펀드_공모_해외", "주식"),
        ("사모_국내_주식", "펀드_사모_국내", "주식"),
        ("사모_해외_주식", "펀드_사모_해외", "주식"),
        ("일임_국내_주식", "일임_국내",     "주식"),
        ("일임_해외_주식", "일임_해외",     "주식"),
    ]

    summary_frames = []
    for label, src_key, col_name in EXTRACT:
        df = fund_results.get(src_key, pd.DataFrame())
        if df.empty or col_name not in df.columns:
            print(f"  ! {label}: 컬럼 '{col_name}' 없음")
            continue
        sub = df[["기준일자", col_name]].copy()
        sub.rename(columns={col_name: label}, inplace=True)
        summary_frames.append(sub.set_index("기준일자"))

    df_fund_summary = pd.concat(summary_frames, axis=1).reset_index() if summary_frames else pd.DataFrame()

    # ─── Part B: 증시자금추이 ───
    print("\n[3] 증시자금추이 API 호출")
    df_stock_raw = call_api("증시자금추이", payload_stock_fund())

    # 컬럼 매핑 (화면 순서 기준)
    # 구분 | 투자자예탁금(장내파생상품거래예수금제외) | 장내파생상품거래예수금 | 대고객RP | 위탁매매미수금 | ...
    if not df_stock_raw.empty:
        cols = list(df_stock_raw.columns)
        print(f"  증시자금 컬럼: {cols}")

        # 첫 행 값으로 매핑 확인
        if len(df_stock_raw) > 0:
            print(f"  첫 행: {df_stock_raw.iloc[0].to_dict()}")

        # TMPV1=기준일자, TMPV2=투자자예탁금 (화면에서 첫 데이터 컬럼)
        stock_col_map = {}
        if "TMPV1" in cols:
            stock_col_map["TMPV1"] = "기준일자"
        if "TMPV2" in cols:
            stock_col_map["TMPV2"] = "투자자예탁금(장내파생상품거래예수금제외)"
        if "TMPV3" in cols:
            stock_col_map["TMPV3"] = "장내파생상품거래예수금"
        if "TMPV4" in cols:
            stock_col_map["TMPV4"] = "대고객환매조건부채권(RP)"
        if "TMPV5" in cols:
            stock_col_map["TMPV5"] = "위탁매매미수금"

        df_stock = df_stock_raw.rename(columns=stock_col_map)

        # 기준일자 포맷
        date_col = "기준일자" if "기준일자" in df_stock.columns else df_stock.columns[0]
        df_stock[date_col] = df_stock[date_col].astype(str).apply(
            lambda x: f"{x[:4]}/{x[4:6]}/{x[6:]}" if len(str(x)) == 8 and str(x).isdigit() else x
        )

        # 투자자예탁금만 추출
        deposit_col = "투자자예탁금(장내파생상품거래예수금제외)"
        if deposit_col in df_stock.columns:
            df_deposit = df_stock[[date_col, deposit_col]].copy()
            print(f"  OK 투자자예탁금 추출: {len(df_deposit)}행")
        else:
            df_deposit = df_stock
    else:
        df_stock = pd.DataFrame()
        df_deposit = pd.DataFrame()

    # ─── 엑셀 저장 ───
    print(f"\n[4] 저장: {OUTPUT}")

    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as w:
        # 1) 펀드/일임 요약
        if not df_fund_summary.empty:
            df_fund_summary.to_excel(w, sheet_name="펀드일임_요약", index=False)
            print(f"  OK '펀드일임_요약' ({len(df_fund_summary)}행)")

        # 2) 투자자예탁금
        if not df_deposit.empty:
            df_deposit.to_excel(w, sheet_name="투자자예탁금", index=False)
            print(f"  OK '투자자예탁금' ({len(df_deposit)}행)")

        # 3) 증시자금 전체
        if not df_stock.empty:
            df_stock.to_excel(w, sheet_name="증시자금_전체", index=False)
            print(f"  OK '증시자금_전체' ({len(df_stock)}행)")

        # 4) 원본 데이터 시트
        for key, df in fund_results.items():
            safe = key[:31]
            df.to_excel(w, sheet_name=safe, index=False)
            print(f"  OK '{safe}' ({len(df)}행)")

    print(f"\n{'='*60}")
    print(f"  완료! -> {OUTPUT}")
    print(f"{'='*60}")
    print(f"""
  시트 구성:
    펀드일임_요약  - 11개 조합 (채권/MMF/주식 x 공모/사모/일임 x 국내/해외)
    투자자예탁금   - 투자자예탁금(장내파생상품거래예수금제외) 일별
    증시자금_전체  - 증시자금추이 전체 컬럼
    펀드_공모_국내 ~ 일임_해외 - 원본 데이터
    """)

    # ─── JSON DB 누적 저장 ───
    print("[5] JSON DB 누적 저장")
    save_to_db(df_fund_summary, df_deposit)


if __name__ == "__main__":
    main()
