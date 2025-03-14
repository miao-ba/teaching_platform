# 教學語音處理與摘要管理平台

本專案是一個基於 Django 的教學語音處理與摘要管理平台，提供音訊轉錄、講者辨識、摘要生成和教學資源生成功能。

## 功能

- 高效處理課堂錄音（轉錄、識別講者）
- 使用 LangChain 與 Gemini API 生成摘要和教學資源
- 實現簡單的 RAG 系統輔助內容生成
- 提供美觀、直覺的使用者介面
- 支援免費/低成本替代方案
- 預留付費服務接口設計

## 安裝與設定

1. 複製專案

```bash
   git clone https://github.com/yourusername/teaching_platform.git
   cd teaching_platform
```

建立虛擬環境並安裝依賴

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

配置環境變數

```cp .env.example .env
# 編輯 .env 檔案設定必要的環境變數
```

執行資料庫遷移

```bash
python manage.py migrate
```

啟動開發伺服器

```bash
bashCopypython manage.py runserver
```

授權
MIT License
