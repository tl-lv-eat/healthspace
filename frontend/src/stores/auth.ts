import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { http } from '@/api/http'

const TOKEN_KEY = 'shuangrenjian_token'
const USER_KEY = 'shuangrenjian_user'

export interface AuthUser {
  id: string
  display_name: string
  default_water_ml: number
  role: string
  sex: string | null
  age: number | null
}

export interface ProfileUpdate {
  display_name: string
  sex?: string | null
  age?: number | null
}

interface TokenResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

function loadToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

function loadUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(loadToken())
  const user = ref<AuthUser | null>(loadUser())

  const isAuthenticated = computed(() => Boolean(token.value))

  function persist() {
    if (token.value) {
      localStorage.setItem(TOKEN_KEY, token.value)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }
    if (user.value) {
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    } else {
      localStorage.removeItem(USER_KEY)
    }
  }

  function clearSession() {
    token.value = null
    user.value = null
    persist()
  }

  async function login(userId: string, password: string) {
    const { data } = await http.post<TokenResponse>('/auth/login', {
      user_id: userId,
      password,
    })
    token.value = data.access_token
    user.value = data.user
    persist()
  }

  /** Private couple app: pick persona without password. */
  async function select(userId: string) {
    const { data } = await http.post<TokenResponse>('/auth/select', {
      user_id: userId,
    })
    token.value = data.access_token
    user.value = data.user
    persist()
  }

  async function updateProfile(payload: ProfileUpdate) {
    const { data } = await http.patch<AuthUser>('/auth/me', payload)
    user.value = data
    persist()
    return data
  }

  return {
    token,
    user,
    isAuthenticated,
    login,
    select,
    updateProfile,
    clearSession,
  }
})
