import { useEffect, useState } from "react"
import { api } from "../services/api"
import { useNavigate } from "react-router-dom"

export function ProfilePage() {
  const navigate = useNavigate()

  const [user, setUser] = useState<any>(null)
  const [nickname, setNickname] = useState("")
  const [msg, setMsg] = useState("")

  const [oldPassword, setOldPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")

  useEffect(() => {
    api.get("/me")
      .then((res) => {
        setUser(res.data)
        setNickname(res.data.nickname || "")
      })
      .catch(() => {
        navigate("/login")
      })
  }, [])

  const saveProfile = async () => {
    try {
      setMsg("")
      await api.put("/users/update-profile", { nickname })
      setMsg("暱稱已成功更新")
    } catch (err: any) {
      setMsg(err.response?.data?.detail || "更新失敗")
    }
  }

  const changePassword = async () => {
    try {
      setMsg("")
      await api.put("/users/update-password", {
        old_password: oldPassword,
        new_password: newPassword,
      })
      setMsg("密碼變更成功")
    } catch (err: any) {
      setMsg(err.response?.data?.detail || "更新失敗")
    }
  }

  const logout = () => {
    localStorage.removeItem("token")
    navigate("/login")
  }

  if (!user) return <p>載入中...</p>

  return (
    <div style={{ maxWidth: 400, margin: "30px auto" }}>
      <h2>個人資料</h2>

      <p><b>Email：</b>{user.email}</p>
      <p><b>註冊日期：</b>{user.created_at}</p>

      <hr />

      <h3>修改暱稱</h3>
      <input
        style={styles.input}
        value={nickname}
        onChange={(e) => setNickname(e.target.value)}
      />
      <button style={styles.button} onClick={saveProfile}>儲存</button>

      <hr />

      <h3>修改密碼</h3>
      <input
        type="password"
        style={styles.input}
        placeholder="舊密碼"
        value={oldPassword}
        onChange={(e) => setOldPassword(e.target.value)}
      />
      <input
        type="password"
        style={styles.input}
        placeholder="新密碼"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
      />
      <button style={styles.button} onClick={changePassword}>修改密碼</button>

      {msg && <p style={{ marginTop: 10 }}>{msg}</p>}

      <hr />
      <button style={styles.logout} onClick={logout}>登出</button>
    </div>
  )
}

const styles = {
  input: {
    width: "100%",
    padding: "10px",
    margin: "6px 0",
    fontSize: 16,
  },
  button: {
    padding: "10px 12px",
    width: "100%",
    background: "#0d6efd",
    color: "white",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  },
  logout: {
    padding: "10px 12px",
    width: "100%",
    background: "#dc3545",
    color: "white",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  }
}
