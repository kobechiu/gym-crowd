# 台北健身房即時人數收集

每 10 分鐘自動抓一次台大綜合體育館的健身中心、游泳池人數，存成 CSV，作為之後「即時人數網頁」與「人數預測」的資料。

## 目前收集的場館

只收**台大綜合體育館**（健身中心、室內游泳池），資料來源是 rent.pe.ntu.edu.tw 首頁的「場地人流」，容量取最大乘載人數。

11/10–11/24 的資料另外包含台北 8 個運動中心；其他場館的讀法保留在 `collector/collect.py` 的 `OTHER_SOURCES`，需要時搬回 `SOURCES` 即可。

## 排程

- **主要觸發**：外部排程服務 cron-job.org 每 10 分鐘呼叫 GitHub API，觸發 `收集健身房人數` workflow（`workflow_dispatch`）。
- **備援**：GitHub 內建排程每小時一次。內建排程實測平均 6～7 小時才真的執行一次，所以不能當主要排程。
- **防重複**：距離上一筆不到 7 分鐘就跳過（手動執行可加 `--force`）。

## 資料格式

`data/YYYY-MM.csv`，每次執行每個場館各一到兩列：

| 欄位 | 說明 |
|---|---|
| time | 抓取時間（台北時間，ISO 8601） |
| venue | 場館名稱 |
| facility | `gym` 健身房、`pool` 游泳池 |
| count | 當下人數 |
| capacity | 容留人數 |
| status | `ok`，或失敗原因（如 `error:TimeoutError`、`no-data`） |

`data/latest.json` 是最新一次的結果，之後網頁可以直接讀這個檔案。

## 怎麼執行

自己的電腦（只需要 Python 3.9 以上，不用安裝套件）：

```bash
python3 collector/collect.py
```

GitHub 上由外部排程每 10 分鐘觸發 `.github/workflows/collect.yml`，並把新資料 commit 回 repo。

## 注意事項

- **repo 請設為公開**：公開 repo 的 GitHub Actions 不限分鐘數；私人 repo 每月只有 2,000 分鐘免費額度，每 10 分鐘跑一次一個月約需 4,300 分鐘，會超過。
- **排程不保證完全準時**，外部服務或 GitHub 偶爾會延遲，分析時以 `time` 欄位為準。
- **禮貌抓取**：每 10 分鐘一次、每館間隔 1 秒、User-Agent 註明是學生專案。資料版權屬於各場館，公開展示時請註明來源；若場館表示不希望被抓取，請移除該館。
- 中山運動中心健身房在測試時顯示 0 人，可能是整修或資料未更新，分析前要確認。
