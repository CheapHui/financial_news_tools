# 信號聚合系統使用指南

本指南介紹如何使用 `rollup_signals.py` 命令和相關的 API 及前端功能。

## 系統架構

```
新聞數據 → 嵌入向量 → 研究匹配 → 信號聚合 → API 輸出 → 前端顯示
```

## 1. Makefile 命令

### 基本命令

```bash
# 標準信號聚合 (最近7天新聞，7天窗口)
make rollup-signals

# 快速測試 (最近3天新聞，3天窗口，較少匹配)
make rollup-signals-fast

# 完整聚合 (最近14天新聞，更多匹配，覆蓋現有數據)
make rollup-signals-full

# 完整新聞處理流水線
make news-pipeline
```

### 完整流水線說明

`news-pipeline` 命令會依序執行：
1. `news-full`: 攝取新聞 + 生成嵌入向量
2. `link-news`: 新聞實體連結
3. `rollup-signals`: 信號聚合

## 2. API 端點

### 2.1 信號匯總 API

```
GET /api/signals/summary/
```

**查詢參數：**
- `limit`: 每類排行榜數量 (默認 20，最大 100)
- `days_back`: 時間範圍天數 (默認 7，最大 30)

**返回數據結構：**
```json
{
  "summary": {
    "query_params": {...},
    "company_stats": {
      "total_signals": 150,
      "positive_signals": 85,
      "negative_signals": 65,
      "avg_score": 0.0234,
      "max_positive_score": 2.4567,
      "max_negative_score": -1.8901
    },
    "industry_stats": {...}
  },
  "rankings": {
    "top_positive_companies": [...],
    "top_negative_companies": [...],
    "top_positive_industries": [...],
    "top_negative_industries": [...]
  }
}
```

### 2.2 公司信號 API

```
GET /api/companies/{ticker}/signals/
```

**查詢參數：**
- `max_details`: 限制詳細信息條數 (默認 100)

### 2.3 行業信號 API

```
GET /api/industries/{id}/signals/
```

**查詢參數：**
- `max_details`: 限制詳細信息條數 (默認 100)

## 3. 前端界面

### 3.1 信號匯總儀表板

訪問前端並選擇 "📈 信號匯總" 標籤頁，功能包括：

- **統計概覽**: 總信號數、正負面信號分佈
- **排行榜**: 最強勢/弱勢公司和行業
- **詳細統計**: 分數分佈和趨勢分析
- **交互功能**: 點擊項目查看詳情

### 3.2 使用步驟

1. 啟動後端服務：`make up`
2. 啟動前端服務：`make start-frontend`
3. 訪問 http://localhost:3000
4. 選擇 "📈 信號匯總" 標籤頁
5. 調整查詢參數（排行榜數量、時間範圍）
6. 點擊 "刷新數據" 獲取最新結果

## 4. 信號計算說明

### 4.1 信號來源

信號基於以下研究物件類型：

**公司層級：**
- `company_profile`: 公司概況 (權重: +0.2)
- `company_risk`: 公司風險 (權重: -1.0)
- `company_catalyst`: 公司催化劑 (權重: ±1.0，依據正負面)
- `company_thesis`: 公司論點 (權重: ±0.5，依據 for/against)

**行業層級：**
- `industry_profile`: 行業概況 (權重: +0.1)
- `industry_player`: 行業參與者 (權重: +0.2)

### 4.2 計算公式

```
信號貢獻 = 相似度 × 極性權重 × 時間衰減

時間衰減 = 0.5 ^ (天數差 / 半衰期)
```

**半衰期設定：**
- 公司概況: 90天
- 公司風險: 60天
- 公司催化劑: 20天
- 公司論點: 45天
- 行業概況: 60天
- 行業參與者: 45天

### 4.3 行業到公司分配

行業信號可通過以下方式分配到公司：

- **weight**: 按市值權重分配 (默認)
- **equal**: 平均分配
- **off**: 不分配

## 5. 故障排除

### 5.1 常見問題

**Q: 沒有信號數據顯示？**
A: 確保已運行完整流水線：`make news-pipeline`

**Q: 信號分數都是 0？**
A: 檢查是否有研究數據和嵌入向量：
```bash
make emb-research
make ai-company
make ai-industry
```

**Q: API 返回 404？**
A: 確保 Django 服務運行且 URL 配置正確

### 5.2 調試命令

```bash
# 檢查數據狀態
make check-data

# 查看數據庫中的信號
make psql
SELECT COUNT(*) FROM research_analyticscompanysignal;
SELECT COUNT(*) FROM analytics_analyticsindustrysignal;

# 查看最新信號
SELECT company_id, score, window_end 
FROM research_analyticscompanysignal 
ORDER BY window_end DESC LIMIT 10;
```

## 6. 自定義配置

### 6.1 修改信號參數

編輯 `rollup_signals.py` 中的配置：

```python
# 極性權重
POLARITY_DEFAULT = {
    "company_profile": +0.2,
    "company_risk": -1.0,
    # ...
}

# 半衰期（天）
HALF_LIFE = {
    "company_profile": 90,
    "company_risk": 60,
    # ...
}
```

### 6.2 添加新的信號類型

1. 在 `ALL_TYPES` 中添加新類型
2. 更新 `POLARITY_DEFAULT` 和 `HALF_LIFE`
3. 在 `resolve_company_signal` 或 `resolve_industry_signal` 中添加處理邏輯

## 7. 監控和維護

### 7.1 定期任務

建議設置 cron 任務定期更新信號：

```bash
# 每天凌晨2點更新信號
0 2 * * * cd /path/to/project && make rollup-signals
```

### 7.2 性能監控

```bash
# 查看 API 性能
curl -s http://localhost:8000/api/metrics/summary | jq .

# 監控信號生成時間
time make rollup-signals
```

## 8. 擴展功能

### 8.1 添加新的排行榜

可以在 API 中添加更多排行榜類型：
- 按行業分組的公司排行
- 按時間段的趨勢分析
- 自定義分數計算方式

### 8.2 實時更新

考慮使用 WebSocket 或 Server-Sent Events 實現實時信號更新。
