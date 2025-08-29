# Trading Infrastructure MVP

一個現代化的金融信號分析平台，採用前後端分離架構。

## 🏗️ 項目結構

```
trading-infra-mvp/
├── backend/                 # Django 後端服務
│   ├── mytrading/          # Django 應用
│   ├── requirements.txt    # Python 依賴
│   └── Dockerfile         # 後端容器配置
├── frontend/              # React 前端應用
│   ├── src/              # 源代碼
│   │   ├── SignalsDashboard.jsx  # 主要儀表板組件
│   │   └── ...
│   ├── package.json      # Node.js 依賴
│   └── Dockerfile        # 前端容器配置
├── docker-compose.yml    # 生產環境配置
├── docker-compose.dev.yml # 開發環境配置
└── nginx.conf           # Nginx 反向代理配置
```

## 🚀 快速開始

### 開發環境

#### 方法 1：本地開發（推薦）

**後端服務（Docker）：**
```bash
# 啟動後端服務（數據庫、Redis、Django）
docker compose up -d db redis web
```

**前端服務（本地）：**
```bash
# 進入前端目錄
cd frontend

# 安裝依賴
npm install

# 啟動開發服務器
npm run dev
```

訪問：
- 前端：http://localhost:3000
- 後端 API：http://localhost:8000

#### 方法 2：完整 Docker 環境

```bash
# 啟動所有服務
docker compose -f docker-compose.dev.yml up -d

# 查看日誌
docker compose -f docker-compose.dev.yml logs -f
```

### 生產環境

```bash
# 構建並啟動所有服務
docker compose up -d --build

# 查看狀態
docker compose ps
```

## 🛠️ 技術棧

### 後端
- **Django** - Web 框架
- **PostgreSQL + pgvector** - 向量數據庫
- **Redis** - 緩存和消息隊列
- **MinIO** - 對象存儲
- **Qdrant** - 向量搜索引擎

### 前端
- **React** - UI 框架
- **Vite** - 構建工具
- **Tailwind CSS** - 樣式框架
- **Nginx** - 反向代理（生產環境）

## 📊 功能特性

- **信號分析儀表板** - 實時金融信號監控
- **新聞匹配系統** - 新聞與研究內容的語義匹配
- **公司信號追踪** - 個股信號分析
- **行業趨勢分析** - 行業層面的信號聚合
- **響應式設計** - 現代化的用戶界面

## 🔧 開發指南

### 前端開發
```bash
cd frontend
npm run dev        # 開發服務器
npm run build      # 構建生產版本
npm run lint       # 代碼檢查
```

### 後端開發
```bash
cd backend/mytrading
python manage.py runserver     # 開發服務器
python manage.py migrate       # 數據庫遷移
python manage.py test          # 運行測試
```

## 🌐 API 端點

- `GET /api/news/<id>/matches` - 獲取新聞匹配
- `GET /api/companies/<ticker>/signals` - 獲取公司信號
- `GET /api/industries/<id>/signals` - 獲取行業信號

## 📝 更新日誌

### v2.0.0 - 2025-08-29
- 🔄 重構為前後端分離架構
- 🎨 全新的 React + Tailwind CSS 前端
- 🐳 優化的 Docker 配置
- 📱 響應式設計改進
- 🚀 性能優化

## 📄 許可證

MIT License

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！
