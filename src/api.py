from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
import uvicorn
import config
from database import get_session, get_contents_by_ids

# 定義請求與回應模型
class SearchRequest(BaseModel):
    query: str

class SubtitleChild(BaseModel):
    text: str
    start_seconds: float
    end_seconds: float
    score: float
    custom: Optional[Dict[str, Any]] = None

class VideoSearchResult(BaseModel):
    video_id: str
    filename: str
    video_url: str  # 新增: 供前端播放的 URL
    author: Optional[str] = None
    created_at: str
    metadata_info: Optional[Dict[str, Any]] = None
    children: List[SubtitleChild]

app = FastAPI(title="Video Search API")

# 掛載 data 資料夾到 /static/videos 路徑，讓前端可以讀取影片
app.mount("/static/videos", StaticFiles(directory=config.DATA_DIR), name="videos")

# 全域變數存放連線
milvus_client = None
model = None

@app.on_event("startup")
async def startup_event():
    global milvus_client, model
    print("Loading embedding model...")
    model = SentenceTransformer(config.MODEL_NAME)
    print("Connecting to Milvus...")
    milvus_client = MilvusClient(config.DB_PATH)

@app.post("/search", response_model=List[VideoSearchResult])
async def search_endpoint(request: SearchRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 1. 產生查詢向量
    query_vector = model.encode([request.query])

    # 2. 搜尋 Milvus
    search_res = milvus_client.search(
        collection_name=config.COLLECTION_NAME,
        data=query_vector,
        limit=20, # 稍微拿多一點
        output_fields=["id"]
    )

    if not search_res or not search_res[0]:
        return []

    hits = search_res[0]
    hit_map = {hit["id"]: hit["distance"] for hit in hits}
    ids_to_fetch = list(hit_map.keys())

    # 3. 從 Postgres 撈取詳細資料
    session = get_session()
    try:
        contents = get_contents_by_ids(session, ids_to_fetch)
    finally:
        session.close()

    # 4. 聚合結果 (Grouping by SourceFile)
    grouped_results: Dict[str, VideoSearchResult] = {}

    for content in contents:
        str_id = str(content.id)
        if str_id not in hit_map:
            continue
            
        score = hit_map[str_id]
        source_file = content.source_file
        video_id = str(source_file.id)

        # 解析 custom 欄位
        custom_data = content.custom or {}
        
        # 建立 Child 物件
        child = SubtitleChild(
            text=content.content,
            start_seconds=custom_data.get("start_seconds", 0.0),
            end_seconds=custom_data.get("end_seconds", 0.0),
            score=score,
            custom=custom_data
        )

        # 如果這個影片還沒在結果中，先初始化
        if video_id not in grouped_results:
            # 組合靜態檔案 URL
            # 假設 filename 就是 data 資料夾下的檔案名稱
            video_url = f"/static/videos/{source_file.filename}"
            
            grouped_results[video_id] = VideoSearchResult(
                video_id=video_id,
                filename=source_file.filename,
                video_url=video_url, # 回傳給前端
                author=source_file.author,
                created_at=str(source_file.created_at),
                metadata_info=source_file.metadata_info,
                children=[]
            )
        
        # 加入 child
        grouped_results[video_id].children.append(child)

    # 5. 排序與回傳
    # 先將每個影片內的 children 依照時間排序 (播放時比較順)
    for res in grouped_results.values():
        res.children.sort(key=lambda x: x.start_seconds)

    # 將影片依照「最相關 child 的分數」來排序
    final_list = list(grouped_results.values())
    
    # 這裡邏輯稍微複雜：我們取每個影片中「分數最高」的片段作為該影片的代表分數
    final_list.sort(key=lambda x: max([c.score for c in x.children], default=0), reverse=True)

    return final_list

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)