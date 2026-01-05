import { useState, useEffect } from "react";
import { api } from "../services/api";
import { useNavigate } from "react-router-dom";

interface HoldingSummary {
  id?: number;              // ⚠️ 若後端之後補 id，可直接用
  symbol: string;
  shares: number;
  avg_price: number;
  current_price: number;
  profit: number;
  profit_rate: number;
}

interface PortfolioSummary {
  total_cost: number;
  total_value: number;
  profit: number;
  profit_rate: number;
  items: HoldingSummary[];
}

export function PortfolioPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  /** 載入投資組合 */
  const loadPortfolio = async () => {
    try {
      setLoading(true);
      const res = await api.get("/portfolio/summary");
      setSummary(res.data);
    } catch (err) {
      console.error("取得投資組合失敗", err);
      alert("取得投資組合失敗，請重新登入");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortfolio();
  }, []);

  /** 刪除持股（依 symbol，目前 summary 沒有 id） */
  const deleteHolding = async (symbol: string) => {
    if (!window.confirm(`確定要移除 ${symbol} 嗎？`)) return;

    try {
      await api.delete(`/holdings/by-symbol/${symbol}`);
      loadPortfolio();
    } catch (e) {
      alert("刪除失敗");
    }
  };

  /** iOS 按鈕 */
  const ActionButton = ({ text, onClick }: any) => (
    <button
      onClick={onClick}
      style={{
        padding: "10px 14px",
        borderRadius: 12,
        background: "var(--accent-soft)",
        border: "none",
        fontSize: 14,
        color: "var(--accent)",
        cursor: "pointer",
      }}
    >
      {text}
    </button>
  );

  if (loading) return <div>讀取中…</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 12 }}>📊 我的持股</h2>

      {/* ===== 操作列 ===== */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <ActionButton
          text="➕ 新增持股"
          onClick={() => navigate("/portfolio/add")}
        />
        <ActionButton
          text="📷 上傳截圖辨識"
          onClick={() => alert("開發中")}
        />
      </div>

      {/* ===== 投資組合總覽 ===== */}
      {summary && (
        <div className="ios-card" style={{ padding: 16, marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 10px 0" }}>📈 投資組合總覽</h3>

          <div className="summary-row">
            <span>總成本</span>
            <span>${summary.total_cost.toLocaleString()}</span>
          </div>

          <div className="summary-row">
            <span>目前市值</span>
            <span>${summary.total_value.toLocaleString()}</span>
          </div>

          <div className="summary-row">
            <span>未實現損益</span>
            <span
              style={{
                color: summary.profit >= 0 ? "#16a34a" : "#dc2626",
                fontWeight: 600,
              }}
            >
              {summary.profit >= 0 ? "+" : ""}
              {summary.profit.toLocaleString()}（
              {summary.profit_rate.toFixed(2)}%）
            </span>
          </div>
        </div>
      )}

      {/* ===== 持股清單 ===== */}
      {summary?.items.length === 0 && (
        <div style={{ padding: 16, color: "#6b7280" }}>
          尚無持股，點擊「新增持股」開始記錄。
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {summary?.items.map((h) => {
          const isProfit = h.profit >= 0;

          return (
            <div key={h.symbol} className="ios-card" style={{ padding: 16 }}>
              {/* 標題列 */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ fontSize: 18, fontWeight: 700 }}>
                  {h.symbol}
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    onClick={() =>
                      navigate(`/portfolio/edit/${h.symbol}`)
                    }
                    style={iconBtn}
                  >
                    ✏️
                  </button>
                  <button
                    onClick={() => deleteHolding(h.symbol)}
                    style={{ ...iconBtn, color: "#dc2626" }}
                  >
                    🗑
                  </button>
                </div>
              </div>

              {/* 中段 */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginTop: 10,
                }}
              >
                <div>
                  <div style={label}>買進均價</div>
                  <div>{h.avg_price}</div>
                </div>
                <div>
                  <div style={label}>持有股數</div>
                  <div>{h.shares}</div>
                </div>
              </div>

              {/* 底段 */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginTop: 16,
                }}
              >
                <div>
                  <div style={label}>現價</div>
                  <div>
                    {h.current_price}{" "}
                    <span
                      style={{
                        color: isProfit ? "#16a34a" : "#dc2626",
                        fontWeight: 600,
                      }}
                    >
                      ({isProfit ? "+" : ""}
                      {h.profit_rate.toFixed(2)}%)
                    </span>
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <div style={label}>總損益</div>
                  <div
                    style={{
                      fontSize: 18,
                      fontWeight: 700,
                      color: isProfit ? "#16a34a" : "#dc2626",
                    }}
                  >
                    {isProfit ? "+" : ""}
                    {h.profit.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ===== 小樣式 ===== */

const label: React.CSSProperties = {
  fontSize: 13,
  color: "#6b7280",
};

const iconBtn: React.CSSProperties = {
  background: "transparent",
  border: "none",
  fontSize: 18,
  cursor: "pointer",
};
