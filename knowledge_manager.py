import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import chromadb

BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "software_engineer_notes"


# =========================================================
# 本地知识库文件
# =========================================================

def get_knowledge_files():
    if not KNOWLEDGE_DIR.exists():
        return []

    files = []

    for path in KNOWLEDGE_DIR.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in [".pdf", ".txt"]:
            continue

        files.append(path)

    return sorted(files, key=lambda x: x.name.lower())


def get_file_info(path):
    stat = path.stat()

    return {
        "name": path.name,
        "path": str(path),
        "suffix": path.suffix.lower(),
        "size": stat.st_size,
        "size_mb": round(stat.st_size / 1024 / 1024, 2),
        "modified": datetime.fromtimestamp(
            stat.st_mtime
        ).strftime("%Y-%m-%d %H:%M:%S"),
    }


# =========================================================
# ChromaDB
# =========================================================

def get_chroma_status():

    if not CHROMA_DIR.exists():
        return {
            "exists": False,
            "documents": 0
        }

    try:

        client = chromadb.PersistentClient(
            path=str(CHROMA_DIR)
        )

        collections = client.list_collections()

        target = None

        for collection in collections:

            name = (
                collection.name
                if hasattr(collection, "name")
                else str(collection)
            )

            if name == COLLECTION_NAME:

                target = client.get_collection(
                    COLLECTION_NAME
                )

                break

        if target is None:

            return {
                "exists": False,
                "documents": 0
            }

        return {
            "exists": True,
            "documents": target.count()
        }

    except Exception as e:

        return {
            "exists": False,
            "documents": 0,
            "error": str(e)
        }


# =========================================================
# 本地上传
# =========================================================

def save_uploaded_file(uploaded_file):

    KNOWLEDGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = KNOWLEDGE_DIR / uploaded_file.name

    with open(file_path, "wb") as f:

        f.write(
            uploaded_file.getbuffer()
        )

    return file_path


# =========================================================
# 云端知识库 V21
# =========================================================

def upload_to_cloud(file_name, file_bytes):

    from cloud_knowledge import upload_knowledge_file

    suffix = Path(file_name).suffix.lower()

    return upload_knowledge_file(
        file_name=file_name,
        file_bytes=file_bytes,
        file_type=suffix
    )


def get_cloud_knowledge_files():

    from cloud_knowledge import list_knowledge_documents

    return list_knowledge_documents()


def delete_cloud_knowledge_file(document_id):

    from cloud_knowledge import delete_knowledge_document

    return delete_knowledge_document(
        document_id
    )


def get_cloud_knowledge_count():

    from cloud_knowledge import get_knowledge_count

    return get_knowledge_count()


# =========================================================
# V20 本地 RAG 构建
# =========================================================

def rebuild_knowledge_base():

    build_script = BASE_DIR / "build_rag.py"

    if not build_script.exists():

        return {
            "success": False,
            "message": "找不到 build_rag.py"
        }

    try:

        env = os.environ.copy()

        env["PYTHONIOENCODING"] = "utf-8"

        result = subprocess.run(
            [
                sys.executable,
                str(build_script)
            ],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        if result.returncode == 0:

            return {
                "success": True,
                "message": "知识库构建完成",
                "output": result.stdout
            }

        return {
            "success": False,
            "message": "知识库构建失败",
            "output": (
                result.stdout
                + "\n"
                + result.stderr
            )
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }


# =========================================================
# 控制台状态报告
# =========================================================

def print_report():

    print()
    print("=" * 65)
    print("📚 AI Agent 知识库状态")
    print("=" * 65)

    files = get_knowledge_files()

    print(
        f"📂 知识库目录：{KNOWLEDGE_DIR}"
    )

    print(
        f"📄 资料数量：{len(files)}"
    )

    if files:

        print("-" * 65)

        for index, path in enumerate(
            files,
            1
        ):

            info = get_file_info(path)

            print(
                f"{index}. {info['name']}"
            )

            print(
                f"   类型：{info['suffix'].upper()}"
            )

            print(
                f"   大小：{info['size_mb']} MB"
            )

            print(
                f"   修改时间：{info['modified']}"
            )

    status = get_chroma_status()

    print("-" * 65)

    if status["exists"]:

        print("🟢 ChromaDB：正常")

        print(
            f"📦 知识块数量：{status['documents']}"
        )

    else:

        print(
            "🔴 ChromaDB：未找到知识库"
        )

        if "error" in status:

            print(
                f"错误：{status['error']}"
            )

    print("=" * 65)


if __name__ == "__main__":

    print_report()