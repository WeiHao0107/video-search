import os

# 路徑設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "milvus_demo.db")

# PostgreSQL 設定
POSTGRES_URL = "postgresql://user:password@localhost:5432/videodb"

# Milvus 設定
COLLECTION_NAME = "video_subtitles"
DIMENSION = 384  # all-MiniLM-L6-v2 的維度

# 模型設定
# 使用多語言模型 (支援中英文)
MODEL_NAME_REMOTE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_NAME = os.path.join(BASE_DIR, "models", "paraphrase-multilingual-MiniLM-L12-v2")
