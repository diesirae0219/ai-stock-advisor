import { useState } from "react"
import { api } from "../services/api"
import { useNavigate } from "react-router-dom"

interface LoginPageProps {
  setUser: (user: any) => void
}

export function LoginPage({ setUser }: LoginPageProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const navigate = useNavigate()

  const handleLogin = async () => {
    if (!email || !password) {
      setError("請輸入 email 與密碼")
      return
    }

    try {
      setError("")

      const res = await api.post("/auth/login", {
        email,
        password,
      })

      const { access_token, user } = res.data

      // ⭐ 儲存 token
      localStorage.setItem("token", access_token)

      // ⭐ 設定 axios 預設授權 header
      api.defaults.headers.common["Authorization"] = `Bearer ${access_token}`

      // ⭐ 更新 App 的 user 狀態
      setUser(user)

      navigate("/") // 回首頁
    } catch (err: any) {
      setError(err.response?.data?.detail || "登入失敗，請確認帳號密碼")
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={{ textAlign: "center", marginBottom: 10 }}>登入</h2>

      <input
        style={styles.input}
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <input
        style={styles.input}
        type="password"
        placeholder="密碼"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      {error && <p style={{ color: "red", margin: 0 }}>{error}</p>}

      <button style={styles.button} onClick={handleLogin}>
        登入
      </button>

      <p
        style={styles.link}
        onClick={() => navigate("/register")}
      >
        還沒有帳號？前往註冊
      </p>
    </div>
  )
}

const styles: { [key: string]: React.CSSProperties } = {
  container: {
    maxWidth: 350,
    margin: "40px auto",
    padding: 20,
    display: "flex",
    flexDirection: "column",
    gap: 12,
    background: "#ffffff",
    borderRadius: 8,
    boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
  },
  input: {
    padding: "10px 12px",
    fontSize: 16,
    border: "1px solid #ccc",
    borderRadius: 6,
  },
  button: {
    padding: "10px 12px",
    fontSize: 16,
    borderRadius: 6,
    backgroundColor: "#0d6efd",
    color: "white",
    cursor: "pointer",
    border: "none",
  },
  link: {
    color: "#0d6efd",
    cursor: "pointer",
    textAlign: "center",
    marginTop: 10,
  },
}
