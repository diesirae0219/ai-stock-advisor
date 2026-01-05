import { useState } from "react"
import { api } from "../services/api"
import { useNavigate } from "react-router-dom"

export function RegisterPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [nickname, setNickname] = useState("")
  const [error, setError] = useState("")
  const navigate = useNavigate()

  const handleRegister = async () => {
    try {
      setError("")
      await api.post("/auth/register", {
        email,
        password,
        nickname,
      })

      alert("註冊成功，請登入")
      navigate("/login")
    } catch (err: any) {
      setError(err.response?.data?.detail || "註冊失敗")
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={{ textAlign: "center", marginBottom: 10 }}>註冊</h2>

      <input
        style={styles.input}
        placeholder="暱稱（選填）"
        value={nickname}
        onChange={(e) => setNickname(e.target.value)}
      />

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

      <button style={styles.button} onClick={handleRegister}>
        註冊
      </button>

      <p
        style={styles.link}
        onClick={() => navigate("/login")}
      >
        已有帳號？立即登入
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
    backgroundColor: "#198754",
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
