const normalizeBase = (base: string): string => {
  if (!base.endsWith('/')) {
    return base
  }
  return base.replace(/\/+$/, '')
}

const defaultApiBase = 'http://127.0.0.1:8001/api/v1'

export const getApiBase = (): string => {
  // NOTE: This module is imported outside Nuxt setup, so it must NOT call Nuxt composables.
  // We only use process.env here (Nuxt will inline env values at build time for client).
  return normalizeBase(process.env.NUXT_PUBLIC_API_BASE ?? defaultApiBase)
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
