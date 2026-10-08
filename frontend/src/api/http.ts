import axios from 'axios'

const TOKEN_KEY = 'shuangrenjian_token'

export const http = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

type UnauthorizedHandler = () => void

let unauthorizedHandler: UnauthorizedHandler | null = null

export function setUnauthorizedHandler(handler: UnauthorizedHandler) {
  unauthorizedHandler = handler
}

function isLoginRequest(url: string | undefined): boolean {
  return (url ?? '').includes('/auth/login')
}

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !isLoginRequest(err.config?.url)) {
      unauthorizedHandler?.()
    }
    return Promise.reject(err)
  },
)
