# ============================================================
# cloud_rag.py
# V25 云端 RAG 核心模块
#
# Supabase Storage
#       ↓
# 文本 Chunk
#       ↓
# BGE Embedding 512维
#       ↓
# Supabase knowledge_vectors
#       ↓
# pgvector
#       ↓
# match_knowledge_vectors_v25
#       ↓
# 云端 RAG 检索
# ============================================================

import os
from typing import Any

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

USER_ID = "default_user"


if not SUPABASE_URL:
    raise RuntimeError("未配置 SUPABASE_URL")

if not SUPABASE_KEY:
    raise RuntimeError("未配置 SUPABASE_KEY")


# ============================================================
# 2. Supabase 客户端
# ============================================================

options = ClientOptions(
    postgrest_client_timeout=60,
    storage_client_timeout=120,
    function_client_timeout=60,
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=options,
)


# ============================================================
# 3. BGE Embedding
# ============================================================

print("正在加载 BGE Embedding 模型...")

embedding_model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)


# 兼容不同 sentence-transformers 版本
try:
    EMBEDDING_DIM = embedding_model.get_embedding_dimension()
except AttributeError:
    EMBEDDING_DIM = (
        embedding_model.get_sentence_embedding_dimension()
    )

print(f"Embedding 维度：{EMBEDDING_DIM}")


# V25 要求 512 维
if EMBEDDING_DIM != 512:
    raise RuntimeError(
        f"Embedding 维度错误：当前为 {EMBEDDING_DIM}，"
        f"V25 要求 512 维"
    )


# ============================================================
# 4. 单文本 Embedding
# ============================================================

def embed_text(text: str) -> np.ndarray:
    """
    将一段文本转换为 512 维向量。
    """

    text = str(text or "").strip()

    if not text:
        return np.zeros(
            EMBEDDING_DIM,
            dtype=np.float32,
        )

    vector = embedding_model.encode(
        text,
        normalize_embeddings=True,
    )

    return np.asarray(
        vector,
        dtype=np.float32,
    )


# ============================================================
# 5. 批量 Embedding
# ============================================================

def embed_texts(
    texts: list[str],
) -> np.ndarray:
    """
    批量生成文本向量。
    """

    clean_texts = [
        str(text or "").strip()
        for text in texts
    ]

    clean_texts = [
        text
        for text in clean_texts
        if text
    ]

    if not clean_texts:
        return np.empty(
            (0, EMBEDDING_DIM),
            dtype=np.float32,
        )

    embeddings = embedding_model.encode(
        clean_texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return np.asarray(
        embeddings,
        dtype=np.float32,
    )


# ============================================================
# 6. 标准化 Chunk
# ============================================================

def _normalize_chunks(chunks):
    """
    将不同格式的 Chunk 统一成：

    {
        content,
        file_name,
        document_id,
        metadata
    }
    """

    normalized_chunks = []

    for index, item in enumerate(chunks):

        # --------------------------------------------
        # Chunk 是 dict
        # --------------------------------------------

        if isinstance(item, dict):

            content = str(
                item.get("content", "")
            ).strip()

            file_name = str(
                item.get("file_name")
                or item.get("source")
                or "unknown"
            ).strip()

            document_id = item.get(
                "document_id"
            )

            metadata = item.get(
                "metadata",
                {},
            )

        # --------------------------------------------
        # Chunk 是字符串
        # --------------------------------------------

        else:

            content = str(
                item or ""
            ).strip()

            file_name = "unknown"

            document_id = None

            metadata = {}

        # --------------------------------------------
        # 跳过空文本
        # --------------------------------------------

        if not content:
            continue

        # --------------------------------------------
        # metadata 必须是 dict
        # --------------------------------------------

        if not isinstance(metadata, dict):
            metadata = {}

        normalized_chunks.append(
            {
                "content": content,
                "file_name": file_name,
                "document_id": document_id,
                "metadata": metadata,
                "original_index": index,
            }
        )

    return normalized_chunks


# ============================================================
# 7. 保存云端向量
# ============================================================

def save_vectors(chunks):
    """
    将 Chunk：

    文本
      ↓
    BGE Embedding
      ↓
    Supabase knowledge_vectors
    """

    if not chunks:

        print("⚠️ 没有需要保存的 Chunk")

        return {
            "success": False,
            "count": 0,
            "message": "没有 Chunk",
        }

    # --------------------------------------------
    # 标准化
    # --------------------------------------------

    normalized_chunks = _normalize_chunks(
        chunks
    )

    if not normalized_chunks:

        print("⚠️ 没有有效文本 Chunk")

        return {
            "success": False,
            "count": 0,
            "message": "没有有效文本",
        }

    print(
        f"开始生成 "
        f"{len(normalized_chunks)} "
        f"个文本向量..."
    )

    # --------------------------------------------
    # 提取文本
    # --------------------------------------------

    texts = [
        item["content"]
        for item in normalized_chunks
    ]

    # --------------------------------------------
    # Embedding
    # --------------------------------------------

    embeddings = embed_texts(
        texts
    )

    if len(embeddings) != len(
        normalized_chunks
    ):

        return {
            "success": False,
            "count": 0,
            "message": "Embedding 数量不匹配",
        }

    # --------------------------------------------
    # 构造数据库记录
    # --------------------------------------------

    rows = []

    for index, (
        item,
        embedding,
    ) in enumerate(
        zip(
            normalized_chunks,
            embeddings,
        )
    ):

        row = {
            "user_id": USER_ID,

            "file_name": item[
                "file_name"
            ],

            "content": item[
                "content"
            ],

            "chunk_index": index,

            "embedding": embedding.tolist(),

            "metadata": item[
                "metadata"
            ],
        }

        # document_id 有值才写入
        if item["document_id"] is not None:

            row["document_id"] = (
                item["document_id"]
            )

        rows.append(row)

    # --------------------------------------------
    # 分批写入
    # --------------------------------------------

    batch_size = 50

    total = len(rows)

    for start in range(
        0,
        total,
        batch_size,
    ):

        end = min(
            start + batch_size,
            total,
        )

        batch = rows[
            start:end
        ]

        (
            supabase
            .table(
                "knowledge_vectors"
            )
            .insert(batch)
            .execute()
        )

        print(
            f"✅ 已写入云端向量 "
            f"{end}/{total}"
        )

    print(
        "✅ 云端向量写入完成"
    )

    return {
        "success": True,
        "count": total,
        "message": "云端向量写入成功",
    }


# ============================================================
# 8. 云端向量搜索
# ============================================================

def search_cloud_vectors(
    query_embedding,
    n=5,
    threshold=0.30,
):
    """
    调用 Supabase RPC：

    match_knowledge_vectors_v25
    """

    if isinstance(
        query_embedding,
        np.ndarray,
    ):

        embedding = (
            query_embedding.tolist()
        )

    else:

        embedding = list(
            query_embedding
        )

    try:

        result = supabase.rpc(
            "match_knowledge_vectors_v25",
            {
                "query_embedding": embedding,

                "match_threshold": float(
                    threshold
                ),

                "match_count": int(n),
            },
        ).execute()

        data = result.data or []

        results = []

        for item in data:

            results.append(
                {
                    "id": item.get(
                        "id"
                    ),

                    "content": item.get(
                        "content",
                        "",
                    ),

                    "source": item.get(
                        "file_name",
                        "unknown",
                    ),

                    "file_name": item.get(
                        "file_name",
                        "unknown",
                    ),

                    "chunk_index": item.get(
                        "chunk_index",
                        0,
                    ),

                    "similarity": float(
                        item.get(
                            "similarity",
                            0,
                        )
                    ),
                }
            )

        return results

    except Exception as e:

        print(
            "❌ 云端向量搜索失败：",
            e,
        )

        return []


# ============================================================
# 9. 云端知识库搜索
# ============================================================

def search_knowledge(
    query,
    n=5,
    top_k=None,
):
    """
    给 Agent 使用的统一 RAG 搜索接口。

    兼容：

        search_knowledge(query)

        search_knowledge(query, 3)

        search_knowledge(query, n=3)

        search_knowledge(query, top_k=3)
    """

    query = str(
        query or ""
    ).strip()

    if not query:

        return "请输入要查询的问题。"

    # 兼容旧代码
    if top_k is not None:

        n = top_k

    try:

        n = int(n)

    except Exception:

        n = 5

    # 限制范围
    n = max(
        1,
        min(n, 20),
    )

    # --------------------------------------------
    # Query Embedding
    # --------------------------------------------

    query_embedding = embed_text(
        query
    )

    # --------------------------------------------
    # 云端向量搜索
    # --------------------------------------------

    results = search_cloud_vectors(
        query_embedding=query_embedding,
        n=n,
        threshold=0.30,
    )

    # --------------------------------------------
    # 没有结果
    # --------------------------------------------

    if not results:

        return (
            "知识库暂时没有找到相关内容。"
        )

    # --------------------------------------------
    # 格式化结果
    # --------------------------------------------

    parts = []

    for index, item in enumerate(
        results,
        1,
    ):

        source = (
            item.get(
                "file_name"
            )
            or item.get(
                "source",
                "未知来源",
            )
        )

        content = item.get(
            "content",
            "",
        )

        similarity = item.get(
            "similarity",
            0,
        )

        try:

            similarity = float(
                similarity
            )

        except Exception:

            similarity = 0.0

        parts.append(
            (
                f"【知识片段 {index}】\n"
                f"来源：{source}\n"
                f"相似度：{similarity:.4f}\n\n"
                f"{content}"
            )
        )

    return "\n\n".join(
        parts
    )


# ============================================================
# 10. 获取云端向量数量
# ============================================================

def get_cloud_vector_count():
    """
    获取 knowledge_vectors 总数量。
    """

    try:

        result = (
            supabase
            .table(
                "knowledge_vectors"
            )
            .select(
                "id",
                count="exact",
            )
            .limit(1)
            .execute()
        )

        return int(
            result.count or 0
        )

    except Exception as e:

        print(
            "❌ 获取云端向量数量失败：",
            e,
        )

        return 0


# ============================================================
# 11. 删除指定文件的云端向量
# ============================================================

def delete_cloud_vectors(
    file_name,
):
    """
    根据 file_name 删除向量。
    """

    file_name = str(
        file_name or ""
    ).strip()

    if not file_name:

        return {
            "success": False,
            "count": 0,
            "message": "文件名为空",
        }

    try:

        # ----------------------------------------
        # 查询数量
        # ----------------------------------------

        existing = (
            supabase
            .table(
                "knowledge_vectors"
            )
            .select(
                "id"
            )
            .eq(
                "user_id",
                USER_ID,
            )
            .eq(
                "file_name",
                file_name,
            )
            .execute()
        )

        count = len(
            existing.data or []
        )

        # ----------------------------------------
        # 删除
        # ----------------------------------------

        (
            supabase
            .table(
                "knowledge_vectors"
            )
            .delete()
            .eq(
                "user_id",
                USER_ID,
            )
            .eq(
                "file_name",
                file_name,
            )
            .execute()
        )

        return {
            "success": True,
            "count": count,
            "message": (
                f"已删除 {count} 个向量"
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "count": 0,
            "message": str(e),
        }


# ============================================================
# 12. 云端 RAG 健康检查
# ============================================================

def health_check():
    """
    V25 云端 RAG 完整健康检查。
    """

    result = {
        "supabase": False,
        "embedding": False,
        "vectors": 0,
        "ready": False,
    }

    # --------------------------------------------
    # Supabase
    # --------------------------------------------

    try:

        (
            supabase
            .table(
                "knowledge_vectors"
            )
            .select(
                "id"
            )
            .limit(1)
            .execute()
        )

        result[
            "supabase"
        ] = True

    except Exception as e:

        print(
            "Supabase 检查失败：",
            e,
        )

    # --------------------------------------------
    # Embedding
    # --------------------------------------------

    try:

        test_vector = embed_text(
            "测试"
        )

        result[
            "embedding"
        ] = (
            len(test_vector)
            == EMBEDDING_DIM
            == 512
        )

    except Exception as e:

        print(
            "Embedding 检查失败：",
            e,
        )

    # --------------------------------------------
    # 向量数量
    # --------------------------------------------

    result[
        "vectors"
    ] = get_cloud_vector_count()

    # --------------------------------------------
    # 最终状态
    # --------------------------------------------

    result[
        "ready"
    ] = (
        result["supabase"]
        and result["embedding"]
        and result["vectors"] > 0
    )

    return result


# ============================================================
# 13. 测试函数
# ============================================================

def test_search():
    """
    V25 RAG 搜索测试。
    """

    print(
        "\n开始测试云端 RAG："
    )

    query = (
        "什么是结构化分析？"
    )

    print(
        f"\n问题：{query}\n"
    )

    result = search_knowledge(
        query,
        n=3,
    )

    print(result)


# ============================================================
# 14. 主程序
# ============================================================

if __name__ == "__main__":

    print("=" * 60)

    print(
        "V25 云端 RAG 测试"
    )

    print("=" * 60)

    print(
        f"Embedding 维度："
        f"{EMBEDDING_DIM}"
    )

    # --------------------------------------------
    # 向量数量
    # --------------------------------------------

    count = (
        get_cloud_vector_count()
    )

    print(
        f"云端向量数量：{count}"
    )

    # --------------------------------------------
    # RAG 搜索
    # --------------------------------------------

    test_search()

    # --------------------------------------------
    # 健康检查
    # --------------------------------------------

    print(
        "\n" + "=" * 60
    )

    print(
        "健康检查"
    )

    print(
        "=" * 60
    )

    print(
        health_check()
    )

    print(
        "\nV25 测试结束"
    )