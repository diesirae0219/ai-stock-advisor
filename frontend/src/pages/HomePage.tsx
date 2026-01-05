import { useEffect, useState } from 'react'
import { api } from '../services/api'

interface NewsItem {
  title: string;
  url: string;
  summary_en: string;
  summary_zh: string;
  source: string;
  published_at: string;
  image_url: string;
  sentiment?: "利多" | "中性" | "利空" | string;
}

interface NewsResponse {
  international: NewsItem[]
  us_finance: NewsItem[]
}

function getLastUpdated(items: NewsItem[]) {
  if (!items || items.length === 0) return "未知";

  const times = items
    .map((i) => new Date(i.published_at).getTime())
    .filter((t) => !isNaN(t));

  if (times.length === 0) return "未知";

  const latest = new Date(Math.max(...times));

  return latest.toLocaleString("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}


export function HomePage() {
  const [data, setData] = useState<NewsResponse | null>(null)

  useEffect(() => {
    api.get('/news').then((res) => setData(res.data))
  }, [])

  if (!data) {
    return <p style={{ padding: 12 }}>載入中…</p>
  }

  // sentiment 顏色
  const getSentimentColor = (s?: string) => {
    if (s === "利多") return "#16a34a" // green-600
    if (s === "利空") return "#dc2626" // red-600
    return "#6b7280" // gray-500
  }

  const getBadgeBG = (s?: string) => {
    if (s === "利多") return "#dcfce7" // green-100
    if (s === "利空") return "#fee2e2" // red-100
    return "#f3f4f6" // gray-100
  }

  const renderNewsBlock = (title: string, subtitle: string, items: NewsItem[]) => (
    <section style={{ marginBottom: 20 }}>
  <div style={{ marginBottom: 8 }}>
      <div className="section-title">{title}</div>
      <div className="section-subtitle">{subtitle}</div>

      {/* 最後更新時間 */}
      <div
        style={{
          fontSize: 12,
          color: "#888",
          marginTop: 4,
        }}
      >
        最後更新時間：{getLastUpdated(items)}
      </div>
    </div>

      

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.slice(0, 5).map((n, idx) => (
          <a
            key={idx}
            href={n.url}
            target="_blank"
            rel="noreferrer"
            className="news-card-link"
          >
            <div style={{ display: "flex", padding: "6px 0" }}>
              <img
                src={n.image_url || 'https://via.placeholder.com/120x90?text=News'}
                className="news-card-thumb"
              />

              <div style={{ flex: 1, marginLeft: 10 }}>

                {/* 標題 + sentiment 標籤 */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div className="news-card-title">{n.title}</div>

                  {n.sentiment && (
                    <div
                      style={{
                        fontSize: 12,
                        padding: "2px 6px",
                        borderRadius: 6,
                        backgroundColor: getBadgeBG(n.sentiment),
                        color: getSentimentColor(n.sentiment),
                        marginLeft: 8,
                        whiteSpace: "nowrap"
                      }}
                    >
                      {n.sentiment}
                    </div>
                  )}
                </div>

                {/* 中文摘要 */}
                <div className="news-card-summary">{n.summary_zh}</div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </section>
  )

  return (
    <div>
      {renderNewsBlock('🌍 國際頭條', '掌握全球重大事件，快速了解市場氣氛。', data.international)}
      {renderNewsBlock('💵 美國財經頭條', '鎖定美股與美國經濟重點消息。', data.us_finance)}
    </div>
  )
}
