# database.py — SQLite 連線 & Table 初始化
import sqlite3
import os

DB_PATH = "news.db"


def get_db():
    """
    回傳 SQLite 連線（請記得用完後 close）
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 讓結果可 dict 取值
    return conn


def init_db():
    """
    初始化所有需要的資料表
    若資料表已存在，不會覆蓋。
    """
    print("[DB] Initializing database tables...")

    conn = get_db()
    cur = conn.cursor()

    # =============================
    # Users 用戶資料表
    # =============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        nickname TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # =============================
    # Holdings 個人持股資料表
    # =============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        shares REAL NOT NULL,
        cost_basis REAL NOT NULL,
        purchase_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)

    # =============================
    # Daily Reports 每日 AI 報告（行情版）
    # =============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_reports (
        date TEXT PRIMARY KEY,
        market_comment_en TEXT,
        market_comment_zh TEXT,
        action_suggestion_en TEXT,
        action_suggestion_zh TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # =============================
    # News Cache 新聞快取（可選用）
    # =============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS news_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        original_title TEXT,
        translated_title TEXT,
        summary_en TEXT,
        summary_zh TEXT,
        sentiment TEXT,
        source TEXT,
        url TEXT,
        published_at TEXT,
        image_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

  # =============================
    # Personal Stock Advice 個人化操作建議
    # =============================
    cur.execute("""
    CREATE TABLE IF NOT EXISTS personal_stock_advice (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        content_zh TEXT,
        content_en TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, date),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)


    conn.commit()
    conn.close()

    print("[DB] All tables are ready.")
