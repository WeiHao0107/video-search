# AI Video Semantic Search 🎥 🔍

這是一個基於 AI 的影片語義搜尋引擎。透過 **OpenAI Whisper** 自動生成字幕，並結合 **Sentence Transformers** 與 **Milvus** 向量資料庫，實現對影片內容的自然語言搜尋。前端使用 **Vue 3** 呈現，支援直接跳轉到搜尋命中的時間片段進行播放。

## ✨ 功能特色

*   **自動字幕生成**：支援 mp4, mkv, mov 等格式，使用 OpenAI Whisper 模型進行語音轉文字。
*   **語義搜尋**：不需要精準關鍵字，支援多語言（中/英）的自然語言查詢（例如：「機器學習的概念」）。
*   **精準跳轉**：搜尋結果直接顯示時間軸，點擊即可跳轉至該片段播放。
*   **RAG 架構**：結合 PostgreSQL (Metadata) 與 Milvus (Vector Index) 的高效檢索架構。

## 📂 專案結構

```text
video-search/
├── data/               # [Ignored] 存放原始影片檔案 (.mp4) 與生成的字幕資料
├── models/             # [Ignored] 存放下載的本地 AI 模型
├── milvus_demo.db      # [Ignored] Milvus Lite 向量資料庫檔案
├── schema.sql          # PostgreSQL 資料庫建立腳本
├── requirements.txt    # Python 後端依賴列表
├── docker-compose.yml  # (Optional) 快速啟動 PostgreSQL
│
├── src/                # 後端核心程式碼
│   ├── api.py          # FastAPI 伺服器，提供搜尋 API 與影片串流
│   ├── ingest.py       # 資料處理腳本 (轉錄 -> 向量化 -> 存入 DB)
│   ├── database.py     # PostgreSQL 連線與 ORM 模型定義
│   ├── search.py       # CLI 版本的搜尋測試工具
│   └── config.py       # 專案設定檔 (路徑、模型名稱、DB 連線)
│
└── frontend/           # 前端 Vue 3 專案
    ├── src/
    │   ├── App.vue     # 主頁面 (搜尋框、結果列表、播放器)
    │   └── ...
    └── vite.config.js  # 前端設定 (包含 API Proxy)
```

## 🛠️ 環境建置

### 1. 系統需求
*   **Python**: 3.8+
*   **Node.js**: 16+
*   **PostgreSQL**: 15+
*   **FFmpeg**: 必須安裝 (Whisper 依賴)
    *   Mac: `brew install ffmpeg`
    *   Linux: `sudo apt install ffmpeg`

### 2. 資料庫設定 (PostgreSQL)
本專案使用 PostgreSQL 儲存影片 Metadata 與字幕文字。

1.  **建立資料庫與使用者**：
    ```sql
    CREATE USER "user" WITH PASSWORD 'password';
    CREATE DATABASE videodb OWNER "user";
    ```
2.  **建立資料表**：
    您可以使用 DBeaver 或 psql 執行專案根目錄下的 `schema.sql` 檔案。

### 3. 後端安裝
```bash
# 建立並啟動虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
pip install openai-whisper  # 需額外確認安裝
```

### 4. 前端安裝
```bash
cd frontend
npm install
```

---

## 🚀 使用指南

### 第一步：匯入影片資料 (Ingestion)
1.  將您的影片檔 (例如 `demo.mp4`) 放入 `data/` 資料夾中。
2.  執行匯入腳本，系統會自動轉錄字幕並建立向量索引：
    ```bash
    # 在專案根目錄執行
    python src/ingest.py
    ```
    *(注意：第一次執行會下載模型，且轉錄過程視影片長度而定，請耐心等候)*

### 第二步：啟動後端 API
```bash
python src/api.py
```
*   API 文件網址：http://127.0.0.1:8000/docs
*   API 服務網址：http://127.0.0.1:8000

### 第三步：啟動前端介面
開啟新的終端機視窗：
```bash
cd frontend
npm run dev
```
打開瀏覽器訪問 `http://localhost:5173` (或終端機顯示的網址)。

---

## ⚠️ 常見問題

*   **Milvus File Lock Error**: 如果執行 `ingest.py` 時報錯，請確認是否關閉了正在執行的 `api.py`，因為 Milvus Lite 不支援多程序同時存取。
*   **搜尋結果不準確**: 專案預設使用多語言模型，請確認 `src/config.py` 中的模型設定。

## 📝 License
MIT
