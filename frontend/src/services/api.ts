import axios from "axios"

export const api = axios.create({
  baseURL: "https://ai-stock-advisor-1dj7.onrender.com",
})

// ⭐ 每次發送 request 前，自動加入 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)
