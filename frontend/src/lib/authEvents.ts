/**
 * Lets the Axios response interceptor (outside the React tree) tell
 * AuthProvider that the current session is no longer valid — e.g. the
 * access token expired or the employee was deactivated — without doing a
 * full page redirect.
 */
let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

export function notifyUnauthorized(): void {
  onUnauthorized?.()
}
