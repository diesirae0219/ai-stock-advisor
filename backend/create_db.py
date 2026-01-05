import sqlite3

conn = sqlite3.connect("news.db")
cur = conn.cursor()

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

conn.commit()
conn.close()

print("SQLite 資料庫建立完成：news.db")
