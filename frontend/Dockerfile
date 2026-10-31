# Сборка: node -> dist (статическая сборка), раздача через nginx с прокси /api.

FROM node:22-alpine AS builder
WORKDIR /app
ARG VITE_API_BASE_URL=/api
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
