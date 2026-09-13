import os
import hashlib
import time
import re
import io
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, ClientOptions

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


# ============================================================
# 环境变量
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BUCKET_NAME = "knowledge"
USER_ID = "default_user"

# BGE 中文模型
# bge-small-zh-v1.5 = 512维
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# 每块大约 500 中文字符
CHUNK_SIZE = 500

# 块之间保留少量上下文
CHUNK_OVERLAP = 80


if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "未配置 SUPABASE_URL 或 SUPABASE_KEY，请检查 .env / Streamlit Secrets"
    )


# ============================================================
# Supabase Client
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

_embedding_model = None


def get_embedding_model():
    """
    延迟加载 BGE 模型。

    第一次上传知识库文件时加载，
    后续直接复用。
    """

    global _embedding_model

    if _embedding_model is None:

        print(
            f"🧠 正在加载 Embedding 模型："
            f"{EMBEDDING_MODEL_NAME}"
        )

        _embedding_model = SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )

        print("✅ BGE Embedding 模型加载完成")

    return _embedding_model


# ============================================================
# 文件 Hash
# ============================================================

def calculate_file_hash(file_bytes):
    """计算文件 SHA256"""

    return hashlib.sha256(file_bytes).hexdigest()


# ============================================================
# Storage 安全文件名
# ============================================================

def make_safe_storage_filename(file_name, file_hash):

    original = Path(file_name)

    suffix = original.suffix.lower()

    stem = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        original.stem
    )

    stem = stem[:40].strip("_")

    if not stem:
        stem = "knowledge"

    short_hash = file_hash[:8]

    return f"{stem}_{short_hash}{suffix}"


# ============================================================
# PDF 解析
# ============================================================

def extract_pdf_text(file_bytes):
    """
    PDF 文本提取：

    第一层：
        PyPDF 普通文本提取

    第二层：
        如果 PDF 没有文本，
        自动使用 PyMuPDF + RapidOCR OCR。
    """

    # ========================================================
    # 第一阶段：普通 PDF 文本提取
    # ========================================================

    normal_text_parts = []

    try:

        reader = PdfReader(
            io.BytesIO(file_bytes)
        )

        for page_index, page in enumerate(reader.pages):

            try:

                text = page.extract_text() or ""

                text = text.strip()

                if text:

                    normal_text_parts.append(text)

            except Exception as e:

                print(
                    f"⚠️ PDF 第 {page_index + 1} 页普通解析失败：{e}"
                )

    except Exception as e:

        print(
            f"⚠️ PyPDF 解析失败，将尝试 OCR：{e}"
        )

    normal_text = "\n\n".join(
        normal_text_parts
    ).strip()

    # ========================================================
    # 如果普通解析成功，直接返回
    # ========================================================

    if len(normal_text) >= 50:

        print(
            f"✅ 普通 PDF 文本提取成功："
            f"{len(normal_text)} 字符"
        )

        return normal_text

    # ========================================================
    # 第二阶段：OCR
    # ========================================================

    print("")
    print("=" * 60)
    print("⚠️ PDF 没有可用文本")
    print("🔎 自动启动 OCR")
    print("=" * 60)

    try:

        import fitz
        from rapidocr_onnxruntime import RapidOCR

        ocr = RapidOCR()

        pdf = fitz.open(
            stream=file_bytes,
            filetype="pdf"
        )

        print(
            f"📄 PDF 总页数：{len(pdf)}"
        )

        ocr_text_parts = []

        for page_index in range(
            len(pdf)
        ):

            page = pdf[
                page_index
            ]

            print(
                f"🔎 OCR 第 "
                f"{page_index + 1}/"
                f"{len(pdf)} 页"
            )

            # ------------------------------------------------
            # 以 2 倍分辨率渲染
            # ------------------------------------------------

            matrix = fitz.Matrix(
                2.0,
                2.0
            )

            pix = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            image_bytes = pix.tobytes(
                "png"
            )

            # ------------------------------------------------
            # OCR
            # ------------------------------------------------

            result, _ = ocr(
                image_bytes
            )

            if not result:

                print(
                    f"⚠️ 第 {page_index + 1} 页没有识别到文字"
                )

                continue

            page_text = []

            for item in result:

                try:

                    text = item[1]

                    if text:

                        page_text.append(
                            text
                        )

                except Exception:

                    continue

            page_text = "\n".join(
                page_text
            ).strip()

            if page_text:

                ocr_text_parts.append(
                    page_text
                )

        pdf.close()

        final_text = "\n\n".join(
            ocr_text_parts
        ).strip()

        if not final_text:

            raise RuntimeError(
                "OCR 也没有识别到任何文字"
            )

        print("")
        print(
            f"✅ OCR 完成："
            f"{len(final_text)} 字符"
        )

        return final_text

    except ImportError as e:

        raise RuntimeError(
            "OCR 依赖未安装，请执行："
            "pip install pymupdf "
            "rapidocr_onnxruntime"
        )

    except Exception as e:

        raise RuntimeError(
            f"PDF OCR 失败：{e}"
        )


# ============================================================
# TXT 解析
# ============================================================

def extract_txt_text(file_bytes):

    encodings = [
        "utf-8",
        "utf-8-sig",
        "gb18030",
        "gbk",
    ]

    for encoding in encodings:

        try:

            return file_bytes.decode(
                encoding
            )

        except UnicodeDecodeError:

            continue

    raise RuntimeError(
        "TXT 文件无法识别编码"
    )


# ============================================================
# 文件文本解析
# ============================================================

def extract_file_text(file_name, file_bytes):

    suffix = Path(
        file_name
    ).suffix.lower()

    if suffix == ".pdf":

        return extract_pdf_text(
            file_bytes
        )

    if suffix == ".txt":

        return extract_txt_text(
            file_bytes
        )

    raise RuntimeError(
        f"暂不支持的知识库文件类型：{suffix}"
    )


# ============================================================
# 文本清洗
# ============================================================

def clean_text(text):

    if not text:
        return ""

    # 统一换行
    text = text.replace(
        "\r\n",
        "\n"
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # 去掉连续空格
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    # 去掉连续空行
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# 文本切块
# ============================================================

def split_text(
    text,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP
):
    """
    中文知识库切块。

    优先按照：
    段落 → 句子 → 固定长度
    """

    text = clean_text(text)

    if not text:
        return []

    # 先按段落
    paragraphs = re.split(
        r"\n\s*\n",
        text
    )

    chunks = []

    current = ""

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        # 当前块可以直接加入
        if len(current) + len(paragraph) <= chunk_size:

            if current:

                current += "\n\n" + paragraph

            else:

                current = paragraph

            continue

        # 当前块已满
        if current:

            chunks.append(
                current.strip()
            )

        # 单段超过 chunk_size
        if len(paragraph) > chunk_size:

            sentences = re.split(
                r"(?<=[。！？；.!?;])",
                paragraph
            )

            temp = ""

            for sentence in sentences:

                sentence = sentence.strip()

                if not sentence:
                    continue

                if len(temp) + len(sentence) <= chunk_size:

                    temp += sentence

                else:

                    if temp:

                        chunks.append(
                            temp.strip()
                        )

                    # 极长句直接继续切
                    if len(sentence) > chunk_size:

                        for i in range(
                            0,
                            len(sentence),
                            chunk_size - overlap
                        ):

                            part = sentence[
                                i:i + chunk_size
                            ]

                            if part.strip():

                                chunks.append(
                                    part.strip()
                                )

                    else:

                        temp = sentence

            if temp:

                current = temp

            else:

                current = ""

        else:

            current = paragraph

    if current:

        chunks.append(
            current.strip()
        )

    # ========================================================
    # 清理 + 去重
    # ========================================================

    final_chunks = []

    seen = set()

    for chunk in chunks:

        chunk = clean_text(chunk)

        if len(chunk) < 10:
            continue

        chunk_hash = hashlib.md5(
            chunk.encode(
                "utf-8"
            )
        ).hexdigest()

        if chunk_hash in seen:
            continue

        seen.add(
            chunk_hash
        )

        final_chunks.append(
            chunk
        )

    return final_chunks


# ============================================================
# 生成 Embedding
# ============================================================

def generate_embeddings(chunks):

    if not chunks:

        return []

    model = get_embedding_model()

    print(
        f"🧠 正在生成 {len(chunks)} 个向量..."
    )

    embeddings = model.encode(
        chunks,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=16,
    )

    embeddings = embeddings.tolist()

    # 检查维度
    if embeddings:

        dimension = len(
            embeddings[0]
        )

        print(
            f"✅ Embedding 完成："
            f"{len(embeddings)} 条，"
            f"{dimension} 维"
        )

        if dimension != 512:

            raise RuntimeError(
                f"Embedding 维度错误："
                f"当前 {dimension} 维，"
                f"预期 512 维"
            )

    return embeddings


# ============================================================
# 删除旧向量
# ============================================================

def delete_document_vectors(
    document_id
):
    """
    删除某个文档旧的向量。

    用于重新处理/防止重复。
    """

    try:

        result = (
            supabase
            .table("knowledge_vectors")
            .delete()
            .eq(
                "document_id",
                document_id
            )
            .execute()
        )

        print(
            f"🗑️ 已清理旧向量："
            f"{document_id}"
        )

        return True

    except Exception as e:

        print(
            f"⚠️ 清理旧向量失败：{e}"
        )

        return False


# ============================================================
# 写入知识向量
# ============================================================

def save_vectors(
    document_id,
    file_name,
    chunks,
    embeddings
):
    """
    将文本块 + 512维向量写入 knowledge_vectors。
    """

    if not chunks:

        return 0

    if len(chunks) != len(embeddings):

        raise RuntimeError(
            "文本块数量与向量数量不一致"
        )

    # 防止重复
    delete_document_vectors(
        document_id
    )

    rows = []

    for index, (
        chunk,
        embedding
    ) in enumerate(
        zip(
            chunks,
            embeddings
        )
    ):

        rows.append(
            {
                "document_id": document_id,
                "user_id": USER_ID,
                "content": chunk,
                "embedding": embedding,
                "chunk_index": index,
                "metadata": {
                    "file_name": file_name,
                    "chunk_index": index,
                },
            }
        )

    # ========================================================
    # 分批写入
    # ========================================================

    total = 0

    batch_size = 50

    for start in range(
        0,
        len(rows),
        batch_size
    ):

        batch = rows[
            start:start + batch_size
        ]

        print(
            f"☁️ 写入向量："
            f"{start + 1}-"
            f"{start + len(batch)} / "
            f"{len(rows)}"
        )

        result = (
            supabase
            .table("knowledge_vectors")
            .insert(batch)
            .execute()
        )

        total += len(
            result.data or batch
        )

    print(
        f"✅ knowledge_vectors 写入完成："
        f"{total} 条"
    )

    return total


# ============================================================
# 处理知识库文档
# ============================================================

def process_knowledge_document(
    document_id,
    file_name,
    file_bytes
):
    """
    V26.2 核心流程：

    Storage
        ↓
    PDF/TXT
        ↓
    文本
        ↓
    切块
        ↓
    BGE
        ↓
    knowledge_vectors
    """

    print("")
    print("=" * 60)
    print(
        f"🚀 开始处理知识库：{file_name}"
    )
    print("=" * 60)

    try:

        # ----------------------------------------------------
        # 1. 解析
        # ----------------------------------------------------

        print("📖 正在解析文件...")

        text = extract_file_text(
            file_name,
            file_bytes
        )

        if not text.strip():

            raise RuntimeError(
                "文件解析后没有得到文本"
            )

        print(
            f"✅ 文本解析完成："
            f"{len(text)} 字符"
        )

        # ----------------------------------------------------
        # 2. 清洗
        # ----------------------------------------------------

        text = clean_text(
            text
        )

        print(
            f"🧹 文本清洗完成："
            f"{len(text)} 字符"
        )

        # ----------------------------------------------------
        # 3. 切块
        # ----------------------------------------------------

        chunks = split_text(
            text
        )

        if not chunks:

            raise RuntimeError(
                "文本切块后没有得到有效内容"
            )

        print(
            f"✂️ 文本切块完成："
            f"{len(chunks)} 块"
        )

        # ----------------------------------------------------
        # 4. Embedding
        # ----------------------------------------------------

        embeddings = generate_embeddings(
            chunks
        )

        # ----------------------------------------------------
        # 5. 写入向量数据库
        # ----------------------------------------------------

        vector_count = save_vectors(
            document_id=document_id,
            file_name=file_name,
            chunks=chunks,
            embeddings=embeddings,
        )

        # ----------------------------------------------------
        # 6. 更新文档状态
        # ----------------------------------------------------

        (
            supabase
            .table("knowledge_documents")
            .update(
                {
                    "chunk_count": vector_count,
                    "status": "ready",
                }
            )
            .eq(
                "id",
                document_id
            )
            .eq(
                "user_id",
                USER_ID
            )
            .execute()
        )

        print(
            f"🎉 知识库处理完成："
            f"{vector_count} 个向量"
        )

        return {
            "success": True,
            "chunk_count": vector_count,
            "message": (
                f"知识库处理完成，"
                f"生成 {vector_count} 个向量"
            ),
        }

    except Exception as e:

        print(
            f"❌ 知识库处理失败：{e}"
        )

        # ----------------------------------------------------
        # 失败状态
        # ----------------------------------------------------

        try:

            (
                supabase
                .table("knowledge_documents")
                .update(
                    {
                        "status": "error",
                    }
                )
                .eq(
                    "id",
                    document_id
                )
                .eq(
                    "user_id",
                    USER_ID
                )
                .execute()
            )

        except Exception as update_error:

            print(
                f"⚠️ 更新错误状态失败："
                f"{update_error}"
            )

        return {
            "success": False,
            "chunk_count": 0,
            "message": str(e),
        }


# ============================================================
# 上传知识库文件
# ============================================================

def upload_knowledge_file(
    file_name,
    file_bytes,
    file_type=None
):
    """
    V26.2：

    上传
      ↓
    Storage
      ↓
    knowledge_documents
      ↓
    自动解析
      ↓
    自动切块
      ↓
    BGE 512维
      ↓
    knowledge_vectors
    """

    if not file_bytes:

        return {
            "success": False,
            "message": "文件内容为空",
        }

    suffix = Path(
        file_name
    ).suffix.lower()

    if suffix not in [
        ".pdf",
        ".txt",
    ]:

        return {
            "success": False,
            "message": (
                "暂时只支持 PDF / TXT 文件"
            ),
        }

    file_hash = calculate_file_hash(
        file_bytes
    )

    # ========================================================
    # 检查重复
    # ========================================================

    try:

        existing = (
            supabase
            .table("knowledge_documents")
            .select("*")
            .eq(
                "user_id",
                USER_ID
            )
            .eq(
                "file_hash",
                file_hash
            )
            .execute()
        )

        if existing.data:

            document = existing.data[0]

            # 如果已经 ready
            if document.get("status") == "ready":

                return {
                    "success": True,
                    "duplicate": True,
                    "message": (
                        "文件已经存在并完成向量化"
                    ),
                    "document": document,
                }

            # 如果之前上传过但没有完成
            print(
                "⚠️ 文件已存在，但尚未完成向量化"
            )

            document_id = document.get(
                "id"
            )

            processing = process_knowledge_document(
                document_id,
                file_name,
                file_bytes
            )

            return {
                **processing,
                "duplicate": True,
                "document": document,
            }

    except Exception as e:

        print(
            f"⚠️ 检查重复文件失败：{e}"
        )

    # ========================================================
    # Storage 文件名
    # ========================================================

    safe_filename = make_safe_storage_filename(
        file_name,
        file_hash
    )

    storage_path = (
        f"{USER_ID}/{safe_filename}"
    )

    # ========================================================
    # MIME
    # ========================================================

    if suffix == ".pdf":

        content_type = (
            "application/pdf"
        )

    elif suffix == ".txt":

        content_type = (
            "text/plain"
        )

    else:

        content_type = (
            file_type
            or
            "application/octet-stream"
        )

    # ========================================================
    # Storage 上传
    # ========================================================

    upload_success = False
    last_error = None

    for attempt in range(1, 5):

        try:

            print(
                f"☁️ Storage 上传 "
                f"{attempt}/4："
                f"{storage_path}"
            )

            result = (
                supabase
                .storage
                .from_(BUCKET_NAME)
                .upload(
                    storage_path,
                    file_bytes,
                    {
                        "content-type": content_type,
                        "upsert": "true",
                    }
                )
            )

            print(
                f"✅ Storage 上传成功："
                f"{result}"
            )

            upload_success = True

            break

        except Exception as e:

            last_error = e

            print(
                f"⚠️ 第 {attempt} 次上传失败："
                f"{e}"
            )

            if attempt < 4:

                time.sleep(3)

    if not upload_success:

        return {
            "success": False,
            "message": (
                f"Storage 上传失败："
                f"{last_error}"
            ),
        }

    # ========================================================
    # 创建数据库记录
    # ========================================================

    document_data = {

        "user_id": USER_ID,

        "file_name": file_name,

        "file_path": file_name,

        "file_type": suffix,

        "file_size": len(file_bytes),

        "file_hash": file_hash,

        "storage_path": storage_path,

        "chunk_count": 0,

        "status": "processing",
    }

    try:

        result = (
            supabase
            .table("knowledge_documents")
            .insert(
                document_data
            )
            .execute()
        )

        print(
            "✅ 数据库记录创建成功"
        )

        if not result.data:

            raise RuntimeError(
                "数据库没有返回文档记录"
            )

        document = result.data[0]

        document_id = document.get(
            "id"
        )

        if not document_id:

            raise RuntimeError(
                "数据库记录缺少 id"
            )

        # ====================================================
        # V26.2 核心：立即向量化
        # ====================================================

        processing = process_knowledge_document(
            document_id=document_id,
            file_name=file_name,
            file_bytes=file_bytes,
        )

        if not processing["success"]:

            return {
                "success": False,
                "duplicate": False,
                "message": (
                    "文件已经上传，但知识库向量化失败："
                    + processing["message"]
                ),
                "document": document,
            }

        document.update(
            {
                "chunk_count": processing[
                    "chunk_count"
                ],
                "status": "ready",
            }
        )

        return {
            "success": True,
            "duplicate": False,
            "message": (
                "知识库文件上传并向量化成功"
            ),
            "document": document,
        }

    except Exception as e:

        print(
            f"❌ 数据库/向量化失败：{e}"
        )

        # ====================================================
        # 回滚 Storage
        # ====================================================

        try:

            supabase.storage.from_(
                BUCKET_NAME
            ).remove(
                [storage_path]
            )

            print(
                "↩️ 已回滚 Storage 文件"
            )

        except Exception as rollback_error:

            print(
                f"⚠️ Storage 回滚失败："
                f"{rollback_error}"
            )

        return {
            "success": False,
            "message": (
                f"知识库处理失败：{e}"
            ),
        }


# ============================================================
# 获取知识库文件列表
# ============================================================

def list_knowledge_documents():

    try:

        result = (
            supabase
            .table(
                "knowledge_documents"
            )
            .select("*")
            .eq(
                "user_id",
                USER_ID
            )
            .order(
                "created_at",
                desc=True
            )
            .execute()
        )

        return result.data or []

    except Exception as e:

        print(
            f"❌ 获取知识库列表失败：{e}"
        )

        return []


# ============================================================
# 删除知识库文件
# ============================================================

def delete_knowledge_document(
    document_id
):

    try:

        # ----------------------------------------------------
        # 找数据库记录
        # ----------------------------------------------------

        result = (
            supabase
            .table(
                "knowledge_documents"
            )
            .select("*")
            .eq(
                "id",
                document_id
            )
            .eq(
                "user_id",
                USER_ID
            )
            .single()
            .execute()
        )

        document = result.data

        if not document:

            return {
                "success": False,
                "message": (
                    "找不到知识库文件"
                ),
            }

        storage_path = document.get(
            "storage_path"
        )

        # ----------------------------------------------------
        # V26.3：先删除向量
        # ----------------------------------------------------

        delete_document_vectors(
            document_id
        )

        # ----------------------------------------------------
        # 删除 Storage
        # ----------------------------------------------------

        if storage_path:

            try:

                supabase.storage.from_(
                    BUCKET_NAME
                ).remove(
                    [storage_path]
                )

            except Exception as e:

                print(
                    f"⚠️ Storage 删除失败："
                    f"{e}"
                )

        # ----------------------------------------------------
        # 删除数据库记录
        # ----------------------------------------------------

        (
            supabase
            .table(
                "knowledge_documents"
            )
            .delete()
            .eq(
                "id",
                document_id
            )
            .eq(
                "user_id",
                USER_ID
            )
            .execute()
        )

        return {
            "success": True,
            "message": (
                "知识库文件及向量删除成功"
            ),
        }

    except Exception as e:

        return {
            "success": False,
            "message": (
                f"删除失败：{e}"
            ),
        }


# ============================================================
# 下载知识库文件
# ============================================================

def download_knowledge_file(
    storage_path
):

    try:

        data = (
            supabase
            .storage
            .from_(BUCKET_NAME)
            .download(
                storage_path
            )
        )

        return data

    except Exception as e:

        print(
            f"❌ 下载知识库文件失败："
            f"{e}"
        )

        return None


# ============================================================
# 获取知识库数量
# ============================================================

def get_knowledge_count():

    try:

        result = (
            supabase
            .table(
                "knowledge_documents"
            )
            .select("id")
            .eq(
                "user_id",
                USER_ID
            )
            .execute()
        )

        return len(
            result.data or []
        )

    except Exception as e:

        print(
            f"❌ 获取知识库数量失败："
            f"{e}"
        )

        return 0
# ============================================================
# V26.4 云端知识库重建
# ============================================================

def rebuild_cloud_knowledge():
    """
    重新处理所有云端知识库文件。

    Storage
        ↓
    下载
        ↓
    PDF/TXT解析
        ↓
    切块
        ↓
    BGE
        ↓
    knowledge_vectors
    """

    documents = list_knowledge_documents()

    if not documents:

        return {
            "success": True,
            "message": "云端知识库为空",
            "total": 0,
            "success_count": 0,
            "failed_count": 0,
        }

    success_count = 0
    failed_count = 0
    results = []

    print("")
    print("=" * 60)
    print("🚀 开始重建云端知识库")
    print("=" * 60)

    for index, document in enumerate(documents, start=1):

        document_id = document.get("id")
        file_name = document.get("file_name")
        storage_path = document.get("storage_path")

        print("")
        print(
            f"📚 [{index}/{len(documents)}] "
            f"{file_name}"
        )

        try:

            if not storage_path:

                raise RuntimeError(
                    "文件缺少 storage_path"
                )

            file_bytes = download_knowledge_file(
                storage_path
            )

            if not file_bytes:

                raise RuntimeError(
                    "无法从 Storage 下载文件"
                )

            result = process_knowledge_document(
                document_id=document_id,
                file_name=file_name,
                file_bytes=file_bytes,
            )

            if result.get("success"):

                success_count += 1

            else:

                failed_count += 1

            results.append(
                {
                    "file_name": file_name,
                    **result,
                }
            )

        except Exception as e:

            failed_count += 1

            results.append(
                {
                    "file_name": file_name,
                    "success": False,
                    "message": str(e),
                }
            )

            print(
                f"❌ 重建失败：{e}"
            )

    print("")
    print("=" * 60)
    print("🎉 云端知识库重建完成")
    print(
        f"总文件：{len(documents)}"
    )
    print(
        f"成功：{success_count}"
    )
    print(
        f"失败：{failed_count}"
    )
    print("=" * 60)

    return {
        "success": failed_count == 0,
        "message": "云端知识库重建完成",
        "total": len(documents),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }