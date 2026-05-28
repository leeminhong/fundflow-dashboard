"""
FREESIS 유형별기간설정 크롤러 (최종 확정)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
11개 데이터 포인트 자동 수집:

  [펀드 - 설정원본]
    공모 국내 채권 / 사모 국내 채권
    공모 국내 주식 / 공모 해외 주식
    사모 국내 주식 / 사모 해외 주식

  [투자일임 - 계약금액]
    일임 국내 채권 / 일임 국내 주식 / 일임 해외 주식

  [MMF(단기금융) - 설정원본]
    공모 국내 MMF / 사모 국내 MMF

API 컬럼 매핑 (브라우저 화면 대조 확인):
  TMPV1=기준일자 TMPV2=주식 TMPV3=혼합주식 TMPV4=혼합채권
  TMPV5=채권 TMPV6=재간접 TMPV7=단기금융 TMPV8=파생형
  TMPV9=부동산 TMPV10=실물 TMPV11=특별자산 TMPV12=혼합자산
  TMPV13=기관전용사모 TMPV14=투자일임기타 TMPV15=합계
  TMPV16=전일대비 TMPV17=전월대비 TMPV18=전년대비
  TMPV19=투자계약 TMPV20=기업성장

사용법:
  pip install requests pandas openpyxl
  python freesis_final3.py
"""

import requests
import json
import pandas as pd
from datetime import datetime, timedelta

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
END_DATE   = datetime.now().strftime("%Y%m%d")
START_DATE = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
OUTPUT     = f"freesis_크레딧채권운용_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

API_URL  = "https://freesis.kofia.or.kr/meta/getMetaDataList.do"
INIT_URL = ("https://freesis.kofia.or.kr/stat/FreeSIS.do"
            "?parentDivId=MSIS40100000000000"
            "&serviceId=STATFND0100100260")

# 컬럼 한글 매핑
COL_MAP = {
    "TMPV1": "기준일자", "TMPV2": "주식", "TMPV3": "혼합주식",
    "TMPV4": "혼합채권", "TMPV5": "채권", "TMPV6": "재간접",
    "TMPV7": "단기금융", "TMPV8": "파생형", "TMPV9": "부동산",
    "TMPV10": "실물", "TMPV11": "특별자산", "TMPV12": "혼합자산",
    "TMPV13": "기관전용사모", "TMPV14": "투자일임기타", "TMPV15": "합계",
    "TMPV16": "전일대비", "TMPV17": "전월대비", "TMPV18": "전년대비",
    "TMPV19": "투자계약", "TMPV20": "기업성장",
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API 호출 (탭별 payload가 다름!)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
session = requests.Session()
session.headers.update({
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":      INIT_URL,
    "Origin":       "https://freesis.kofia.or.kr",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept":       "application/json, text/plain, */*",
})


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


def call_api(label, payload):
    """API 호출 -> 한글 컬럼 DataFrame"""
    print(f"  -> {label}")
    resp = session.post(API_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    records = data if isinstance(data, list) else \
              next((v for v in data.values() if isinstance(v, list)), [])

    df = pd.DataFrame(records)
    df.rename(columns=COL_MAP, inplace=True)

    # 기준일자 포맷
    if "기준일자" in df.columns:
        df["기준일자"] = df["기준일자"].astype(str).str[:4] + "/" + \
                       df["기준일자"].astype(str).str[4:6] + "/" + \
                       df["기준일자"].astype(str).str[6:]

    print(f"     OK {len(df)}행")
    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  6개 API 호출 정의
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API_CALLS = {
    "펀드_공모_국내": lambda: call_api("펀드 공모 국내", payload_fund("1", "1")),
    "펀드_공모_해외": lambda: call_api("펀드 공모 해외", payload_fund("4", "1")),
    "펀드_사모_국내": lambda: call_api("펀드 사모 국내", payload_fund("1", "2")),
    "펀드_사모_해외": lambda: call_api("펀드 사모 해외", payload_fund("4", "2")),
    "일임_국내":     lambda: call_api("투자일임 국내",  payload_disc("1")),
    "일임_해외":     lambda: call_api("투자일임 해외",  payload_disc("2")),
}


def main():
    print("=" * 55)
    print(f"  FREESIS 크레딧채권 운용 데이터 수집")
    print(f"  {START_DATE} ~ {END_DATE}")
    print("=" * 55)

    # 세션
    print("\n[1] 세션 초기화")
    try:
        session.get(INIT_URL, timeout=15)
        print("  OK")
    except:
        print("  ! 쿠키 없이 진행")

    # API 호출
    print("\n[2] API 호출 (6건)")
    results = {}
    for key, fn in API_CALLS.items():
        results[key] = fn()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  요약 테이블 생성
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print("\n[3] 요약 테이블 생성")

    # 11개 조합 → 어떤 API 결과에서 어떤 컬럼을 읽을지
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
        df = results.get(src_key, pd.DataFrame())
        if df.empty or col_name not in df.columns:
            print(f"  ! {label}: 데이터 없음")
            continue

        sub = df[["기준일자", col_name]].copy()
        sub.rename(columns={col_name: label}, inplace=True)
        summary_frames.append(sub.set_index("기준일자"))

    if summary_frames:
        df_summary = pd.concat(summary_frames, axis=1)
        df_summary = df_summary.reset_index()
        print(f"  OK 요약: {df_summary.shape}")
    else:
        df_summary = pd.DataFrame()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  엑셀 저장
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    print(f"\n[4] 저장: {OUTPUT}")

    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as w:
        # 요약 시트 (첫 번째)
        if not df_summary.empty:
            df_summary.to_excel(w, sheet_name="요약", index=False)
            print(f"  OK '요약'")

        # 원본 데이터 시트
        for key, df in results.items():
            safe = key[:31]
            df.to_excel(w, sheet_name=safe, index=False)
            print(f"  OK '{safe}' ({len(df)}행)")

    print(f"\n{'='*55}")
    print(f"  완료! -> {OUTPUT}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
