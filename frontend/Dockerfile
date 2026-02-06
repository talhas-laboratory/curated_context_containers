FROM node:20-alpine AS base
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

FROM base AS deps
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json ./
RUN npm ci

FROM base AS builder
RUN apk add --no-cache libc6-compat
ARG NEXT_PUBLIC_MCP_BASE_URL=/api
ARG NEXT_PUBLIC_MCP_TOKEN=
ARG NEXT_PUBLIC_BUILD_SHA=
ARG NEXT_PUBLIC_BUILD_TIME=
ENV NEXT_PUBLIC_MCP_BASE_URL=${NEXT_PUBLIC_MCP_BASE_URL}
ENV NEXT_PUBLIC_MCP_TOKEN=${NEXT_PUBLIC_MCP_TOKEN}
ENV NEXT_PUBLIC_BUILD_SHA=${NEXT_PUBLIC_BUILD_SHA}
ENV NEXT_PUBLIC_BUILD_TIME=${NEXT_PUBLIC_BUILD_TIME}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM base AS runner
ENV NODE_ENV=production
ENV PORT=3000
ARG NEXT_PUBLIC_BUILD_SHA=
ARG NEXT_PUBLIC_BUILD_TIME=
ENV NEXT_PUBLIC_BUILD_SHA=${NEXT_PUBLIC_BUILD_SHA}
ENV NEXT_PUBLIC_BUILD_TIME=${NEXT_PUBLIC_BUILD_TIME}
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.js ./next.config.js
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
USER nextjs
EXPOSE 3000
CMD ["npm", "run", "start"]
