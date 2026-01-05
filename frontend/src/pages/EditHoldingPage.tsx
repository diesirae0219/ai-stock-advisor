import { useEffect, useState } from "react";
import { api } from "../services/api";
import { useNavigate, useParams } from "react-router-dom";

export function EditHoldingPage() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();

  const [shares, setShares] = useState("");
  const [avgPrice, setAvgPrice] = useState("");
  const [purchaseDate, setPurchaseDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /** 進頁面先載入原始資料 */
  useEffect(() => {
    const loadHolding = async () => {
      try {
        const res = await api.get("/portfolio/summary");
        const item = res.data.items.find(
          (i: any) => i.symbol === symbol
        );

        if (!item) {
          setError("找不到持股資料");
          return;
        }

        setShares(item.shares.toString());
        setAvgPrice(item.avg_price.toString());
      } catch (e) {
        setError("載入失敗");
      } finally {
        setLoading(false);
      }
    };

    loadHolding();
  }, [symbol]);

  /** 更新 */
  const handleSubmit = async () => {
    try {
      await api.put(`/holdings/by-symbol/${symbol}`, {
        symbol,
        shares: Number(shares),
        cost_basis: Number(avgPrice),
        purchase_date: purchaseDate || null,
      });

      alert("更新成功");
      navigate("/portfolio");
    } catch (e: any) {
      setError(e.response?.data?.detail || "更新失敗");
    }
  };

  if (loading) return <div>載入中…</div>;

  return (
    <div className="app-content">
      <h2>✏️ 編輯持股</h2>

      <div className="ios-card">
        <div className="label">股票代號</div>
        <input value={symbol} disabled className="ios-input" />
      </div>

      <div className="ios-card">
        <div className="label">買進均價</div>
        <input
          type="number"
          value={avgPrice}
          onChange={(e) => setAvgPrice(e.target.value)}
          className="ios-input"
        />
      </div>

      <div className="ios-card">
        <div className="label">持有股數</div>
        <input
          type="number"
          value={shares}
          onChange={(e) => setShares(e.target.value)}
          className="ios-input"
        />
      </div>

      <div className="ios-card">
        <div className="label">買進日期</div>
        <input
          type="date"
          value={purchaseDate}
          onChange={(e) => setPurchaseDate(e.target.value)}
          className="ios-input"
        />
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <button className="primary-btn" onClick={handleSubmit}>
        儲存修改
      </button>
    </div>
  );
}
