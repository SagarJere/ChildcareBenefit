import axios from 'axios'

import { notifyUnauthorized } from './authEvents'
import { clearStoredToken, getStoredToken } from './authStorage'

/**
 * Shared Axios instance for all backend calls. The base URL points at the
 * FastAPI `/api/v1` prefix; individual API modules append their own path.
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15_000,
})

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && !isLoginRequest) {
      clearStoredToken()
      notifyUnauthorized()
    }
    return Promise.reject(error)
  },
)
