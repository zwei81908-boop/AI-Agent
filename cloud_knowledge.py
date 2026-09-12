import os
import hashlib
import time
import re
import uuid
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, ClientOptions


# ============================================================
# 环境变量
# ============================================================

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

BUCKET_NAME = "knowledge"
USER_ID = "default_user"


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
# 文件 Hash
# ============================================================

def calculate_file_hash(file_bytes):
    """计算文件 SHA256"""
    return hashlib.sha256(file_bytes).hexdigest()


# ============================================================
# 生成安全的 Storage 文件名
# ============================================================

def make_safe_storage_filename(file_name, file_hash):
    """
    将用户原始文件名转换成 Supabase Storage 安全文件名。

    原始：
        2024年上半年软件设计师《知识点集锦》(3).pdf

    Storage：
        2024_pdf_8f31a2c4.pdf
    """

    original = Path(file_name)

    suffix = original.suffix.lower()

    # 只保留 ASCII 字母、数字、下划线、横线
    stem = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        original.stem
    )

    # 避免名字太长
    stem = stem[:40].strip("_")

    if not stem:
        stem = "knowledge"

    # 使用 hash 前 8 位保证唯一
    short_hash = file_hash[:8]

    safe_name = f"{stem}_{short_hash}{suffix}"

    return safe_name


# ============================================================
# 上传知识库文件
# ============================================================

def upload_knowledge_file(
    file_name,
    file_bytes,
    file_type=None
):
    """
    上传知识库文件到 Supabase Storage。

    注意：
    - 数据库保存原始中文文件名
    - Storage 使用安全文件名
    """

    if not file_bytes:
        return {
            "success": False,
            "message": "文件内容为空"
        }

    suffix = Path(file_name).suffix.lower()

    file_hash = calculate_file_hash(file_bytes)

    # ========================================================
    # 检查重复文件
    # ========================================================

    try:
        existing = (
            supabase
            .table("knowledge_documents")
            .select("*")
            .eq("user_id", USER_ID)
            .eq("file_hash", file_hash)
            .execute()
        )

        if existing.data:
            return {
                "success": True,
                "duplicate": True,
                "message": "文件已经存在",
                "document": existing.data[0]
            }

    except Exception as e:
        print(f"⚠️ 检查重复文件失败：{e}")


    # ========================================================
    # 生成安全 Storage 文件名
    # ========================================================

    safe_filename = make_safe_storage_filename(
        file_name,
        file_hash
    )

    storage_path = f"{USER_ID}/{safe_filename}"


    # ========================================================
    # MIME 类型
    # ========================================================

    if suffix == ".pdf":
        content_type = "application/pdf"
    elif suffix == ".txt":
        content_type = "text/plain"
    else:
        content_type = file_type or "application/octet-stream"


    # ========================================================
    # Storage 上传
    # ========================================================

    upload_success = False
    last_error = None

    for attempt in range(1, 5):

        try:

            print(
                f"☁️ Storage 上传 {attempt}/4："
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

            print(f"✅ Storage 上传成功：{result}")

            upload_success = True
            break

        except Exception as e:

            last_error = e

            print(
                f"⚠️ 第 {attempt} 次上传失败：{e}"
            )

            if attempt < 4:
                time.sleep(3)


    # ========================================================
    # 上传失败
    # ========================================================

    if not upload_success:

        return {
            "success": False,
            "message": f"Storage 上传失败：{last_error}"
        }


    # ========================================================
    # 写入数据库
    # ========================================================

    document_data = {
        "user_id": USER_ID,

        # 数据库保存用户原始文件名
        "file_name": file_name,

        "file_path": file_name,

        "file_type": suffix,

        "file_size": len(file_bytes),

        "file_hash": file_hash,

        # Storage 保存安全路径
        "storage_path": storage_path,

        "chunk_count": 0,

        "status": "uploaded",
    }


    try:

        result = (
            supabase
            .table("knowledge_documents")
            .insert(document_data)
            .execute()
        )

        print("✅ 数据库记录创建成功")

        return {
            "success": True,
            "duplicate": False,
            "message": "知识库文件上传成功",
            "document": result.data[0] if result.data else document_data
        }


    except Exception as e:

        print(
            f"❌ 数据库写入失败：{e}"
        )

        # ====================================================
        # 数据库失败 → 删除 Storage 文件
        # ====================================================

        try:

            supabase.storage.from_(BUCKET_NAME).remove(
                [storage_path]
            )

            print(
                "↩️ 已回滚 Storage 文件"
            )

        except Exception as rollback_error:

            print(
                f"⚠️ Storage 回滚失败：{rollback_error}"
            )


        return {
            "success": False,
            "message": f"数据库记录失败：{e}"
        }


# ============================================================
# 获取知识库文件列表
# ============================================================

def list_knowledge_documents():

    try:

        result = (
            supabase
            .table("knowledge_documents")
            .select("*")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
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

def delete_knowledge_document(document_id):

    try:

        # ----------------------------------------------------
        # 找数据库记录
        # ----------------------------------------------------

        result = (
            supabase
            .table("knowledge_documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", USER_ID)
            .single()
            .execute()
        )

        document = result.data

        if not document:

            return {
                "success": False,
                "message": "找不到知识库文件"
            }


        storage_path = document.get("storage_path")


        # ----------------------------------------------------
        # 删除 Storage
        # ----------------------------------------------------

        if storage_path:

            try:

                supabase.storage.from_(BUCKET_NAME).remove(
                    [storage_path]
                )

            except Exception as e:

                print(
                    f"⚠️ Storage 删除失败：{e}"
                )


        # ----------------------------------------------------
        # 删除数据库记录
        # ----------------------------------------------------

        (
            supabase
            .table("knowledge_documents")
            .delete()
            .eq("id", document_id)
            .eq("user_id", USER_ID)
            .execute()
        )


        return {
            "success": True,
            "message": "知识库文件删除成功"
        }


    except Exception as e:

        return {
            "success": False,
            "message": f"删除失败：{e}"
        }


# ============================================================
# 下载知识库文件
# ============================================================

def download_knowledge_file(storage_path):

    try:

        data = (
            supabase
            .storage
            .from_(BUCKET_NAME)
            .download(storage_path)
        )

        return data

    except Exception as e:

        print(
            f"❌ 下载知识库文件失败：{e}"
        )

        return None


# ============================================================
# 获取知识库数量
# ============================================================

def get_knowledge_count():

    try:

        result = (
            supabase
            .table("knowledge_documents")
            .select("id")
            .eq("user_id", USER_ID)
            .execute()
        )

        return len(result.data or [])

    except Exception as e:

        print(
            f"❌ 获取知识库数量失败：{e}"
        )

        return 0