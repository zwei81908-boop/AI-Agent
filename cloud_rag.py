import os
import re
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, ClientOptions
from sentence_transformers import SentenceTransformer


# ============================================================
# 配置
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

USER_ID = "default_user"

MODEL_NAME = "BAAI/bge-small-zh-v1.5"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "未配置 SUPABASE_URL 或 SUPABASE_KEY"
    )


# ============================================================
# Supabase
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
# Embedding 模型
# ============================================================

print("正在加载 BGE Embedding 模型...")

embedding_model = SentenceTransformer(
    MODEL_NAME
)

print(
    "Embedding 维度：",
    embedding_model.get_sentence_embedding_dimension()
)


# ============================================================
# 文本 Embedding
# ============================================================

def embed_text(text):

    vector = embedding_model.encode(
        text,
        normalize_embeddings=True
    )

    return vector.tolist()


def embed_texts(texts):

    if not texts:
        return []

    vectors = embedding_model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    return vectors.tolist()


# ============================================================
# 文本切块
# ============================================================

def split_text(
    text,
    chunk_size=800,
    overlap=120
):

    text = re.sub(
        r"\r\n?",
        "\n",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + chunk_size,
            len(text)
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


# ============================================================
# 保存向量到 Supabase
# ============================================================

def save_vectors(
    file_name,
    chunks,
    document_id=None,
    metadata_list=None
):

    if not chunks:
        return {
            "success": False,
            "count": 0,
            "message": "没有可保存的文本块"
        }


    print(
        f"开始向量化：{file_name}"
    )

    vectors = embed_texts(chunks)

    records = []

    for i, (chunk, vector) in enumerate(
        zip(chunks, vectors)
    ):

        metadata = {}

        if metadata_list and i < len(metadata_list):
            metadata = metadata_list[i] or {}

        records.append({
            "user_id": USER_ID,
            "document_id": document_id,
            "file_name": file_name,
            "content": chunk,
            "chunk_index": i,
            "embedding": vector,
            "metadata": metadata,
        })


    # --------------------------------------------------------
    # 删除这个文件原来的向量
    # --------------------------------------------------------

    try:

        query = (
            supabase
            .table("knowledge_vectors")
            .delete()
            .eq("user_id", USER_ID)
            .eq("file_name", file_name)
        )

        query.execute()

    except Exception as e:

        print(
            f"⚠️ 删除旧向量失败：{e}"
        )


    # --------------------------------------------------------
    # 分批写入
    # --------------------------------------------------------

    batch_size = 50
    saved = 0

    for start in range(
        0,
        len(records),
        batch_size
    ):

        batch = records[
            start:start + batch_size
        ]

        result = (
            supabase
            .table("knowledge_vectors")
            .insert(batch)
            .execute()
        )

        count = len(
            result.data or batch
        )

        saved += count

        print(
            f"☁️ 云端向量写入："
            f"{saved}/{len(records)}"
        )


    return {
        "success": True,
        "count": saved,
        "message": f"成功保存 {saved} 个向量"
    }


# ============================================================
# 云端向量搜索
# ============================================================

def search_cloud_knowledge(
    query,
    top_k=5,
    threshold=0.30
):

    if not query or not query.strip():
        return []


    query_vector = embed_text(
        query
    )


    try:

        result = supabase.rpc(
            "match_knowledge_vectors",
            {
                "query_embedding": query_vector,
                "match_threshold": threshold,
                "match_count": top_k,
            }
        ).execute()


        rows = result.data or []

        formatted = []

        for row in rows:

            formatted.append({
                "content": row.get(
                    "content",
                    ""
                ),

                "source": row.get(
                    "file_name",
                    ""
                ),

                "chunk_index": row.get(
                    "chunk_index",
                    0
                ),

                "similarity": float(
                    row.get(
                        "similarity",
                        0
                    )
                ),

                "metadata": row.get(
                    "metadata",
                    {}
                ),
            })


        return formatted


    except Exception as e:

        print(
            f"❌ 云端 RAG 搜索失败：{e}"
        )

        return []


# ============================================================
# 兼容原来的 search_knowledge
# ============================================================

def search_knowledge(
    query,
    top_k=5
):

    results = search_cloud_knowledge(
        query,
        top_k=top_k
    )

    if not results:
        return "知识库暂时没有找到相关内容。"


    parts = []

    for i, item in enumerate(
        results,
        1
    ):

        parts.append(
            f"""
【知识片段 {i}】
来源：{item['source']}
相似度：{item['similarity']:.4f}

{item['content']}
"""
        )


    return "\n".join(parts)


# ============================================================
# 云端向量数量
# ============================================================

def get_cloud_vector_count():

    try:

        result = (
            supabase
            .table("knowledge_vectors")
            .select("id")
            .eq("user_id", USER_ID)
            .execute()
        )

        return len(
            result.data or []
        )

    except Exception as e:

        print(
            f"获取云端向量数量失败：{e}"
        )

        return 0


# ============================================================
# 删除文件向量
# ============================================================

def delete_cloud_vectors(
    file_name
):

    try:

        (
            supabase
            .table("knowledge_vectors")
            .delete()
            .eq("user_id", USER_ID)
            .eq("file_name", file_name)
            .execute()
        )

        return {
            "success": True
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# ============================================================
# 根据文件 Hash 找 Supabase 文档
# ============================================================

def get_document_by_hash(
    file_hash
):

    try:

        result = (
            supabase
            .table("knowledge_documents")
            .select("*")
            .eq("user_id", USER_ID)
            .eq("file_hash", file_hash)
            .execute()
        )

        data = result.data or []

        return data[0] if data else None

    except Exception as e:

        print(
            f"查询文档失败：{e}"
        )

        return None


# ============================================================
# 计算 Hash
# ============================================================

def calculate_file_hash(
    file_bytes
):

    return hashlib.sha256(
        file_bytes
    ).hexdigest()


# ============================================================
# PDF / TXT 读取
# ============================================================

def read_knowledge_file(
    path
):

    suffix = path.suffix.lower()


    # --------------------------------------------------------
    # TXT
    # --------------------------------------------------------

    if suffix == ".txt":

        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )


    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if suffix == ".pdf":

        from pypdf import PdfReader

        reader = PdfReader(
            str(path)
        )

        pages = []

        for page in reader.pages:

            try:

                text = page.extract_text()

                if text:
                    pages.append(text)

            except Exception as e:

                print(
                    f"⚠️ PDF 页面读取失败：{e}"
                )


        return "\n".join(pages)


    return ""


# ============================================================
# 构建单个文件的云端向量
# ============================================================

def index_file(
    path
):

    print()
    print("=" * 60)
    print(
        f"📚 开始处理：{path.name}"
    )
    print("=" * 60)


    try:

        file_bytes = path.read_bytes()

        file_hash = calculate_file_hash(
            file_bytes
        )

        document = get_document_by_hash(
            file_hash
        )

        document_id = None

        if document:

            document_id = document.get(
                "id"
            )

            print(
                f"☁️ 找到云端文档 ID："
                f"{document_id}"
            )


        text = read_knowledge_file(
            path
        )

        if not text.strip():

            return {
                "success": False,
                "file": path.name,
                "count": 0,
                "message": "文件没有提取到文本"
            }


        chunks = split_text(
            text
        )

        print(
            f"📄 文本长度：{len(text)}"
        )

        print(
            f"✂️ 文本块数量：{len(chunks)}"
        )


        result = save_vectors(
            file_name=path.name,
            chunks=chunks,
            document_id=document_id
        )


        # ----------------------------------------------------
        # 更新知识库文档 chunk_count
        # ----------------------------------------------------

        if result.get("success") and document_id:

            try:

                (
                    supabase
                    .table("knowledge_documents")
                    .update({
                        "chunk_count": result["count"],
                        "status": "indexed"
                    })
                    .eq("id", document_id)
                    .execute()
                )

            except Exception as e:

                print(
                    f"⚠️ 更新文档状态失败：{e}"
                )


        return {
            "success": result.get(
                "success",
                False
            ),

            "file": path.name,

            "count": result.get(
                "count",
                0
            ),

            "message": result.get(
                "message",
                ""
            )
        }


    except Exception as e:

        return {
            "success": False,
            "file": path.name,
            "count": 0,
            "message": str(e)
        }


# ============================================================
# 扫描知识库
# ============================================================

def index_knowledge_directory(
    knowledge_dir="knowledge"
):

    root = Path(
        knowledge_dir
    )

    if not root.exists():

        return []


    files = []

    files.extend(
        root.rglob("*.pdf")
    )

    files.extend(
        root.rglob("*.PDF")
    )

    files.extend(
        root.rglob("*.txt")
    )

    files.extend(
        root.rglob("*.TXT")
    )


    # 去重
    unique = {}

    for path in files:
        unique[str(path.resolve())] = path

    files = list(
        unique.values()
    )


    print()
    print(
        f"📚 找到知识库文件：{len(files)} 个"
    )


    results = []

    for i, path in enumerate(
        files,
        1
    ):

        print()
        print(
            f"========== {i}/{len(files)} =========="
        )

        result = index_file(
            path
        )

        results.append(
            result
        )


    print()
    print("=" * 60)
    print("🎉 云端 RAG 构建完成")
    print("=" * 60)


    total = sum(
        x.get("count", 0)
        for x in results
        if x.get("success")
    )

    success_count = sum(
        1
        for x in results
        if x.get("success")
    )


    print(
        f"📚 文件：{success_count}/{len(results)}"
    )

    print(
        f"🧠 向量：{total}"
    )


    return results