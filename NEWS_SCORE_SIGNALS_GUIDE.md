# 新聞分數信號系統使用指南

本指南介紹如何使用更新後的新聞分數信號功能，這是對原有研究匹配信號的補充。

## 系統架構

```
新聞數據 → 新聞分數計算 → 信號聚合 → API 輸出 → 前端顯示
```

新聞分數信號基於以下計算公式：
```
信號分數 = 影響力分數 × 可信度分數 × 新穎性分數 × 時間衰減 × 情感分數
```

## 1. Makefile 命令

### 新聞分數相關命令

```bash
# 計算新聞分數 (最近24小時新聞)
make news-score

# 聚合新聞分數為信號 (回看168小時)
make rollup-news-score-signals

# 完整新聞分數流水線 (計算分數 → 聚合信號)
make news-score-pipeline
```

### 研究匹配相關命令 (原有功能)

```bash
# 標準研究匹配信號聚合
make rollup-signals

# 完整研究匹配流水線 (攝取 → 嵌入 → 連結 → 聚合)
make news-research-pipeline
```

## 2. API 端點

### 2.1 新聞分數信號匯總 API

```
GET /api/signals/news-score-summary/
```

**查詢參數：**
- `limit`: 每類排行榜數量 (默認 20，最大 100)
- `lookback_hours`: 回看時間小時數 (默認 168，最大 720)

**返回數據結構：**
```json
{
  "summary": {
    "query_params": {...},
    "company_stats": {
      "total_signals": 50,
      "positive_signals": 30,
      "negative_signals": 20,
      "avg_window_score": 0.123456,
      "max_positive_score": 2.456789,
      "max_negative_score": -1.234567,
      "avg_news_count": 5.2
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

### 2.2 公司新聞分數信號 API

```
GET /api/companies/{ticker}/news-score-signal/
```

**返回數據包括：**
- 窗口分數和新聞數量
- 平均每條新聞分數
- 相關新聞詳情（包含分數組成）
- 研究匹配信號（如果有）

### 2.3 原有研究匹配信號 API

```
GET /api/signals/summary/
GET /api/companies/{ticker}/signals/
GET /api/industries/{id}/signals/
```

## 3. 前端界面

### 3.1 新聞分數信號儀表板

訪問前端並選擇 "📰 新聞分數信號" 標籤頁，功能包括：

- **統計概覽**: 基於新聞分數的信號統計
- **排行榜**: 最佳/最差新聞表現的公司和行業
- **詳細信息**: 每條新聞的分數組成
- **時間控制**: 可調整回看時間範圍

### 3.2 研究匹配信號儀表板

選擇 "📈 研究匹配信號" 標籤頁查看原有功能：

- 基於新聞與研究報告相似度的信號
- 時間衰減和極性分析
- 行業到公司的分配策略

## 4. 新聞分數計算說明

### 4.1 分數組成

新聞分數由以下幾個維度計算：

1. **影響力分數 (Impact Score)**: 新聞的潛在市場影響
2. **可信度分數 (Credibility Score)**: 新聞來源的可信度
3. **新穎性分數 (Novelty Score)**: 新聞內容的新穎程度
4. **時間衰減 (Decayed Weight)**: 基於時間的權重衰減
5. **情感分數 (Sentiment)**: 新聞的情感傾向

### 4.2 目標分配

新聞分數會根據以下邏輯分配到實體：

1. **精準匹配**: 根據 `targets` 字段中的公司符號或行業名稱
2. **回退機制**: 當無精準匹配時，使用整體情感分數分配到已連結實體
3. **聚合計算**: 多條新聞的分數會累加到窗口分數中

### 4.3 與研究匹配信號的區別

| 特性 | 新聞分數信號 | 研究匹配信號 |
|------|-------------|--------------|
| 數據源 | 新聞內容分數 | 新聞與研究報告相似度 |
| 計算方式 | 影響力×可信度×新穎性×衰減×情感 | 相似度×極性×時間衰減 |
| 時間範圍 | 基於小時的回看窗口 | 基於天數的時間窗口 |
| 更新頻率 | 可實時更新 | 需要研究報告匹配 |
| 適用場景 | 快速市場反應 | 深度研究分析 |

## 5. 使用場景

### 5.1 新聞分數信號適用於：

- **快速市場監控**: 實時追蹤新聞對公司的影響
- **情感分析**: 了解市場對公司的整體情感
- **新聞質量評估**: 基於可信度和影響力篩選重要新聞
- **短期交易決策**: 基於最新新聞趨勢的快速決策

### 5.2 研究匹配信號適用於：

- **深度分析**: 基於研究報告的長期投資分析
- **主題匹配**: 新聞與特定研究主題的關聯分析
- **風險評估**: 基於風險報告的預警系統
- **投資研究**: 結合研究報告的投資決策支持

## 6. 數據流程

### 6.1 新聞分數流程

```
1. 新聞攝取 → NewsItem
2. 分數計算 → news_scores_json
3. 實體匹配 → targets 分配
4. 信號聚合 → AnalyticsCompanySignal.window_score
5. API 輸出 → 前端顯示
```

### 6.2 研究匹配流程

```
1. 新聞攝取 → NewsItem
2. 嵌入生成 → NewsChunk embeddings
3. 研究匹配 → 相似度計算
4. 信號聚合 → AnalyticsCompanySignal.score
5. API 輸出 → 前端顯示
```

## 7. 故障排除

### 7.1 常見問題

**Q: 新聞分數信號沒有數據？**
A: 確保已運行新聞分數計算：`make news-score`

**Q: 分數計算失敗？**
A: 檢查新聞是否有 `news_scores_json` 字段，確保模型配置正確

**Q: 信號聚合沒有結果？**
A: 確保新聞有目標實體匹配，檢查 `targets` 字段

### 7.2 調試命令

```bash
# 檢查新聞分數數據
make psql
SELECT COUNT(*) FROM news_newsitem WHERE news_scores_json IS NOT NULL;

# 檢查信號聚合結果
SELECT COUNT(*) FROM research_analyticscompanysignal WHERE window_count > 0;

# 查看最新新聞分數信號
SELECT company_id, window_score, window_count, last_aggregated_at 
FROM research_analyticscompanysignal 
WHERE window_count > 0 
ORDER BY last_aggregated_at DESC LIMIT 10;
```

## 8. 配置選項

### 8.1 新聞分數參數

在 `score_news` 命令中可配置：
- `--since-hours`: 處理最近N小時的新聞
- `--model`: 使用的AI模型
- `--half-life`: 時間衰減半衰期

### 8.2 信號聚合參數

在 `rollup_signals` 命令中可配置：
- `--lookback-hours`: 回看時間窗口
- `--min-decayed-weight`: 最小衰減權重閾值
- `--apply-overall-when-missing`: 當無精準匹配時使用整體情感

## 9. 性能優化

### 9.1 數據庫索引

已自動創建以下索引：
- `news_scores_json` 的 GIN 索引
- `last_aggregated_at` 的 B-tree 索引
- `window_score` 的查詢索引

### 9.2 API 優化

- 使用 `select_related` 減少數據庫查詢
- 限制返回數據量避免大 payload
- 支持分頁和時間範圍過濾

## 10. 監控和維護

### 10.1 定期任務

建議設置定期任務：

```bash
# 每小時更新新聞分數
0 * * * * cd /path/to/project && make news-score

# 每4小時聚合信號
0 */4 * * * cd /path/to/project && make rollup-news-score-signals
```

### 10.2 監控指標

- 新聞分數計算成功率
- 信號聚合數據量
- API 響應時間
- 前端刷新頻率

## 11. 未來擴展

### 11.1 可能的增強功能

- 實時 WebSocket 推送
- 自定義分數權重配置
- 多語言新聞支持
- 歷史趨勢分析
- 預警系統集成

### 11.2 集成建議

- 與交易系統集成
- 風險管理系統對接
- 投資組合管理工具整合
- 第三方數據源擴展
