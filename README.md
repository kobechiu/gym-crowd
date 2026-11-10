# 台北健身房即時人數收集

每 10 分鐘自動抓一次台北各運動中心與台大綜合體育館的健身房、游泳池人數，存成 CSV，作為之後「即時人數網頁」與「人數預測」的資料。

## 目前收集的場館

| 場館 | 資料來源 |
|---|---|
| 台大綜合體育館 | rent.pe.ntu.edu.tw 首頁「場地人流」（容量取最大乘載人數） |
| 中正運動中心 | wsjjsc.com.tw 首頁文字 |
| 大同運動中心 | dtsc-wdyg.com.tw 首頁文字 |
| 士林運動中心 | slsc-taipei.org 首頁文字 |
| 松山運動中心 | sssc.com.tw 首頁內嵌的 JSON |
| 中山、內湖、南港、文山運動中心 | 各館官網的 `/api`（POST） |

還沒加入：大安、信義、北投、萬華（尚未找到可讀取的人數來源）。新增場館時，在 `collector/collect.py` 的 `SOURCES` 加一行即可。

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

GitHub 上會依 `.github/workflows/collect.yml` 每 10 分鐘自動執行，並把新資料 commit 回 repo。

## 注意事項

- **repo 請設為公開**：公開 repo 的 GitHub Actions 不限分鐘數；私人 repo 每月只有 2,000 分鐘免費額度，每 10 分鐘跑一次一個月約需 4,300 分鐘，會超過。
- **GitHub 排程不保證準時**，尖峰時段可能延遲或略過幾次，分析時以 `time` 欄位為準。
- **禮貌抓取**：每 10 分鐘一次、每館間隔 1 秒、User-Agent 註明是學生專案。資料版權屬於各場館，公開展示時請註明來源；若場館表示不希望被抓取，請移除該館。
- 中山運動中心健身房在測試時顯示 0 人，可能是整修或資料未更新，分析前要確認。
