
# 新的數據管理命令使用說明

## 1. 檢查當前數據狀態
make check-data
# 或者直接使用 Django 命令
python manage.py seed_reference_data --check

## 2. 僅創建基本結構（推薦）
make create-structure
# 或者
python manage.py seed_reference_data --create-basic

## 3. 完全重置數據（慎用）
make reset-data
# 或者
python manage.py seed_reference_data --purge --create-basic

## 4. 只清空數據
python manage.py seed_reference_data --purge

## 主要改進：
- 不再有默認的公司數據
- 不會每次都重置數據庫
- 可以檢查當前狀態
- 只創建必要的板塊和行業結構
- 公司數據通過 research_pipeline.py 導入

