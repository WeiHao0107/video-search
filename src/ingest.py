import os
import glob
import whisper
from pymilvus import MilvusClient, DataType
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import config
from database import init_db, get_session, SourceFile, Content

def init_milvus():
    """初始化 Milvus Client 並建立極簡化 Collection"""
    client = MilvusClient(config.DB_PATH)
    
    # 檢查是否需要重建 Collection (因為 Schema 改變了)
    if client.has_collection(config.COLLECTION_NAME):
        # 為了開發方便，每次重建
        # print(f"Dropping existing collection {config.COLLECTION_NAME}...")
        # client.drop_collection(config.COLLECTION_NAME)
        pass # 保留舊資料，如果 schema 不相容再手動刪

    if not client.has_collection(config.COLLECTION_NAME):
        print(f"Creating collection {config.COLLECTION_NAME} (ID + Vector only)...")
        schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
        
        # 1. ID: 使用 VARCHAR 存儲 UUID
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=64, is_primary=True)
        
        # 2. Vector
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=config.DIMENSION)
        
        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", metric_type="COSINE", index_type="FLAT")
        
        client.create_collection(
            collection_name=config.COLLECTION_NAME,
            schema=schema,
            index_params=index_params
        )
    return client

def transcribe_video(model, file_path):
    """使用 Whisper 進行語音轉文字"""
    print(f"Transcribing {os.path.basename(file_path)} with Whisper (this may take a while)...")
    
    # Whisper 支援自動語言偵測，也可以強制指定 language='en'
    result = model.transcribe(file_path)
    return result['segments']

def process_video_file(session, whisper_model, file_path):
    """處理影片檔案：轉錄 -> Postgres -> 回傳 (id, vector_text) 給 Milvus"""
    filename = os.path.basename(file_path)
    
    # 1. 執行轉錄
    try:
        segments = transcribe_video(whisper_model, file_path)
    except Exception as e:
        print(f"Failed to transcribe {filename}: {e}")
        return []

    print(f"Got {len(segments)} segments from {filename}")

    # 2. 建立 SourceFile Metadata
    source_file = SourceFile(
        filename=filename, 
        file_type="video/mp4", # 簡化假設，實際可偵測副檔名
        file_path=os.path.abspath(file_path), # 儲存絕對路徑或相對路徑
        author="unknown",
        metadata_info={"segment_count": len(segments)}
    )
    session.add(source_file)
    session.flush()

    data_for_milvus = []
    
    for i, seg in enumerate(segments):
        start_seconds = seg['start']
        end_seconds = seg['end']
        text = seg['text'].strip()
        
        if not text:
            continue
        
        # 3. 建立 Content
        content_entry = Content(
            source_file_id=source_file.id,
            type="subtitle",
            content=text,
            custom={
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "original_index": i
            }
        )
        session.add(content_entry)
        session.flush()

        # 準備寫入 Milvus 的資料
        data_for_milvus.append({
            "id": str(content_entry.id),
            "text_for_embedding": text
        })
    
    session.commit()
    return data_for_milvus

def main():
    # 初始化 Postgres
    print("Initializing PostgreSQL...")
    try:
        init_db()
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return

    # 初始化 Embedding 模型
    print("Loading embedding model (SentenceTransformer)...")
    embed_model = SentenceTransformer(config.MODEL_NAME)
    
    # 初始化 Whisper 模型
    print("Loading Whisper model (base)...")
    whisper_model = whisper.load_model("base")

    # 初始化 Milvus
    client = init_milvus()
    
    # 掃描所有支援的影片格式
    video_extensions = ['*.mp4', '*.mkv', '*.mov', '*.webm']
    video_files = []
    for ext in video_extensions:
        video_files.extend(glob.glob(os.path.join(config.DATA_DIR, ext)))
    
    if not video_files:
        print(f"No video files found in {config.DATA_DIR}")
        print("Please place some .mp4 files in the data/ directory.")
        return

    session = get_session()
    all_milvus_tasks = []

    try:
        for f in video_files:
            # 檢查是否已經處理過 (簡單檢查: 用檔名查 DB)
            # 這裡為了演示方便，暫時省略，每次都重新轉錄可能會導致重複資料
            # 建議生產環境要加檢查邏輯
            
            file_tasks = process_video_file(session, whisper_model, f)
            all_milvus_tasks.extend(file_tasks)
    except Exception as e:
        print(f"Error processing files: {e}")
        session.rollback()
        return
    finally:
        session.close()

    if not all_milvus_tasks:
        print("No valid subtitles generated.")
        return

    # 批次向量化與寫入 Milvus
    batch_size = 100
    print(f"Ingesting {len(all_milvus_tasks)} items into Milvus...")
    
    for i in tqdm(range(0, len(all_milvus_tasks), batch_size)):
        batch_items = all_milvus_tasks[i : i + batch_size]
        texts = [item["text_for_embedding"] for item in batch_items]
        ids = [item["id"] for item in batch_items]
        
        # 產生向量
        embeddings = embed_model.encode(texts)
        
        # 組合寫入資料
        insert_data = []
        for j, vector in enumerate(embeddings):
            insert_data.append({
                "id": ids[j],
                "vector": vector.tolist()
            })
            
        client.insert(collection_name=config.COLLECTION_NAME, data=insert_data)
        
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
