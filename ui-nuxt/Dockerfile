FROM node:20-alpine AS build

WORKDIR /app

COPY ui-nuxt/package.json ui-nuxt/package-lock.json ./
RUN npm ci

COPY ui-nuxt/ ./

RUN npm run build


FROM node:20-alpine AS run

WORKDIR /app

ENV NODE_ENV=production
ENV NITRO_HOST=0.0.0.0
ENV NITRO_PORT=3000

# These end up in Nuxt public runtimeConfig (client-side config)
ENV NUXT_PUBLIC_API_BASE=http://localhost:8001/api/v1
ENV NUXT_PUBLIC_PODIUM_API_BASE=http://localhost:8001

COPY --from=build /app/.output ./.output
COPY --from=build /app/package.json ./package.json

EXPOSE 3000

CMD ["node", ".output/server/index.mjs"]
