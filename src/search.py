import argparse
from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer
import config
from database import get_session, get_contents_by_ids

def search(query):
    client = MilvusClient(config.DB_PATH)
    model = SentenceTransformer(config.MODEL_NAME)
    session = get_session()
    
    print(f"Query: '{query}'")
    
    # 1. 產生查詢向量
    query_vector = model.encode([query])
    
    # 2. 搜尋 Milvus (只拿回 ID)
    search_res = client.search(
        collection_name=config.COLLECTION_NAME,
        data=query_vector,
        limit=5,
        output_fields=["id"] # 其實只回傳 id 就夠了
    )
    
    if not search_res or not search_res[0]:
        print("No matches found.")
        return

    # 解析搜尋結果
    hits = search_res[0]
    hit_map = {hit["id"]: hit["distance"] for hit in hits} # id -> score
    ids_to_fetch = list(hit_map.keys())
    
    # 3. 從 Postgres 撈取詳細資料
    print(f"Fetching details for {len(ids_to_fetch)} items from PostgreSQL...")
    contents = get_contents_by_ids(session, ids_to_fetch)
    
    # 4. 顯示結果 (依照分數排序)
    # 因為 Postgres 回傳順序不一定，我們手動依分數排序
    results = []
    for content in contents:
        str_id = str(content.id)
        if str_id in hit_map:
            results.append({
                "content": content,
                "score": hit_map[str_id]
            })
            
    # 根據分數由高到低排序
    results.sort(key=lambda x: x["score"], reverse=True)
    
    print(f"\nFound {len(results)} matches:\n")
    print("-" * 50)
    for item in results:
        c = item["content"]
        score = item["score"]
        
        # 解析 custom 欄位
        custom_data = c.custom or {}
        start_time = custom_data.get("start_seconds", 0)
        
        # 格式化時間 mm:ss
        m, s = divmod(start_time, 60)
        time_str = f"{int(m):02d}:{int(s):02d}"
        
        print(f"File:  {c.source_file.filename}")
        print(f"Type:  {c.type}")
        print(f"Time:  {time_str} (s: {start_time:.2f})")
        print(f"Text:  {c.content}")
        print(f"Score: {score:.4f}")
        print("-" * 50)
        
    session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search video subtitles.")
    parser.add_argument("query", type=str, help="Search query string")
    args = parser.parse_args()
    
    search(args.query)