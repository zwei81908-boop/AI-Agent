import os
import numpy as np

from dotenv import load_dotenv
from supabase import create_client, ClientOptions
from sentence_transformers import SentenceTransformer


# ============================================================
# 1. 环境变量
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "未配置 SUPABASE_URL 或 SUPABASE_KEY"
    )


# ============================================================
# 2. Supabase
# ============================================================

options = ClientOptions(
    postgrest_client_timeout=60,
    storage_client_timeout=120,
    function_client_timeout=60
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=options
)


# ============================================================
# 3. BGE Embedding
# ============================================================

print("正在加载 BGE Embedding 模型...")

embedding_model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)

print(
    "Embedding 维度：",
    embedding_model.get_sentence_embedding_dimension()
)


# ============================================================
# 4. 文本向量化
# ============================================================

def embed_text(text):
    """
    将文本转换为 512 维向量
    """

    if not text:
        text = ""

    vector = embedding_model.encode(
        [text],
        normalize_embeddings=True
    )[0]

    return vector.tolist()


# ============================================================
# 5. 保存向量到 Supabase
# ============================================================

def save_vectors(chunks):
    """
    chunks 格式：

    [
        {
            "content": "...",
            "source": "xxx.pdf"
        }
    ]
    """

    if not chunks:
        return {
            "success": False,
            "message": "没有可保存的内容"
        }

    rows = []

    print(
        f"开始生成 {len(chunks)} 个文本向量..."
    )

    texts = [
        item.get("content", "")
        for item in chunks
    ]

    embeddings = embedding_model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    for item, embedding in zip(
        chunks,
        embeddings
    ):

        rows.append({
            "content": item.get("content", ""),
            "source": item.get("source", ""),
            "embedding": embedding.tolist()
        })

    # 分批插入
    batch_size = 100

    for i in range(
        0,
        len(rows),
        batch_size
    ):

        batch = rows[
            i:i + batch_size
        ]

        supabase.table(
            "knowledge_vectors"
        ).insert(batch).execute()

        print(
            f"已保存：{min(i + batch_size, len(rows))}/{len(rows)}"
        )

    return {
        "success": True,
        "count": len(rows)
    }


# ============================================================
# 6. 云端向量搜索
# ============================================================

def search_cloud_vectors(
    query,
    top_k=5
):
    """
    从 Supabase knowledge_vectors
    查询最相关知识。
    """

    query_embedding = embed_text(query)

    try:

        result = supabase.rpc(
            "match_knowledge_vectors",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "match_threshold": 0.30
            }
        ).execute()

        return result.data or []

    except Exception as e:

        print(
            "RPC 向量搜索失败：",
            e
        )

        return []


# ============================================================
# 7. 统一知识库搜索接口
# ============================================================

def search_knowledge(
    query,
    n=5,
    top_k=None
):
    """
    统一 RAG 搜索接口。

    兼容：

        search_knowledge(
            query,
            n=3
        )

    也兼容：

        search_knowledge(
            query,
            top_k=3
        )
    """

    if top_k is None:
        top_k = n

    results = search_cloud_vectors(
        query,
        top_k=top_k
    )

    if not results:
        return (
            "知识库暂时没有找到相关内容。"
        )

    parts = []

    for i, item in enumerate(
        results,
        1
    ):

        content = item.get(
            "content",
            ""
        )

        source = item.get(
            "source",
            "未知来源"
        )

        similarity = item.get(
            "similarity",
            item.get(
                "distance",
                0
            )
        )

        try:
            similarity = float(
                similarity
            )
        except Exception:
            similarity = 0.0

        parts.append(
            f"""
【知识片段 {i}】
来源：{source}
相似度：{similarity:.4f}

{content}
"""
        )

    return "\n".join(parts)


# ============================================================
# 8. 获取云端向量数量
# ============================================================

def get_cloud_vector_count():

    try:

        result = supabase.table(
            "knowledge_vectors"
        ).select(
            "id",
            count="exact"
        ).limit(1).execute()

        return result.count or 0

    except Exception as e:

        print(
            "获取向量数量失败：",
            e
        )

        return 0


# ============================================================
# 9. 测试
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("云端 RAG 测试")
    print("=" * 60)

    print(
        "云端向量数量：",
        get_cloud_vector_count()
    )

    answer = search_knowledge(
        "什么是结构化分析？",
        n=3
    )

    print(answer)