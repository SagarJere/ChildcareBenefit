const ACCESS_TOKEN_KEY = 'childcare.accessToken'

/**
 * localStorage is per-browser only (see artifact/runtime storage notes) —
 * this is just a convenience so a page refresh doesn't log the employee
 * out. It is wrapped in try/catch because storage access can throw (private
 * browsing, blocked site data, etc.).
 */
export function getStoredToken(): string | null {
  try {
    return window.localStorage.getItem(ACCESS_TOKEN_KEY)
  } catch {
    return null
  }
}

export function setStoredToken(token: string): void {
  try {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, token)
  } catch {
    // Ignore: the session simply won't survive a page refresh.
  }
}

export function clearStoredToken(): void {
  try {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY)
  } catch {
    // Ignore.
  }
}
