// lib/auth.ts

export const getToken = (): string | null => {
  if (typeof window === "undefined") return null
  return localStorage.getItem("access_token")
}

export const setToken = (token: string) => {
  localStorage.setItem("access_token", token)
}

export const removeToken = () => {
  localStorage.removeItem("access_token")
}

export const isAuthenticated = (): boolean => {
  return !!getToken()
}