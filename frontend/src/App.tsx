import { Routes, Route, Link, useLocation, useNavigate, Navigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { FiMenu, FiHome, FiPieChart, FiFileText, FiUser } from "react-icons/fi";
import { api } from "./services/api";

import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { ProfilePage } from "./pages/ProfilePage";
import { PortfolioPage } from "./pages/PortfolioPage";
import NewsPage from "./pages/NewsPage";
import { ReportPage } from "./pages/ReportPage";
import { RegisterPage } from "./pages/RegisterPage";
import { AddHoldingPage } from "./pages/AddHoldingPage";
import { EditHoldingPage } from "./pages/EditHoldingPage";


/* ============================= */
/* 🔐 Route Guard 元件           */
/* ============================= */
function RequireAuth({
  user,
  children,
}: {
  user: any | null;
  children: JSX.Element;
}) {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [user, setUser] = useState<any | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);

  const location = useLocation();
  const navigate = useNavigate();
  const activePath = location.pathname;

  /** 底部 Tab active 判斷 */
  const isTabActive = (path: string) => activePath === path;

  /* ============================= */
  /* 🔁 App 初始化：驗證 token     */
  /* ============================= */
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      setLoadingUser(false);
      return;
    }

    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;

    api
      .get("/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        // token 無效 → 強制登出
        localStorage.removeItem("token");
        delete api.defaults.headers.common["Authorization"];
        setUser(null);
      })
      .finally(() => setLoadingUser(false));
  }, []);

  /* ============================= */
  /* 🚪 登出                      */
  /* ============================= */
  const logout = () => {
    localStorage.removeItem("token");
    delete api.defaults.headers.common["Authorization"];
    setUser(null);
    navigate("/login");
  };

  /* ============================= */
  /* ⏳ 等待 /me 避免畫面跳動      */
  /* ============================= */
  if (loadingUser) {
    return <div style={{ padding: 20 }}>載入中…</div>;
  }

  return (
    <div className="app-shell">
      {/* ========================== */}
      {/* 🔝 Header */}
      {/* ========================== */}
      <header className="app-header">
        <button
          onClick={() => setMenuOpen((v) => !v)}
          style={{
            background: "transparent",
            border: "none",
            padding: 4,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
          }}
        >
          <FiMenu size={22} />
        </button>

        <h1 className="app-header-title">AI Stock Advisor</h1>

        {user && (
          <div className="user-badge">
            {user.nickname || user.email}
          </div>
        )}
      </header>

      {/* ========================== */}
      {/* 🍔 Drawer Menu */}
      {/* ========================== */}
      {menuOpen && (
        <div className="app-drawer">
          <nav>
            <Link to="/" onClick={() => setMenuOpen(false)}>🏠 首頁</Link>
            <Link to="/portfolio" onClick={() => setMenuOpen(false)}>📊 我的持股</Link>
            <Link to="/news" onClick={() => setMenuOpen(false)}>📰 新聞列表</Link>
            <Link to="/report" onClick={() => setMenuOpen(false)}>📈 今日報告</Link>

            {!user ? (
              <>
                <Link to="/login" onClick={() => setMenuOpen(false)}>🔐 登入</Link>
                <Link to="/register" onClick={() => setMenuOpen(false)}>📝 註冊</Link>
              </>
            ) : (
              <p
                onClick={() => {
                  logout();
                  setMenuOpen(false);
                }}
                style={{ cursor: "pointer", padding: "8px 0", color: "red" }}
              >
                🚪 登出
              </p>
            )}
          </nav>
        </div>
      )}

      {/* ========================== */}
      {/* 📄 Main Content */}
      {/* ========================== */}
      <main
        className="app-content"
        onClick={() => menuOpen && setMenuOpen(false)}
      >
        <Routes>
          {/* ===== 公開頁面 ===== */}
          <Route
            path="/login"
            element={user ? <Navigate to="/" replace /> : <LoginPage setUser={setUser} />}
          />
          <Route
            path="/register"
            element={user ? <Navigate to="/" replace /> : <RegisterPage />}
          />

          {/* ===== 需要登入 ===== */}
          <Route
            path="/"
            element={
              <RequireAuth user={user}>
                <HomePage />
              </RequireAuth>
            }
          />

          <Route
            path="/portfolio"
            element={
              <RequireAuth user={user}>
                <PortfolioPage />
              </RequireAuth>
            }
          />

          <Route
            path="/portfolio/add"
            element={
              <RequireAuth user={user}>
                <AddHoldingPage />
              </RequireAuth>
            }
          />
          <Route
            path="/portfolio/edit/:symbol"
            element={
              <RequireAuth user={user}>
                <EditHoldingPage />
              </RequireAuth>
            }
          />
          <Route
            path="/news"
            element={
              <RequireAuth user={user}>
                <NewsPage />
              </RequireAuth>
            }
          />

          <Route
            path="/report"
            element={
              <RequireAuth user={user}>
                <ReportPage />
              </RequireAuth>
            }
          />

          <Route
            path="/profile"
            element={
              <RequireAuth user={user}>
                <ProfilePage />
              </RequireAuth>
            }
          />

         

        </Routes>
      </main>

      {/* ========================== */}
      {/* 📱 Bottom TabBar */}
      {/* ========================== */}
      <div className="app-tabbar">
        <div className="app-tabbar-inner">
          <Link
            to="/"
            className={`app-tab ${isTabActive("/") ? "app-tab-active" : ""}`}
          >
            <FiHome size={18} />
            <span>首頁</span>
          </Link>

          <Link
            to="/portfolio"
            className={`app-tab ${isTabActive("/portfolio") ? "app-tab-active" : ""}`}
          >
            <FiPieChart size={18} />
            <span>持股</span>
          </Link>

          <Link
            to="/report"
            className={`app-tab ${isTabActive("/report") ? "app-tab-active" : ""}`}
          >
            <FiFileText size={18} />
            <span>報告</span>
          </Link>

          {!user ? (
            <Link
              to="/login"
              className={`app-tab ${isTabActive("/login") ? "app-tab-active" : ""}`}
            >
              <FiUser size={18} />
              <span>登入</span>
            </Link>
          ) : (
            <Link
              to="/profile"
              className={`app-tab ${isTabActive("/profile") ? "app-tab-active" : ""}`}
            >
              <FiUser size={18} />
              <span>個人</span>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
