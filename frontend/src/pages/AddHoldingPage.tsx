import { useState, useEffect } from "react";
import { api } from "../services/api";
import { useNavigate } from "react-router-dom";

export function AddHoldingPage() {
  const navigate = useNavigate();

  const [symbol, setSymbol] = useState("");
  const [name, setName] = useState("");
  const [avgPrice, setAvgPrice] = useState("");
  const [shares, setShares] = useState("");
  const [purchaseDate, setPurchaseDate] = useState("");
  const [error, setError] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);

  /** ⭐ 自動查詢股票名稱（debounce） */
  useEffect(() => {
    if (symbol.trim().length < 2) return;

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        setLookupLoading(true);

        const res = await api.get(`/stocks/info?symbol=${symbol.trim()}`, {
          signal: controller.signal,
        });

        if (res.data?.valid && !name) {
          setName(res.data.name);
        }
      } catch (e) {
        // 查不到就好，不影響輸入
      } finally {
        setLookupLoading(false);
      }
    }, 500);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [symbol]);

  /** 儲存持股 */
 const handleSubmit = async () => {
  if (!symbol || !avgPrice || !shares) {
    setError("請至少填寫：股票代號 / 均價 / 股數");
    return;
  }

  try {
    setError("");

    await api.post("/holdings", {
    symbol: symbol.toUpperCase(),
    shares: Number(shares),
    cost_basis: Number(avgPrice),
    purchase_date: purchaseDate || null,
  });

    alert("新增成功！");
    navigate("/portfolio");
  } catch (err: any) {
    console.error(err.response?.data || err);
    setError(err.response?.data?.detail || "新增失敗");
  }
};

  return (
    <div className="app-content">
      <h2 className="section-title">➕ 新增持股</h2>

      {/* 股票代號 */}
      <div className="ios-card">
        <label className="ios-label">股票代號（必填）</label>
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          onBlur={() => setSymbol(symbol.trim().toUpperCase())}
          placeholder="AAPL / NVDA（純數字視為台股）"
          className="ios-input"
        />
      </div>

      {/* 名稱 */}
      <div className="ios-card">
        <label className="ios-label">
          股票名稱 {lookupLoading && "（查詢中…）"}
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="自動帶出，可手動修改"
          className="ios-input"
        />
      </div>

      {/* 均價 */}
      <div className="ios-card">
        <label className="ios-label">買進均價</label>
        <input
          type="number"
          inputMode="decimal"
          value={avgPrice}
          onChange={(e) => setAvgPrice(e.target.value)}
          className="ios-input"
        />
      </div>

      {/* 股數 */}
      <div className="ios-card">
        <label className="ios-label">持有股數</label>
        <input
          type="number"
          inputMode="decimal"
          value={shares}
          onChange={(e) => setShares(e.target.value)}
          className="ios-input"
        />
      </div>

      {/* 日期 */}
      <div className="ios-card">
        <label className="ios-label">買進日期（可選）</label>
        <input
          type="date"
          value={purchaseDate}
          onChange={(e) => setPurchaseDate(e.target.value)}
          className="ios-input"
        />
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <button className="ios-primary-btn" onClick={handleSubmit}>
        新增持股
      </button>
    </div>
  );
}
