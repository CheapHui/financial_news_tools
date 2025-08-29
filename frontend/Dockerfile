# --- build stage ---
    FROM node:20-alpine AS build
    WORKDIR /app
    COPY package*.json ./
    RUN npm ci
    COPY . .
    RUN npm run build
    
    # --- runtime stage ---
    FROM nginx:alpine
    # 自定義 nginx 設定（含 /api 反代到 Django）
    COPY nginx.conf /etc/nginx/conf.d/default.conf
    # 把 Vite build 出來的靜態檔案放去 Nginx 預設目錄
    COPY --from=build /app/dist /usr/share/nginx/html
    EXPOSE 80
    CMD ["nginx", "-g", "daemon off;"]