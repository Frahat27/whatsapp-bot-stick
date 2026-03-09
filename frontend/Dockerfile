FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Build-time env — backend URL on Railway
ENV NEXT_PUBLIC_API_URL=https://whatsapp-bot-stick-production.up.railway.app

RUN npm run build

# Production
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

ENV PORT=3000
EXPOSE ${PORT}

CMD ["node", "server.js"]
