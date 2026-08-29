FROM node:22-slim AS builder
WORKDIR /app

COPY package*.json ./
RUN npm install --no-audit --fetch-retries=5 --fetch-retry-factor=2

ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY . .
RUN npm run build

FROM nginx:alpine AS runner
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
