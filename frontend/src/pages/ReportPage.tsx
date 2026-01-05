// src/pages/ReportPage.tsx
import { useEffect, useState } from "react"
import { api } from "../services/api"

/* ============================= */
/* 型別定義                      */
/* ============================= */

interface PersonalAction {
  symbol: string
  action: "BUY" | "HOLD" | "SELL"
  reason_zh: string
  risk_level: "LOW" | "MEDIUM" | "HIGH"
}

interface DailyReport {
  date: string
  market_comment_en: string
  market_comment_zh: string
  action_suggestion_en: string
  action_suggestion_zh: string

  // ⭐ 新增（後端尚未給也不會壞）
  personal_actions?: PersonalAction[]
}

/* ============================= */
/* Component                     */
/* ============================= */

export function ReportPage() {
  const [report, setReport] = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [regenerating, setRegenerating] = useState(false);

  const regeneratePersonalAdvice = async () => {
  if (!confirm("確定要重新產生今日的個人化持股建議嗎？")) {
    return;
  }

  try {
    setRegenerating(true);

    const res = await api.post("/reports/personal/regenerate");

    setReport((prev: any) => {
      if (!prev) return prev;
      return {
        ...prev,
        personal_actions: res.data.personal_actions,
      };
    });
  } catch (err: any) {
    alert(err.response?.data?.message || "重新產生失敗");
  } finally {
    setRegenerating(false);
  }
};



  const loadReport = async () => {
    try {
      setLoading(true)
      setError("")
      const res = await api.get<DailyReport>("/reports/today")
      setReport(res.data)
    } catch (err: any) {
      console.error(err)
      setError(err.response?.data?.detail || "載入今日報告失敗")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReport()
  }, [])

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* ================= Header ================= */}
        <div style={styles.headerRow}>
          <h2 style={{ margin: 0 }}>📈 今日國際市場報告</h2>
          <button
            style={styles.refreshBtn}
            onClick={loadReport}
            disabled={loading}
          >
            {loading ? "更新中…" : "重新整理"}
          </button>
        </div>

        <p style={styles.dateText}>
          日期：{report ? report.date : "--"}
          <br />
          （每日產生一次，首次開啟當日自動生成）
        </p>

        {loading && <p>AI 正在為你整理今日市場…</p>}
        {error && <p style={{ color: "red" }}>{error}</p>}

        {/* ================= 全球市場 ================= */}
        {!loading && report && (
          <>
            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>市場總觀（中文）</h3>
              <p style={styles.text}>{report.market_comment_zh}</p>
            </section>

            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>今日操作建議（中文）</h3>
              <p style={styles.text}>{report.action_suggestion_zh}</p>
            </section>

            {/* ================= 個人化持股建議 ================= */}
            <section style={{ marginTop: 20 }}>
              {/* 標題列 + 重新產生按鈕 */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 10,
                }}
              >
                <h3 style={styles.sectionTitle}>📌 我的持股操作建議</h3>

                <button
                  onClick={regeneratePersonalAdvice}
                  disabled={regenerating}
                  style={{
                    padding: "6px 10px",
                    fontSize: 13,
                    borderRadius: 8,
                    border: "1px solid #0d6efd",
                    background: regenerating ? "#e5e7eb" : "#ffffff",
                    color: "#0d6efd",
                    cursor: regenerating ? "not-allowed" : "pointer",
                    fontWeight: 500,
                  }}
                >
                  {regenerating ? "產生中…" : "🔄 重新產生"}
                </button>
              </div>

              {report.personal_actions && report.personal_actions.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {report.personal_actions.map((p) => {
                    const color =
                      p.action === "BUY"
                        ? "#16a34a"
                        : p.action === "SELL"
                        ? "#dc2626"
                        : "#2563eb";

                    return (
                      <div
                        key={p.symbol}
                        style={{
                          border: "1px solid #e5e7eb",
                          borderRadius: 10,
                          padding: 12,
                          background: "#ffffff",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: 6,
                          }}
                        >
                          <strong>{p.symbol}</strong>
                          <span
                            style={{
                              color,
                              fontWeight: 700,
                              fontSize: 13,
                            }}
                          >
                            {p.action}
                          </span>
                        </div>

                        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5 }}>
                          {p.reason_zh}
                        </p>

                        <div
                          style={{
                            marginTop: 6,
                            fontSize: 12,
                            color: "#6b7280",
                          }}
                        >
                          風險等級：{p.risk_level}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p style={{ fontSize: 14, color: "#6b7280" }}>
                  尚未產生與你持股相關的操作建議。
                </p>
              )}
            </section>


            {/* ================= 英文 ================= */}
            <details style={styles.details}>
              <summary style={styles.summary}>顯示英文版本</summary>
              <section style={styles.section}>
                <h3 style={styles.sectionTitle}>Market Overview (EN)</h3>
                <p style={styles.text}>{report.market_comment_en}</p>
              </section>
              <section style={styles.section}>
                <h3 style={styles.sectionTitle}>Trading Suggestions (EN)</h3>
                <p style={styles.text}>{report.action_suggestion_en}</p>
              </section>
            </details>
          </>
        )}
      </div>
    </div>
  )
}

/* ============================= */
/* Styles                        */
/* ============================= */

const styles: { [key: string]: React.CSSProperties } = {
  page: {
    maxWidth: 800,
    margin: "20px auto",
    padding: "0 12px",
  },
  card: {
    background: "#ffffff",
    borderRadius: 12,
    padding: 20,
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  },
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  refreshBtn: {
    padding: "6px 12px",
    fontSize: 14,
    borderRadius: 6,
    border: "1px solid #0d6efd",
    background: "#0d6efd",
    color: "#fff",
    cursor: "pointer",
  },
  dateText: {
    fontSize: 13,
    color: "#666",
    marginTop: 0,
    marginBottom: 16,
    lineHeight: 1.4,
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    margin: "0 0 6px 0",
    fontSize: 16,
  },
  text: {
    margin: 0,
    whiteSpace: "pre-line",
    lineHeight: 1.6,
    fontSize: 14,
  },
  details: {
    marginTop: 12,
    fontSize: 14,
  },
  summary: {
    cursor: "pointer",
    color: "#0d6efd",
    listStyle: "none",
  },
}
