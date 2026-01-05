# AI Stock Advisor (Starter Template)

前端：React + Vite + TypeScript  
後端：FastAPI (Python)

## 快速啟動

### 後端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev -- --host
```

預設前端會呼叫 `http://localhost:8000` 的 API。

## 下一步可以擴充的主題

- 導入真正的 JWT 登入 / 登出機制
- 把 in-memory 資料換成資料庫（PostgreSQL / SQLite + SQLAlchemy）
- 在後端實作：
  - 券商 APP 截圖 → LLM Vision 分析 → 自動產生持股資料
  - 美股新聞抓取 + GPT / Gemini 摘要
  - 台北時間 22:30 排程自動產生每日報告並寄送或推播
