const normalizeBase = (base: string): string => {
  if (!base.endsWith('/')) {
    return base
  }
  return base.replace(/\/+$/, '')
}

const defaultApiBase = 'http://localhost:8001/api/v1'

export const config = {
  apiBase: normalizeBase(process.env.NUXT_PUBLIC_API_BASE ?? defaultApiBase)
}

export const buildApiUrl = (path: string): string => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${config.apiBase}${normalizedPath}`
}
