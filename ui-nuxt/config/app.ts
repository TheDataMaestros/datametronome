const normalizeBase = (base: string): string => {
  if (!base.endsWith('/')) {
    return base
  }
  return base.replace(/\/+$/, '')
}

const defaultApiBase = 'http://127.0.0.1:8001/api/v1'

const getRuntimeApiBase = (): string | null => {
  // When running in the browser, Nuxt exposes runtime config on `window.__NUXT__`.
  // This is more reliable than relying on inlined `process.env` values, especially
  // when the dev server is started with different env vars.
  try {
    const nuxt = (globalThis as any).__NUXT__
    const apiBase = nuxt?.config?.public?.apiBase
    return typeof apiBase === 'string' && apiBase.length > 0 ? apiBase : null
  } catch {
    return null
  }
}

export const getApiBase = (): string => {
  // NOTE: This module is imported outside Nuxt setup, so it must NOT call Nuxt composables.
  // Prefer the runtime config when available (browser), otherwise fall back to env/default.
  return normalizeBase(getRuntimeApiBase() ?? process.env.NUXT_PUBLIC_API_BASE ?? defaultApiBase)
}

export const config = {
  get apiBase() {
    return getApiBase()
  },
}

export const buildApiUrl = (path: string): string => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${getApiBase()}${normalizedPath}`
}
