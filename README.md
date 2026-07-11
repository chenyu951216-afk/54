# gate-quant-ranking-scanner

Gate 永續合約量化找幣、排名與歷史重播回測系統。它掃描 Gate USDT 永續合約、計算多週期技術與市場結構、輸出綜合／做多／做空排名，並提供嚴格的 point-in-time replay 與分開的績效回測。系統只提供研究資料，不自動下單、不平倉、不撤單、不管理資產。

## 功能

- Gate 官方 Futures REST v4 與 Futures WebSocket adapter。
- 4H 大方向、30m 正式排名、15m/5m 回踩輔助。
- EMA、BOLL、VWAP、DMI、ADX、MFI、ATR、成交額、OI、基差、funding、結構與突破。
- 資料缺口、單位轉換、暖機、時間對齊、API partial failure 與 stale data diagnostics。
- 每根 30m 收線後排程掃描，預設收線後 20 秒，防止重複執行。
- 響應式繁體中文深色網頁、Discord 完整 1～10 名分段通知。
- 歷史 replay job、進度、取消、JSON/CSV/HTML export。
- 下一根開盤／固定持有／ATR 止損止盈／手續費／滑價／MFE/MAE／walk-forward 回測引擎。
- PostgreSQL async mode；沒有 `DATABASE_URL` 時明確使用 memory mode，重啟資料會消失。

## Gate 資料來源

本專案只使用官方 endpoint：`https://api.gateio.ws/api/v4/futures/usdt`。完整欄位、單位與歷史限制見 [docs/gate-data-map.md](docs/gate-data-map.md)。Gate 官方文件：[REST Futures API](https://www.gate.com/docs/developers/apiv4/en/futures/)、[Futures WebSocket](https://www.gate.com/docs/developers/futures/ws/)。

官方 API 的限制很重要：K 線單次最多 2000 根；逐筆成交的正負 size 可作為即時 taker side；歷史 spread、任意歷史 24h ticker 與完整歷史 active flow 不一定可由官方公開接口重建。系統會顯示 `unavailable`、扣除不可用權重與降低完整度，不會用目前數字或 0 偽造歷史狀態。

## 本機安裝

需要 Python 3.12。建立 venv 後執行 `python -m pip install -r requirements.txt`，複製 `.env.example` 為 `.env`，再執行 `python main.py`。服務會監聽 `0.0.0.0:${PORT:-8080}`；`GET /health` 與 `GET /api/rankings` 可用來檢查。

## Docker

執行 `docker compose up --build`。Dockerfile 使用 Python 3.12 slim、非 root `app` 使用者、單一 Uvicorn worker、`/health` healthcheck，且不複製 `.env`。

## GitHub

網頁一鍵上傳時，把根目錄內容完整上傳，確認 `Dockerfile`、`main.py`、`.github/workflows/` 在根目錄，且 `.env` 沒有被加入。Git 指令依序為 `git init`、`git add .`、`git commit -m "build gate quant ranking scanner"`、`git branch -M main`、`git remote add origin https://github.com/<user>/<repo>.git`、`git push -u origin main`。

## Zeabur

從 GitHub 建立 service，使用根目錄 Dockerfile；加入 PostgreSQL service 並把 `DATABASE_URL` 設到 app。保持 `PORT=8080`，部署完成後開啟 `/health`。不要設定多個 worker，避免 scheduler 重複掃描。

可直接貼入 Zeabur 的環境變數（請先替換 secrets）：

`APP_NAME=gate-quant-ranking-scanner`

`APP_ENV=production`

`LOG_LEVEL=INFO`

`HOST=0.0.0.0`

`PORT=8080`

`TIMEZONE=Asia/Taipei`

`DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME`

`GATE_REST_BASE_URL=https://api.gateio.ws/api/v4`

`GATE_WS_URL=wss://fx-ws.gateio.ws/v4/ws/usdt`

`MIN_24H_TURNOVER_USDT=10000000`

`MAX_SPREAD_PCT=0.10`

`MIN_30M_CANDLES=240`

`MIN_4H_CANDLES=150`

`MIN_DATA_COMPLETENESS_PCT=70`

`RANKING_MIN_SCORE=55`

`SCAN_DELAY_SECONDS=20`

`SCAN_ON_STARTUP=false`

`SCHEDULER_ENABLED=true`

`MANUAL_SCAN_TOKEN=REPLACE_WITH_LONG_RANDOM_VALUE`

`ADMIN_BEARER_TOKEN=REPLACE_WITH_LONG_RANDOM_VALUE`

`DISCORD_WEBHOOK_URL=`

`PUBLIC_BASE_URL=https://YOUR_ZEABUR_DOMAIN`

`REPLAY_REQUIRE_HISTORICAL_SPREAD=true`

`REPLAY_REQUIRE_HISTORICAL_ACTIVE_FLOW=false`

## 即時掃描與 Discord

手動掃描使用 `POST /api/scan` 並帶 `Authorization: Bearer $ADMIN_BEARER_TOKEN`；body 可用 `{"dry_run":true,"top_n":10,"notify_discord":false}`。Discord 測試使用 `POST /api/notifications/test`。通知包含總覽、綜合、做多、做空完整排名；超過 Discord 限制會拆段並標示序號，429 會依 `retry_after` 重試。

## 歷史重播

網頁 `/replay` 可輸入 `2026-06-09 10:00` 到 `2026-06-09 12:00`、時區 `Asia/Taipei`、30 分鐘間隔。API 建立背景工作，結果從 `/api/replay/{job_id}/results`、`diagnostics` 與 `export.json/csv/html` 取得。無可靠排名不是系統錯誤：代表資料完整度、時間對齊或官方歷史資料可得性未達門檻。

## 回測

先完成 replay，再把 `replay_job_id` POST 到 `/api/backtest`。回測才會計算進場、持有、ATR 止損止盈、費用、滑價、MFE/MAE 與 walk-forward；replay 本身不假設下單。

## API

`GET /`、`GET /health`、`GET /api/status`、`GET /api/scan/latest`、`GET /api/rankings`、`GET /api/rankings/long`、`GET /api/rankings/short`、`GET /api/rankings/history`、`GET /api/contracts/{contract}`、`GET /api/contracts/{contract}/history`、`POST /api/scan`、`POST /api/notifications/test`、`GET /api/notifications/history`、replay 與 backtest API 都有 OpenAPI 文件 `/docs`。

## 測試與限制

執行 `pytest -q`、`ruff check app tests scripts main.py`、`mypy app` 與 `docker build -t gate-quant-ranking-scanner .`。指標只使用目前及之前資料，正式排名只用已收線 K，rolling 結構不引用未來擺動點。任何 API timeout、429、schema 異常、資料缺口或指標錯誤都會進入 diagnostics。這是研究工具，不是投資建議；排名第一不代表一定上漲，也不代表勝率。

