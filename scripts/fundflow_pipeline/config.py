"""Constants, item definitions, and dataclasses for the fundflow pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
)

BOK_MARKET_LIST_URL = "https://www.bok.or.kr/portal/bbs/P0002018/list.do?menuNo=200366"
BOK_MARKET_RSS_URL = "https://www.bok.or.kr/portal/bbs/P0002018/news.rss?menuNo=200366"
REPO_LINK_URL = (
    "https://seibro.or.kr/websquare/control.jsp?"
    "w2xPath=/IPORTAL/user/repo/BIP_CNTS09001V.xml&menuNo=233"
)
# 패키지(scripts/fundflow_pipeline/) → scripts/fetch_seibro_repo.js
SEIBRO_REPO_FETCH_SCRIPT = Path(__file__).resolve().parent.parent / "fetch_seibro_repo.js"
# 유형별기간설정 (펀드 설정/일임) — 스크래퍼 INIT_URL과 동일한 페이지
FREESIS_LINK_URL = (
    "https://freesis.kofia.or.kr/stat/FreeSIS.do"
    "?parentDivId=MSIS40100000000000&serviceId=STATFND0100100260"
)
# 증시자금추이 (고객예탁금/CMA)
FREESIS_STOCK_LINK_URL = (
    "https://freesis.kofia.or.kr/stat/FreeSIS.do"
    "?parentDivId=MSIS10000000000000&serviceId=STATSCU0100000060"
)
DETAIL_URL_PATTERN = re.compile(
    r"/portal/bbs/P0002018/view\.do\?[^\"'<> ]*nttId=\d+[^\"'<> ]*",
    re.I,
)

ITEM_LINK_OVERRIDES = {
    "FUND_BOND": FREESIS_LINK_URL,
    "FUND_MMF": FREESIS_LINK_URL,
    "FUND_EQUITY": FREESIS_LINK_URL,
    "SEC_CUSTOMER_DEPOSIT": FREESIS_STOCK_LINK_URL,
    "SEC_CMA": FREESIS_STOCK_LINK_URL,
    "SEC_CUSTOMER_RP": REPO_LINK_URL,
    "REPO_INTERBANK": REPO_LINK_URL,
}

LEGACY_FUND_ITEM_CODES = {"FUND_BOND", "FUND_MMF", "FUND_EQUITY"}

FREESIS_SUMMARY_COLUMNS = {
    "FUND_BOND_PUBLIC_DOMESTIC": "공모_국내_채권",
    "FUND_BOND_PRIVATE_DOMESTIC": "사모_국내_채권",
    "FUND_BOND_DISCRETIONARY_DOMESTIC": "일임_국내_채권",
    "FUND_MMF_PUBLIC_DOMESTIC": "공모_국내_MMF",
    "FUND_MMF_PRIVATE_DOMESTIC": "사모_국내_MMF",
    "FUND_EQUITY_PUBLIC_DOMESTIC": "공모_국내_주식",
    "FUND_EQUITY_PUBLIC_OVERSEAS": "공모_해외_주식",
    "FUND_EQUITY_PRIVATE_DOMESTIC": "사모_국내_주식",
    "FUND_EQUITY_PRIVATE_OVERSEAS": "사모_해외_주식",
    "FUND_EQUITY_DISCRETIONARY_DOMESTIC": "일임_국내_주식",
    "FUND_EQUITY_DISCRETIONARY_OVERSEAS": "일임_해외_주식",
}

FREESIS_CALCULATED_PARENTS = [
    {
        "itemCode": "FUND_MMF_TOTAL", "itemName": "MMF", "displayOrder": 40,
        "children": ["FUND_MMF_PUBLIC_DOMESTIC", "FUND_MMF_PRIVATE_DOMESTIC"],
    },
    {
        "itemCode": "FUND_BOND_TOTAL", "itemName": "채권", "displayOrder": 45,
        "children": ["FUND_BOND_PUBLIC_DOMESTIC", "FUND_BOND_PRIVATE_DOMESTIC", "FUND_BOND_DISCRETIONARY_DOMESTIC"],
    },
    {
        "itemCode": "FUND_EQUITY_TOTAL", "itemName": "주식", "displayOrder": 55,
        "children": [
            "FUND_EQUITY_PUBLIC_DOMESTIC", "FUND_EQUITY_PUBLIC_OVERSEAS",
            "FUND_EQUITY_PRIVATE_DOMESTIC", "FUND_EQUITY_PRIVATE_OVERSEAS",
            "FUND_EQUITY_DISCRETIONARY_DOMESTIC", "FUND_EQUITY_DISCRETIONARY_OVERSEAS",
        ],
    },
]

FREESIS_FUND_ITEMS = [
    {"itemCode": "FUND_MMF_PUBLIC_DOMESTIC", "itemName": "공모 국내 MMF", "displayOrder": 41, "parentCode": "FUND_MMF_TOTAL"},
    {"itemCode": "FUND_MMF_PRIVATE_DOMESTIC", "itemName": "사모 국내 MMF", "displayOrder": 42, "parentCode": "FUND_MMF_TOTAL"},
    {"itemCode": "FUND_BOND_PUBLIC_DOMESTIC", "itemName": "공모 국내 채권", "displayOrder": 46, "parentCode": "FUND_BOND_TOTAL"},
    {"itemCode": "FUND_BOND_PRIVATE_DOMESTIC", "itemName": "사모 국내 채권", "displayOrder": 47, "parentCode": "FUND_BOND_TOTAL"},
    {"itemCode": "FUND_BOND_DISCRETIONARY_DOMESTIC", "itemName": "일임 국내 채권", "displayOrder": 48, "parentCode": "FUND_BOND_TOTAL"},
    {"itemCode": "FUND_EQUITY_PUBLIC_DOMESTIC", "itemName": "공모 국내 주식", "displayOrder": 56, "parentCode": "FUND_EQUITY_TOTAL"},
    {"itemCode": "FUND_EQUITY_PUBLIC_OVERSEAS", "itemName": "공모 해외 주식", "displayOrder": 57, "parentCode": "FUND_EQUITY_TOTAL"},
    {"itemCode": "FUND_EQUITY_PRIVATE_DOMESTIC", "itemName": "사모 국내 주식", "displayOrder": 58, "parentCode": "FUND_EQUITY_TOTAL"},
    {"itemCode": "FUND_EQUITY_PRIVATE_OVERSEAS", "itemName": "사모 해외 주식", "displayOrder": 59, "parentCode": "FUND_EQUITY_TOTAL"},
    {"itemCode": "FUND_EQUITY_DISCRETIONARY_DOMESTIC", "itemName": "일임 국내 주식", "displayOrder": 60, "parentCode": "FUND_EQUITY_TOTAL"},
    {"itemCode": "FUND_EQUITY_DISCRETIONARY_OVERSEAS", "itemName": "일임 해외 주식", "displayOrder": 61, "parentCode": "FUND_EQUITY_TOTAL"},
]


@dataclass(frozen=True)
class Attachment:
    label: str
    url: str


@dataclass(frozen=True)
class PageResult:
    page_url: str
    page_title: str
    attachment: Attachment
    parsed: dict


TARGET_ITEMS = {
    "실세총예금": {
        "sector": "은행",
        "itemCode": "BANK_TOTAL_DEPOSIT",
        "itemName": "실세총예금",
        "displayOrder": 10,
    },
    "실세요구불": {
        "sector": "은행",
        "itemCode": "BANK_DEMAND_DEPOSIT",
        "itemName": "실세요구불",
        "parentCode": "BANK_TOTAL_DEPOSIT",
        "level": 2,
        "includeInTotal": False,
        "displayOrder": 11,
    },
    "저축성": {
        "sector": "은행",
        "itemCode": "BANK_SAVINGS_DEPOSIT",
        "itemName": "저축성",
        "parentCode": "BANK_TOTAL_DEPOSIT",
        "level": 2,
        "includeInTotal": False,
        "displayOrder": 12,
    },
    "금전신탁": {"sector": "은행", "itemCode": "BANK_MONEY_TRUST", "itemName": "금전신탁", "displayOrder": 20},
    "고객예탁금": {"sector": "증권", "itemCode": "SEC_CUSTOMER_DEPOSIT", "itemName": "고객예탁금", "displayOrder": 70},
    "대고객RP매도": {"sector": "증권", "itemCode": "SEC_CUSTOMER_RP", "itemName": "고객RP", "displayOrder": 80},
    "CMA": {"sector": "증권", "itemCode": "SEC_CMA", "itemName": "CMA", "displayOrder": 90},
    "채권형": {"sector": "투신", "itemCode": "FUND_BOND", "itemName": "채권형", "displayOrder": 40},
    "MMF": {"sector": "투신", "itemCode": "FUND_MMF", "itemName": "MMF", "displayOrder": 50},
    "주식형": {"sector": "투신", "itemCode": "FUND_EQUITY", "itemName": "주식형", "displayOrder": 60},
}

# 표시 순서는 app.js의 sectorOrder가 최종 기준. 여기도 동일하게 유지(REPO→투신→증권→은행).
SECTOR_ORDER = {"REPO": 1, "투신": 2, "증권": 3, "은행": 4}

SEIBRO_REPO_ITEM = {
    "itemCode": "REPO_INTERBANK",
    "sector": "REPO",
    "groupName": "기관RP",
    "itemName": "기관RP",
    "parentCode": None,
    "level": 1,
    "itemType": "raw",
    "includeInTotal": True,
    "requiredForComplete": True,
    "showInHeatmap": True,
    "rawBalanceColumn": "잔고금액",
    "rawChangeColumn": "잔고금액_증감",
    "link": REPO_LINK_URL,
    "displayOrder": 65,
    "isActive": True,
    "unit": "조원",
    "source": "SEIBro 일별거래현황",
}
