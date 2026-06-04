FROM node:20-alpine AS deps

WORKDIR /app/frontend

COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder

ENV NEXT_TELEMETRY_DISABLED=1 \
    NEXT_PUBLIC_API_BASE=/api/v1

WORKDIR /app/frontend

COPY --from=deps /app/frontend/node_modules ./node_modules
COPY . .

RUN npm run build

FROM node:20-alpine AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    NEXT_PUBLIC_API_BASE=/api/v1

WORKDIR /app/frontend

COPY --from=builder /app/frontend/public ./public
COPY --from=builder /app/frontend/.next/standalone ./
COPY --from=builder /app/frontend/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
