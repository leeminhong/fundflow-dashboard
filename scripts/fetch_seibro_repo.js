#!/usr/bin/env node

const { chromium } = require("playwright");

const TARGET_URL =
  "https://seibro.or.kr/websquare/control.jsp?w2xPath=/IPORTAL/user/repo/BIP_CNTS09001V.xml&menuNo=233";

function parseArgs(argv) {
  let limit = 20;
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--limit" && i + 1 < argv.length) {
      const value = Number(argv[i + 1]);
      if (Number.isFinite(value) && value > 0) {
        limit = Math.floor(value);
      }
      i += 1;
    }
  }
  return { limit };
}

function toIsoDate(ymdSlash) {
  const [y, m, d] = ymdSlash.split("/");
  return `${y}-${m}-${d}`;
}

async function scrapeRepoDailyRows(limit) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  try {
    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
    await page.waitForTimeout(10000);
    const rows = await page.evaluate(() => {
      const isDate = (text) => /^\d{4}\/\d{2}\/\d{2}$/.test(text);
      const isNumber = (text) => /^[\d,]+$/.test(text);
      const data = [];
      const values = Array.from(document.querySelectorAll("table td"))
        .map((node) => (node.textContent || "").trim())
        .filter(Boolean);

      for (let i = 0; i < values.length - 2; i += 1) {
        const a = values[i];
        const b = values[i + 1];
        const c = values[i + 2];
        if (isDate(a) && isNumber(b) && isNumber(c)) {
          data.push({ stdDate: a, tradeAmountBillion: b, balanceAmountBillion: c });
        }
      }
      return data;
    });

    const uniqueByDate = new Map();
    for (const row of rows) {
      if (!uniqueByDate.has(row.stdDate)) {
        uniqueByDate.set(row.stdDate, row);
      }
    }
    const picked = Array.from(uniqueByDate.values()).slice(0, limit);
    return picked.map((row) => ({
      date: toIsoDate(row.stdDate),
      tradeAmountBillion: Number(String(row.tradeAmountBillion).replaceAll(",", "")),
      balanceAmountBillion: Number(String(row.balanceAmountBillion).replaceAll(",", "")),
    }));
  } finally {
    await browser.close();
  }
}

async function main() {
  const { limit } = parseArgs(process.argv.slice(2));
  const rows = await scrapeRepoDailyRows(limit);
  process.stdout.write(`${JSON.stringify(rows)}\n`);
}

main().catch((error) => {
  console.error(error.message || String(error));
  process.exit(1);
});
