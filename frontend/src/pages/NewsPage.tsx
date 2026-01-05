import React, { useEffect, useState } from "react";

interface NewsItem {
  title: string;
  url: string;
  summary_en: string;
  summary_zh: string;
  source: string;
  published_at: string;
  image_url: string;
  sentiment?: string; // "利多" | "中性" | "利空"
}

interface NewsResponse {
  international: NewsItem[];
  us_finance: NewsItem[];
}

export default function NewsPage() {
  const [news, setNews] = useState<NewsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/news")
      .then((res) => res.json())
      .then((data) => {
        setNews(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">📈 今日科技財經新聞</h1>

      {loading ? (
        <LoadingSkeleton />
      ) : (
        <>
          <Section
            title="🌍 國際科技財經新聞"
            items={news?.international || []}
          />

          <Section
            title="🇺🇸 美國科技財經新聞"
            items={news?.us_finance || []}
          />
        </>
      )}
    </div>
  );
}

// ----------------- Section -----------------
const Section = ({ title, items }: { title: string; items: NewsItem[] }) => (
  <div className="mb-10">
    <h2 className="text-2xl font-semibold mb-3">{title}</h2>

    <div className="space-y-4">
      {items.map((item, idx) => (
        <NewsCard key={idx} item={item} />
      ))}
    </div>
  </div>
);

// ----------------- Sentiment 顏色 -----------------
function sentimentColor(sent: string | undefined) {
  if (sent === "利多") return "bg-green-500";
  if (sent === "利空") return "bg-red-500";
  return "bg-gray-300"; // 中性
}

// ----------------- News Card -----------------
const NewsCard = ({ item }: { item: NewsItem }) => {
  // sentiment 顏色
  const sentimentColor = 
    item.sentiment === "利多"
      ? "bg-green-500"
      : item.sentiment === "利空"
      ? "bg-red-500"
      : "bg-gray-400";

  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-white shadow hover:shadow-lg transition rounded-lg overflow-hidden border border-gray-200"
    >
      {/* Sentiment 色條 */}
      <div className={`h-2 w-full ${sentimentColor}`} />

      {/* 圖片 */}
      {item.image_url && (
        <img
          src={item.image_url}
          alt={item.title}
          className="w-full h-48 object-cover"
        />
      )}

      {/* 文字內容 */}
      <div className="p-4">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-xl font-bold">{item.title}</h3>

          {/* sentiment 顯示文字 */}
          <span
            className={`text-sm px-2 py-1 rounded ${
              item.sentiment === "利多"
                ? "bg-green-100 text-green-700"
                : item.sentiment === "利空"
                ? "bg-red-100 text-red-700"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {item.sentiment}
          </span>
        </div>

        <p className="text-gray-700 mb-2 leading-relaxed">
          {item.summary_zh}
        </p>

        <p className="text-gray-500 text-sm italic leading-relaxed">
          {item.summary_en}
        </p>

        <div className="text-xs text-gray-400 mt-3 flex justify-between">
          <span>{item.source}</span>
          <span>{new Date(item.published_at).toLocaleString()}</span>
        </div>
      </div>
    </a>
  );
};


// ----------------- Loading Skeleton -----------------
const LoadingSkeleton = () => (
  <div className="animate-pulse space-y-4">
    {[1, 2, 3, 4, 5].map((i) => (
      <div key={i} className="bg-gray-200 h-40 rounded-lg"></div>
    ))}
  </div>
);
