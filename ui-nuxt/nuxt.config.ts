export default defineNuxtConfig({
  devtools: { enabled: false },
  compatibilityDate: '2025-10-16',
  // Every page here sits behind a login and reads a token from localStorage,
  // which the server cannot see. Server rendering therefore produced a
  // logged-out, empty version of each page first: placeholder identity, zero
  // counts, "No data sources found", followed by hydration mismatches when the
  // client corrected it. Rendering purely on the client removes that whole
  // class of flicker and mismatch. There is nothing public to pre-render.
  ssr: false,
  modules: ['@nuxt/ui', '@nuxtjs/color-mode', '@pinia/nuxt', '@vueuse/nuxt'],
  css: ['~/assets/css/main.css'],
  colorMode: {
    preference: 'dark',
    fallback: 'dark',
    hid: 'nuxt-color-mode-script',
    globalName: '__NUXT_COLOR_MODE__',
    componentName: 'ColorScheme',
    classPrefix: '',
    classSuffix: '',
    storageKey: 'nuxt-color-mode',
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || 'http://127.0.0.1:8001/api/v1',
      podiumApiBase: process.env.NUXT_PUBLIC_PODIUM_API_BASE || 'http://127.0.0.1:8001',
    },
  },
  app: {
    head: {
      title: 'DataMetronome - Data Quality & Anomaly Detection',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Real-time Data Quality & Anomaly Detection Platform' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,200..800&family=Manrope:wght@300..800&family=JetBrains+Mono:wght@400;500&display=swap',
        },
      ],
    },
  },
})
