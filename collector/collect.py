"""收集台北各運動中心與台大體育館的即時人數，追加寫入 data/ 下的 CSV。

只用 Python 標準函式庫，GitHub Actions 或自己的電腦都能直接執行：
    python collector/collect.py

每個場館各自獨立：某一館失敗只會記成 error，不影響其他館。
"""
from __future__ import annotations

import csv
import html
import json
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TPE = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = "Mozilla/5.0 (compatible; gym-crowd-student-project/0.1; course research, every 10 min)"
FIELDS = ["time", "venue", "facility", "count", "capacity", "status"]


def fetch(url: str, method: str = "GET") -> str:
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA}, data=b"" if method == "POST" else None)
    with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
        return r.read().decode("utf-8", "ignore")


def page_text(raw: str) -> str:
    t = re.sub(r"<(script|style).*?</\1>", " ", raw, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


# ── 各網站的讀法 ─────────────────────────────────────────────
def cyc_api(site: str):
    """救國團經營的運動中心：POST /api 回傳 {"gym": ["人數", "容留", ...], "swim": [...]}"""
    def run():
        d = json.loads(fetch(f"https://{site}.cyc.org.tw/api", "POST"))
        out = {}
        for key, fac in (("gym", "gym"), ("swim", "pool")):
            v = d.get(key)
            if v and v[0].strip().lstrip("-").isdigit():
                out[fac] = (max(0, int(v[0])), int(v[1]))
        return out
    return run


def text_pattern(url: str, patterns: dict[str, str]):
    """人數直接寫在官網首頁文字裡（中正、大同、士林）。"""
    def run():
        t = page_text(fetch(url))
        out = {}
        for fac, pat in patterns.items():
            m = re.search(pat, t)
            if m:
                out[fac] = (int(m.group(1)), int(m.group(2)))
        return out
    return run


def songshan():
    """松山：人數以 JSON 字串寫在頁面的 Vue 程式碼裡。"""
    raw = fetch("https://sssc.com.tw/")
    m = re.search(r'venueInfo\s*=\s*JSON\.parse\("(.*?)"\)', raw, re.S)
    if not m:
        return {}
    items = json.loads(json.loads('"' + m.group(1) + '"'))  # 先還原 JS 字串的跳脫字元，再解析 JSON
    names = {"健身房": "gym", "游泳池": "pool"}
    return {names[i["MachineName"]]: (max(0, int(i["UseQty"])), int(i["MaxQty"])) for i in items if i.get("MachineName") in names}


def ntu():
    """台大綜合體育館：場地租借系統首頁的「場地人流」。"""
    t = page_text(fetch("https://rent.pe.ntu.edu.tw/"))
    out = {}
    for fac, label in (("gym", "健身中心"), ("pool", "室內游泳池")):
        m = re.search(label + r"\s*(\d+)\s*現在人數\s*(\d+)\s*最適人數\s*(\d+)\s*最大乘載", t)
        if m:
            out[fac] = (int(m.group(1)), int(m.group(3)))  # 容量取「最大乘載」，最適人數另存在 README 說明
    return out


WP = {"gym": r"健身房\s*(\d+)\s*人\s*容留\s*(\d+)\s*人", "pool": r"游泳池\s*(\d+)\s*人\s*容留\s*(\d+)\s*人"}
SL = {"gym": r"健身房\s*(\d+)\s*人\s*/\s*容納\s*(\d+)\s*人", "pool": r"游泳池\s*(\d+)\s*人\s*/\s*容納\s*(\d+)\s*人"}

SOURCES = {
    "台大綜合體育館": ntu,
    "中正運動中心": text_pattern("https://wsjjsc.com.tw/", WP),
    "大同運動中心": text_pattern("https://www.dtsc-wdyg.com.tw/", WP),
    "士林運動中心": text_pattern("https://www.slsc-taipei.org/", SL),
    "松山運動中心": songshan,
    "中山運動中心": cyc_api("cssc"),
    "內湖運動中心": cyc_api("nhsc"),
    "南港運動中心": cyc_api("ngsc"),
    "文山運動中心": cyc_api("wssc"),
}


def collect() -> list[dict]:
    now = datetime.now(TPE).replace(second=0, microsecond=0).isoformat()
    rows = []
    for venue, fn in SOURCES.items():
        result, err = {}, ""
        for attempt in range(2):
            try:
                result = fn()
                err = "" if result else "no-data"
                break
            except Exception as e:  # 網路或格式問題：重試一次後記錄下來
                err = f"error:{type(e).__name__}"
                time.sleep(3)
        if result:
            for fac, (count, cap) in result.items():
                rows.append({"time": now, "venue": venue, "facility": fac, "count": count, "capacity": cap, "status": "ok"})
        else:
            rows.append({"time": now, "venue": venue, "facility": "", "count": "", "capacity": "", "status": err})
        time.sleep(1)  # 每館間隔 1 秒，不要同時打太多請求
    return rows


def save(rows: list[dict]) -> Path:
    DATA.mkdir(exist_ok=True)
    month = rows[0]["time"][:7]
    path = DATA / f"{month}.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)
    latest = {"updated": rows[0]["time"], "venues": {}}
    for r in rows:
        if r["status"] == "ok":
            latest["venues"].setdefault(r["venue"], {})[r["facility"]] = {"count": r["count"], "capacity": r["capacity"]}
        else:
            latest["venues"].setdefault(r["venue"], {"status": r["status"]})
    (DATA / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


if __name__ == "__main__":
    rows = collect()
    path = save(rows)
    ok = sum(r["status"] == "ok" for r in rows)
    for r in rows:
        print(f'{r["venue"]:<8} {r["facility"]:<5} {str(r["count"]):>4} / {str(r["capacity"]):<4} {r["status"]}')
    print(f"寫入 {path.relative_to(ROOT)}：{ok} 筆成功，{len(rows) - ok} 筆失敗")
    # 全部失敗才回傳錯誤碼，讓 GitHub Actions 標成紅燈提醒
    sys.exit(0 if ok else 1)
