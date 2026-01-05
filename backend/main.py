# ============================================================
# main.py — AI Stock Advisor (Clean Integrated Version)
# ============================================================

import os
import re
import json
import base64
import datetime as dt
from datetime import datetime, timedelta, date
from typing import Optional, List, Any, Dict
import httpx
import yfinance as yf
import bcrypt

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

from openai import OpenAI

from database import get_db, init_db  # 你提供的 database.py


# ============================================================
# App & CORS
# ============================================================

load_dotenv()

app = FastAPI(title="AI Stock Advisor API", version="1.0.0")

# CORS：務必只在「唯一的 app 實例」上設定一次
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.0.102:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Security / Auth
# ============================================================

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY missing in .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ============================================================
# 基本設定 & DB 連線
# ============================================================

DB_PATH = "news.db"
CACHE_EXPIRE_MINUTES = 60  # C: 60分鐘

TAIPEI_TZ = dt.timezone(dt.timedelta(hours=8))
scheduler = AsyncIOScheduler(timezone=TAIPEI_TZ)


def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class UserRegister(BaseModel):
    email: str
    password: str
    nickname: Optional[str] = None


class UserLogin(BaseModel):
    email: str  # 允許 email 或 nickname
    password: str


class User(BaseModel):
    id: int
    email: str
    nickname: Optional[str] = None
    created_at: Optional[str] = None

class NewsItem(BaseModel):
    title: str
    url: str
    summary_en: str
    summary_zh: str
    source: Optional[str] = None
    published_at: Optional[dt.datetime] = None
    image_url: Optional[str] = None
    sentiment: Optional[str] = None  # 利多 / 中性 / 利空


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """JWT -> uid -> DB user"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid:
            raise HTTPException(status_code=401, detail="Token 無效或已過期")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 無效或已過期")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email, nickname, created_at FROM users WHERE id=?", (uid,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    # 你的 database.py 設定了 row_factory=sqlite3.Row，可用 dict key 取值
    return User(
        id=row["id"],
        email=row["email"],
        nickname=row["nickname"],
        created_at=row["created_at"],
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# -------------------------
# Auth Routes
# -------------------------

@app.post("/auth/register", response_model=User)
def register(payload: UserRegister):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email=?", (payload.email,))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Email 已註冊")

    pw_hash = hash_password(payload.password)

    cur.execute(
        "INSERT INTO users (email, password_hash, nickname) VALUES (?, ?, ?)",
        (payload.email, pw_hash, payload.nickname),
    )
    conn.commit()
    uid = cur.lastrowid
    conn.close()

    return User(id=uid, email=payload.email, nickname=payload.nickname)


@app.post("/auth/login")
def login_user(payload: UserLogin):
    login_id = payload.email  # 使用者輸入的欄位，可是 email 或 nickname
    password = payload.password

    conn = get_db()
    cur = conn.cursor()

    # 判斷是 email 還是 nickname
    if "@" in login_id:
        cur.execute("SELECT id, email, nickname, password_hash FROM users WHERE email=?", (login_id,))
    else:
        cur.execute("SELECT id, email, nickname, password_hash FROM users WHERE nickname=?", (login_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=400, detail="帳號不存在")

    user_id, email, nickname, password_hash = row

    # 驗證密碼
    if not bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8")):
        raise HTTPException(status_code=400, detail="密碼錯誤")

    # 產生 token
    token = create_access_token({"sub": str(user_id)})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "nickname": nickname,
        }
    }



@app.get("/me", response_model=User)
def get_me(current: User = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email, nickname, created_at FROM users WHERE id=?", (current.id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    return User(id=row[0], email=row[1], nickname=row[2], created_at=row[3])


# ============================================================
# LLM & NewsAPI 設定
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_SUMMARIZER_PROVIDER = os.getenv("NEWS_SUMMARIZER_PROVIDER", "openai").lower()

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ============================================================
# SQLite 工具：載入 / 儲存 / 檢查快取
# ============================================================

def save_news_item(conn, category, art, title_zh, summary_en, summary_zh, sentiment: str = ""):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO news_cache (
            category,
            original_title,
            translated_title,
            summary_en,
            summary_zh,
            sentiment,
            source,
            url,
            published_at,
            image_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            category,
            art.get("title"),
            title_zh,
            summary_en,
            summary_zh,
            sentiment,
            art.get("source"),
            art.get("url"),
            art.get("published_at"),
            art.get("image_url"),
        ),
    )

def load_news_from_db(conn):
    cur = conn.cursor()

    def load(category: str):
        cur.execute(
            """
            SELECT translated_title, summary_en, summary_zh, sentiment,
                   source, url, image_url, published_at
            FROM news_cache
            WHERE category = ?
            ORDER BY created_at DESC
            LIMIT 5
            """,
            (category,),
        )
        rows = cur.fetchall()
        return [
            {
                "title": r[0],
                "summary_en": r[1],
                "summary_zh": r[2],
                "sentiment": r[3],
                "source": r[4],
                "url": r[5],
                "image_url": r[6],
                "published_at": r[7],
            }
            for r in rows
        ]

    return {
        "international": load("international"),
        "us_finance": load("us_finance"),
    }

def is_cache_expired(conn, category: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT created_at FROM news_cache
        WHERE category = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (category,),
    )
    row = cur.fetchone()
    if not row:
        return True

    ts = row[0]

    # SQLite 產出格式："2025-12-08 14:40:01" → 要用 strptime
    try:
        last_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except:
        return True

    return datetime.now() - last_time > timedelta(minutes=CACHE_EXPIRE_MINUTES)


# ============================================================
# NewsAPI 抓取新聞
# ============================================================

async def fetch_news_from_newsapi() -> dict:
    """
    精準抓取：
    - 國際科技財經新聞（Global Tech Finance）
    - 美國科技財經新聞（US Tech Finance）
    過濾條件：
    - 必須有圖片
    - 排除 sports / entertainment / gossip 類型
    """
    if not NEWS_API_KEY:
        raise RuntimeError("NEWS_API_KEY not set")

    international_articles = []
    us_finance_articles = []

    async with httpx.AsyncClient(timeout=10.0) as client:

        # 🌍 國際科技財經
        try:
            intl_resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": "(technology OR tech OR semiconductor OR chip OR AI OR finance OR stock OR market)",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "apiKey": NEWS_API_KEY,
                },
            )
            intl_data = intl_resp.json()

            for art in intl_data.get("articles", []):
                if not art.get("urlToImage"):
                    continue

                bad_keywords = ["sports", "entertainment", "gossip"]
                if any(k in (art.get("title") or "").lower() for k in bad_keywords):
                    continue

                international_articles.append(
                    {
                        "title": art.get("title"),
                        "url": art.get("url"),
                        "description": art.get("description") or "",
                        "content": art.get("content") or "",
                        "source": (art.get("source") or {}).get("name"),
                        "published_at": art.get("publishedAt"),
                        "image_url": art.get("urlToImage"),
                    }
                )

        except Exception as e:
            print("Error fetching international tech finance news:", e)

        # 🇺🇸 美國科技財經
        try:
            us_resp = await client.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "country": "us",
                    "category": "technology",
                    "pageSize": 10,
                    "apiKey": NEWS_API_KEY,
                },
            )
            us_data = us_resp.json()

            for art in us_data.get("articles", []):
                if not art.get("urlToImage"):
                    continue

                bad_keywords = ["sports", "entertainment", "gossip"]
                if any(k in (art.get("title") or "").lower() for k in bad_keywords):
                    continue

                us_finance_articles.append(
                    {
                        "title": art.get("title"),
                        "url": art.get("url"),
                        "description": art.get("description") or "",
                        "content": art.get("content") or "",
                        "source": (art.get("source") or {}).get("name"),
                        "published_at": art.get("publishedAt"),
                        "image_url": art.get("urlToImage"),
                    }
                )

        except Exception as e:
            print("Error fetching US tech finance news:", e)

    return {
        "international": international_articles[:5],
        "us_finance": us_finance_articles[:5],
    }

# ============================================================
# LLM 摘要 + Sentiment
# ============================================================

def _parse_summary(text: str):
    """
    從 LLM 回覆中解析：
    TITLE_ZH / ZH / EN / SENTIMENT（可選）
    """
    title_zh = ""
    zh = ""
    en = ""
    sentiment = ""

    for line in text.splitlines():
        s = line.strip()
        low = s.lower()

        if low.startswith("title_zh"):
            title_zh = s.split(":", 1)[1].strip()
        elif low.startswith("zh:"):
            zh = s.split(":", 1)[1].strip()
        elif low.startswith("en:"):
            en = s.split(":", 1)[1].strip()
        elif low.startswith("sentiment"):
            sentiment = s.split(":", 1)[1].strip()

    return title_zh, en, zh, sentiment

def _summarize_with_openai(title: str, body: str):
    """
    回傳：title_zh, summary_en, summary_zh, sentiment
    """
    if not openai_client:
        return "", "", "", ""

    prompt = f"""
你是一位專業的國際科技財經新聞摘要助手。

請閱讀下方新聞，並完成四件事：
1. 產生「繁體中文標題翻譯」
2. 產生「繁體中文摘要」（自然、口語、易讀）
3. 產生「英文摘要」（簡潔、正式）
4. 判斷新聞對股市為「利多 / 中性 / 利空」，格式為：SENTIMENT: <xxx>

請務必用以下格式回覆（注意冒號）：

TITLE_ZH: <繁體中文標題>
ZH: <繁體中文摘要>
EN: <English summary>
SENTIMENT: <利多/中性/利空>

新聞內容：
{title}

{body}
"""

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        full = resp.choices[0].message.content or ""
    except Exception as e:
        print("OpenAI summarization error:", e)
        return "", "", "", ""

    return _parse_summary(full)

def _summarize_with_gemini(title: str, body: str):
    """
    回傳：title_zh, summary_en, summary_zh, sentiment（Gemini 目前 sentiment 可留空）
    """
    if not gemini_client:
        return "", "", "", ""

    prompt = f"""
你是一位專業的國際科技財經新聞摘要助手。

請閱讀下方新聞，並完成三件事：
1. 產生「繁體中文標題翻譯」
2. 產生「繁體中文摘要」
3. 產生「英文摘要」

請務必用以下格式回覆：

TITLE_ZH: <繁體中文標題>
ZH: <繁體中文摘要>
EN: <English summary>

新聞內容：
{title}

{body}
"""

    try:
        resp = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        full = getattr(resp, "text", None) or getattr(resp, "output_text", None) or ""
    except Exception as e:
        print("Gemini summarization error:", e)
        return "", "", "", ""

    title_zh, en, zh, sentiment = _parse_summary(full)
    return title_zh, en, zh, sentiment  # sentiment 多半為空字串

def summarize_article(title: str, description: str, content: str):
    """
    回傳順序固定：title_zh, summary_en, summary_zh, sentiment
    """
    body = content or description or ""
    if not body:
        return title, "", "", "中性"

    title_zh = ""
    en = ""
    zh = ""
    sentiment = ""

    if NEWS_SUMMARIZER_PROVIDER == "openai":
        title_zh, en, zh, sentiment = _summarize_with_openai(title, body)
    elif NEWS_SUMMARIZER_PROVIDER == "gemini":
        title_zh, en, zh, sentiment = _summarize_with_gemini(title, body)

    # fallback
    if not title_zh:
        title_zh = title
    if not en:
        en = body[:200]
    if not zh:
        zh = body[:150]
    if not sentiment:
        sentiment = "中性"

    return title_zh, en, zh, sentiment



# ============================================================
# /news：使用 SQLite 快取 + Sentiment
# ============================================================

@app.get("/news")
async def get_news():
    """
    1. 先檢查 SQLite 快取是否過期
    2. 未過期 → 直接從 DB 載入
    3. 過期 → NewsAPI 抓新資料 + LLM 摘要 + 寫入 DB
    4. 回傳：
       - 國際科技財經
       - 美國科技財經
       各 5 則，含：
       title, summary_zh, summary_en, sentiment, image_url, ...
    """

    conn = get_db()

    from_cache_international = not is_cache_expired(conn, "international")
    from_cache_us_finance = not is_cache_expired(conn, "us_finance")

    # ✅ 若兩個 category 的快取都還有效 → 直接回 DB
    if from_cache_international and from_cache_us_finance:
        data = load_news_from_db(conn)
        conn.close()
        return data

    # ❌ 至少有一個過期 → 重新抓
    raw = await fetch_news_from_newsapi()

    international_items = []
    us_finance_items = []

    cur = conn.cursor()
    # 先刪除舊資料（兩個 category）
    if not from_cache_international:
        cur.execute("DELETE FROM news_cache WHERE category='international'")

    if not from_cache_us_finance:
        cur.execute("DELETE FROM news_cache WHERE category='us_finance'")

    # 🌍 國際
    for art in raw["international"]:
        title = art["title"] or ""
        desc = art.get("description", "") or ""
        content = art.get("content", "") or ""

        title_zh, summary_en, summary_zh, sentiment = summarize_article(title, desc, content)

        save_news_item(
            conn,
            "international",
            art,
            title_zh,
            summary_en,
            summary_zh,
            sentiment=sentiment,
        )

        international_items.append(
            NewsItem(
                title=title_zh,
                url=art["url"],
                summary_en=summary_en,
                summary_zh=summary_zh,
                sentiment=sentiment,
                source=art["source"],
                published_at=art["published_at"],
                image_url=art["image_url"],
            )
        )

    # 🇺🇸 美國
    for art in raw["us_finance"]:
        title = art["title"] or ""
        desc = art.get("description", "") or ""
        content = art.get("content", "") or ""

        title_zh, summary_en, summary_zh, sentiment = summarize_article(title, desc, content)

        save_news_item(
            conn,
            "us_finance",
            art,
            title_zh,
            summary_en,
            summary_zh,
            sentiment=sentiment,
        )

        us_finance_items.append(
            NewsItem(
                title=title_zh,
                url=art["url"],
                summary_en=summary_en,
                summary_zh=summary_zh,
                sentiment=sentiment,
                source=art["source"],
                published_at=art["published_at"],
                image_url=art["image_url"],
            )
        )

    conn.commit()
    conn.close()

    return {
        "international": international_items,
        "us_finance": us_finance_items,
    }


# ============================================================
# Holdings
# ============================================================

class HoldingCreate(BaseModel):
    symbol: str
    shares: float
    cost_basis: float
    purchase_date: Optional[date] = None


class HoldingUpdate(BaseModel):
    shares: float
    cost_basis: float
    purchase_date: Optional[date] = None


def normalize_symbol(symbol: str) -> str:
    """
    - 美股：AAPL / NVDA / TSLA -> AAPL
    - 台股純數字：2330 -> 2330.TW
    """
    s = symbol.strip().upper()
    if re.fullmatch(r"\d{4,6}", s):
        return f"{s}.TW"
    return s


@app.get("/stocks/info")
def get_stock_info(symbol: str, current: User = Depends(get_current_user)):
    """
    前端輸入：2330 / AAPL
    回傳：名稱、現價、是否有效
    """
    raw = symbol.strip().upper()
    yf_symbol = normalize_symbol(raw)

    try:
        ticker = yf.Ticker(yf_symbol)
        fast = ticker.fast_info or {}
        price = fast.get("lastPrice")

        info = ticker.info or {}
        name = info.get("shortName") or info.get("longName")

        if not name:
            return {"valid": False, "message": "找不到股票資訊，請確認代號是否正確"}

        return {
            "valid": True,
            "symbol": raw,
            "yf_symbol": yf_symbol,
            "market": "TW" if yf_symbol.endswith(".TW") else "US",
            "name": name,
            "price": price,
        }
    except Exception as e:
        print("[stocks/info] error:", e)
        return {"valid": False, "message": "查詢股票時發生錯誤"}


@app.get("/holdings")
def list_holdings(current: User = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, symbol, shares, cost_basis, purchase_date
        FROM holdings
        WHERE user_id=?
        ORDER BY created_at DESC
        """,
        (current.id,),
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "symbol": r["symbol"],
            "shares": r["shares"],
            "cost_basis": r["cost_basis"],
            "purchase_date": r["purchase_date"],
        }
        for r in rows
    ]


@app.post("/holdings")
def create_holding(payload: HoldingCreate, current: User = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()

    symbol = normalize_symbol(payload.symbol)

    # 不允許同 user 重複同一支股票
    cur.execute("SELECT id FROM holdings WHERE user_id=? AND symbol=?", (current.id, symbol))
    if cur.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"你已經有 {symbol} 的持股，請改用編輯功能")

    cur.execute(
        """
        INSERT INTO holdings (user_id, symbol, shares, cost_basis, purchase_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (current.id, symbol, payload.shares, payload.cost_basis, payload.purchase_date),
    )
    conn.commit()
    hid = cur.lastrowid
    conn.close()

    return {"id": hid, "symbol": symbol, **payload.model_dump()}


@app.put("/holdings/{hid}")
def update_holding(hid: int, payload: HoldingUpdate, current: User = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE holdings
        SET shares=?, cost_basis=?, purchase_date=?
        WHERE id=? AND user_id=?
        """,
        (payload.shares, payload.cost_basis, payload.purchase_date, hid, current.id),
    )

    if cur.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="找不到持股")

    conn.commit()
    conn.close()
    return {"ok": True}


@app.delete("/holdings/{hid}")
def delete_holding(hid: int, current: User = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM holdings WHERE id=? AND user_id=?", (hid, current.id))
    conn.commit()
    conn.close()
    return {"ok": True}


# ============================================================
# Portfolio Summary
# ============================================================

@app.get("/portfolio/summary")
def portfolio_summary(current: User = Depends(get_current_user)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT symbol, shares, cost_basis
        FROM holdings
        WHERE user_id=?
        """,
        (current.id,),
    )
    rows = cur.fetchall()
    conn.close()

    total_cost = 0.0
    total_value = 0.0
    items = []

    for r in rows:
        symbol = r["symbol"]
        shares = float(r["shares"])
        cost_basis = float(r["cost_basis"])

        # yfinance symbol：你 DB 已存 normalize 後 symbol（含 .TW）
        yf_symbol = symbol.upper()

        try:
            ticker = yf.Ticker(yf_symbol)
            fast = ticker.fast_info or {}
            price = fast.get("lastPrice") or 0.0
        except Exception as e:
            print("Price fetch error:", yf_symbol, e)
            price = 0.0

        cost = cost_basis * shares
        value = price * shares

        total_cost += cost
        total_value += value

        profit = value - cost
        profit_rate = (profit / cost * 100) if cost > 0 else 0

        items.append(
            {
                "symbol": symbol,
                "shares": shares,
                "avg_price": cost_basis,
                "current_price": round(price, 2),
                "value": round(value, 2),
                "profit": round(profit, 2),
                "profit_rate": round(profit_rate, 2),
            }
        )

    profit = total_value - total_cost
    profit_rate = (profit / total_cost * 100) if total_cost > 0 else 0

    return {
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "profit": round(profit, 2),
        "profit_rate": round(profit_rate, 2),
        "items": items,
    }


# ============================================================
# Daily Report + Personal Actions
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


class DailyReport(BaseModel):
    date: dt.date
    market_comment_en: str
    market_comment_zh: str
    action_suggestion_en: str
    action_suggestion_zh: str


def _parse_daily_report(text: str):
    market_zh = suggest_zh = market_en = suggest_en = ""
    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith("MARKET_ZH"):
            market_zh = s.split(":", 1)[1].strip()
        elif s.startswith("SUGGEST_ZH"):
            suggest_zh = s.split(":", 1)[1].strip()
        elif s.startswith("MARKET_EN"):
            market_en = s.split(":", 1)[1].strip()
        elif s.startswith("SUGGEST_EN"):
            suggest_en = s.split(":", 1)[1].strip()
    return market_zh, suggest_zh, market_en, suggest_en


async def fetch_market_snapshot():
    symbols = {
        "^GSPC": "S&P 500",
        "^IXIC": "NASDAQ",
        "^DJI": "Dow Jones",
    }

    results = []

    for symbol, name in symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info or {}

            price = info.get("lastPrice")
            prev = info.get("previousClose")

            change = None
            change_pct = None

            if price and prev:
                change = price - prev
                change_pct = change / prev * 100

            results.append({
                "symbol": symbol,
                "name": name,
                "price": price,
                "change": change,
                "changePercent": change_pct,
            })

        except Exception as e:
            print("Market fetch error:", symbol, e)

    return results



async def generate_market_report(snapshot: list[dict]) -> DailyReport:
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI KEY 未設定")

    lines = []
    for s in snapshot:
        if s.get("price") is None:
            continue
        lines.append(
            f"{s['symbol']} ({s['name']}): {s['price']:.2f} ({s['change']:+.2f}, {s['changePercent']:+.2f}%)"
        )
    market_text = "\n".join(lines)

    prompt = f"""
你是一位專業的國際金融市場與美股分析師。

以下是重要指數與科技股的即時行情：

{market_text}

請輸出下列格式（每項一行、用冒號）：

MARKET_ZH: <繁體中文市場評論>
SUGGEST_ZH: <繁體中文操作建議>
MARKET_EN: <English market comment>
SUGGEST_EN: <English trading suggestions>
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    full = resp.choices[0].message.content or ""
    market_zh, suggest_zh, market_en, suggest_en = _parse_daily_report(full)

    if not market_zh:
        market_zh = "今日市場資訊不足。"
    if not suggest_zh:
        suggest_zh = "今日無法提供操作建議。"
    if not market_en:
        market_en = "Market data insufficient today."
    if not suggest_en:
        suggest_en = "No actionable trading suggestions."

    today = dt.date.today()

    # 寫入 daily_reports（欄位與你 DB 一致）
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO daily_reports
        (date, market_comment_en, market_comment_zh, action_suggestion_en, action_suggestion_zh, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (today.isoformat(), market_en, market_zh, suggest_en, suggest_zh),
    )
    conn.commit()
    conn.close()

    return DailyReport(
        date=today,
        market_comment_en=market_en,
        market_comment_zh=market_zh,
        action_suggestion_en=suggest_en,
        action_suggestion_zh=suggest_zh,
    )


def get_user_holdings(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT symbol, shares, cost_basis
        FROM holdings
        WHERE user_id=?
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "symbol": r["symbol"],
            "shares": float(r["shares"]),
            "cost_basis": float(r["cost_basis"]),
        }
        for r in rows
    ]


def enrich_holdings_with_price(holdings: list) -> list:
    enriched = []
    for h in holdings:
        symbol = h["symbol"].upper()
        try:
            ticker = yf.Ticker(symbol)
            fast = ticker.fast_info or {}
            price = fast.get("lastPrice")
            if price is None:
                info = ticker.info or {}
                price = info.get("regularMarketPrice")
        except Exception as e:
            print("[price error]", symbol, e)
            price = 0.0

        price = float(price or 0.0)
        cost_basis = float(h["cost_basis"] or 0.0)

        profit_rate = 0.0
        if cost_basis > 0 and price > 0:
            profit_rate = (price - cost_basis) / cost_basis * 100

        enriched.append(
            {
                **h,
                "current_price": round(price, 2),
                "profit_rate": round(profit_rate, 2),
            }
        )
    return enriched


async def generate_personal_actions(user_holdings: list) -> list:
    """
    回傳 JSON array:
    [
      {"symbol":"AAPL","action":"HOLD","reason_zh":"...","risk_level":"LOW"}
    ]
    """
    if not openai_client:
        return []

    if not user_holdings:
        return []

    holding_lines = []
    for h in user_holdings:
        holding_lines.append(
            f"{h['symbol']} | 現價 {h['current_price']} | 成本 {h['cost_basis']} | 損益 {h['profit_rate']}%"
        )
    holdings_text = "\n".join(holding_lines)

    prompt = f"""
你是一位專業投資顧問（偏穩健、給一般投資人看的建議）。
以下是使用者目前持股與即時狀態：

{holdings_text}

請針對「每一檔股票」給出：
- action: BUY / HOLD / SELL（三選一）
- reason_zh: 繁體中文理由（50~120字，避免艱深術語）
- risk_level: LOW / MEDIUM / HIGH（三選一）

只回傳「JSON array」，不要加任何多餘文字。格式如下：

[
  {{
    "symbol": "AAPL",
    "action": "HOLD",
    "reason_zh": "理由…",
    "risk_level": "LOW"
  }}
]
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw = (resp.choices[0].message.content or "").strip()

    # 只擷取 JSON 區塊，避免模型偶爾加註解
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []

    try:
        return json.loads(raw[start : end + 1])
    except Exception as e:
        print("[personal_actions json parse error]", e, raw)
        return []


def get_user_holdings_for_advice(user_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT symbol, shares, cost_basis
        FROM holdings
        WHERE user_id=?
    """, (user_id,))

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "symbol": r["symbol"],
            "shares": r["shares"],
            "cost_basis": r["cost_basis"],
        }
        for r in rows
    ]

async def generate_personal_advice(user_id: int, holdings: list) -> dict:
    if not openai_client:
        return {
            "zh": "系統尚未設定 AI 金鑰，暫無個人化建議。",
            "en": "AI key not configured.",
        }

    if not holdings:
        return {
            "zh": "你目前尚未持有任何股票，請先新增持股。",
            "en": "You currently have no holdings.",
        }

    lines = []
    for h in holdings:
        lines.append(
            f"{h['symbol']}, shares={h['shares']}, avg_price={h['cost_basis']}"
        )

    prompt = f"""
以下是某位投資者目前的股票持股資訊：

{chr(10).join(lines)}

請根據目前市場環境，提供「實務導向」的操作建議：
- 是否應該：續抱 / 逢高減碼 / 觀察 / 分批加碼
- 用條列方式
- 不要給買賣價格
- 不要使用誇張語氣

請輸出格式：

ADVICE_ZH:
ADVICE_EN:
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    text = resp.choices[0].message.content

    zh = en = ""
    for line in text.splitlines():
        if line.startswith("ADVICE_ZH"):
            zh = line.split(":", 1)[1].strip()
        elif line.startswith("ADVICE_EN"):
            en = line.split(":", 1)[1].strip()

    return {"zh": zh, "en": en}

def save_personal_advice(
    user_id: int,
    date: str,
    actions: list,
    content_en: str | None = None
):
    import json

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO personal_stock_advice
        (user_id, date, content_zh, content_en)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        date,
        json.dumps(actions, ensure_ascii=False),
        content_en,
    ))

    conn.commit()
    conn.close()

def get_cached_personal_advice(user_id: int, date: str):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT content_zh
        FROM personal_stock_advice
        WHERE user_id=? AND date=?
    """, (user_id, date))

    row = cur.fetchone()
    conn.close()

    if not row or not row["content_zh"]:
        return None

    import json
    return json.loads(row["content_zh"])

async def get_or_create_personal_stock_advice(
    user_id: int,
    enriched_holdings: list
):
    today = dt.date.today().isoformat()

    # 1️⃣ 先查 DB 快取
    cached = get_cached_personal_advice(user_id, today)
    if cached:
        print("✅ use cached personal_stock_advice")
        return cached

    # 2️⃣ 沒快取 → 產生（GPT）
    print("⚠️ generate personal_stock_advice via GPT")
    actions = await generate_personal_actions(enriched_holdings)

    # 3️⃣ 存 DB
    save_personal_advice(
        user_id=user_id,
        date=today,
        actions=actions,
    )

    return actions


@app.get("/reports/today")
async def report_today(current: User = Depends(get_current_user)):
    """
    回傳：
    - 市場報告（daily_reports）
    - personal_actions（依使用者持股產生）
    """
    today = dt.date.today().isoformat()

    # =============================
    # 1️⃣ 市場報告（先查 DB）
    # =============================
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT date, market_comment_en, market_comment_zh,
               action_suggestion_en, action_suggestion_zh
        FROM daily_reports
        WHERE date=?
        """,
        (today,),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        base_report = {
            "date": row["date"],
            "market_comment_en": row["market_comment_en"],
            "market_comment_zh": row["market_comment_zh"],
            "action_suggestion_en": row["action_suggestion_en"],
            "action_suggestion_zh": row["action_suggestion_zh"],
        }
    else:
        # ⚠️ 注意：fetch_market_snapshot 是「同步」function
        snapshot = await fetch_market_snapshot()
        dr = await generate_market_report(snapshot)

        base_report = {
            "date": dr.date.isoformat(),
            "market_comment_en": dr.market_comment_en,
            "market_comment_zh": dr.market_comment_zh,
            "action_suggestion_en": dr.action_suggestion_en,
            "action_suggestion_zh": dr.action_suggestion_zh,
        }

    # =============================
    # 2️⃣ 個人化建議（依持股）
    # =============================
    try:
        holdings = get_user_holdings(current.id)
    except Exception as e:
        print("❌ get_user_holdings error:", e)
        holdings = []

    personal_actions = []

    if holdings:
        try:
            enriched = enrich_holdings_with_price(holdings)
            if enriched:
                personal_actions = await get_or_create_personal_stock_advice(current.id, enriched)
            enriched
        except Exception as e:
            # ⚠️ 個人化建議失敗不影響整個報告
            print("❌ personal_actions error:", e)
            personal_actions = []

    # =============================
    # 3️⃣ 統一回傳
    # =============================
    return {
        **base_report,
        "personal_actions": personal_actions,
    }


@app.post("/reports/personal/regenerate")
async def regenerate_personal_advice(
    current: User = Depends(get_current_user)
):
    """
    強制重新產生「今日個人化持股建議」
    - 只影響本人
    - 覆蓋 personal_stock_advice 今日資料
    """
    today = dt.date.today().isoformat()

    # 1️⃣ 取得使用者持股
    holdings = get_user_holdings(current.id)
    if not holdings:
        return {
            "ok": False,
            "message": "尚未有持股，無法產生個人化建議",
            "personal_actions": [],
        }

    enriched = enrich_holdings_with_price(holdings)
    if not enriched:
        return {
            "ok": False,
            "message": "持股價格取得失敗",
            "personal_actions": [],
        }

    # 2️⃣ 強制呼叫 GPT
    actions = await generate_personal_actions(enriched)

    # 3️⃣ 覆蓋寫入 DB（今天）
    save_personal_advice(
        user_id=current.id,
        date=today,
        actions=actions,
    )

    return {
        "ok": True,
        "message": "已重新產生今日個人化建議",
        "personal_actions": actions,
    }


# ============================================================
# OCR (optional)
# ============================================================

@app.post("/holdings/ocr")
async def ocr_holdings(file: UploadFile = File(...), current: User = Depends(get_current_user)):
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI KEY 未設定")

    content = await file.read()
    b64 = base64.b64encode(content).decode()

    prompt = """
請從股票 APP 截圖中讀取持股資訊。
只回傳 JSON array，例如：

[
  { "symbol": "AAPL", "shares": 10, "cost_basis": 185.5 },
  { "symbol": "TSLA", "shares": 5, "cost_basis": 250.0 }
]
"""

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "請解析這張圖片"},
                    {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"},
                ],
            },
        ],
        temperature=0.2,
    )

    raw = (resp.choices[0].message.content or "").strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return {"items": []}

    try:
        return {"items": json.loads(raw[start : end + 1])}
    except:
        return {"items": []}


# ============================================================
# Scheduler: generate daily report at 22:00 Asia/Taipei
# ============================================================

TAIPEI_TZ = dt.timezone(dt.timedelta(hours=8))
scheduler = AsyncIOScheduler(timezone=TAIPEI_TZ)


async def scheduled_generate_report():
    try:
        print("[Scheduler] Start generating daily report...")
        snapshot =  fetch_market_snapshot()
        await generate_market_report(snapshot)
        print("[Scheduler] Daily report generated.")
    except Exception as e:
        print("[Scheduler] Error:", e)


@app.on_event("startup")
async def on_startup():
    init_db()
    scheduler.add_job(
        scheduled_generate_report,
        "cron",
        hour=22,
        minute=0,
        second=0,
        id="daily_report_22",
        replace_existing=True,
    )
    scheduler.start()
    print("[Scheduler] started")


@app.on_event("shutdown")
async def on_shutdown():
    scheduler.shutdown()
    print("[Scheduler] shutdown")
