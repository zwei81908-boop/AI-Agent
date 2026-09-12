import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

import chromadb


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "software_engineer_notes"

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


def get_knowledge_files():
    """扫描 knowledge 目录下所有 PDF / TXT。"""
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    files = []

    for path in KNOWLEDGE_DIR.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        files.append(path)

    return sorted(files, key=lambda x: x.name.lower())


def get_file_info(path):
    """获取文件基本信息。"""
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


def get_chroma_status():
    """获取 ChromaDB 状态。"""
    if not CHROMA_DIR.exists():
        return {
            "exists": False,
            "documents": 0,
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
                "documents": 0,
            }

        return {
            "exists": True,
            "documents": target.count(),
        }

    except Exception as e:
        return {
            "exists": False,
            "documents": 0,
            "error": str(e),
        }


def save_uploaded_file(uploaded_file):
    """
    保存 Streamlit 上传的 PDF/TXT。
    返回：
        success, message, path
    """

    if uploaded_file is None:
        return False, "没有选择文件", None

    filename = Path(uploaded_file.name).name
    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        return (
            False,
            "只支持 PDF 和 TXT 文件",
            None,
        )

    KNOWLEDGE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    target_path = KNOWLEDGE_DIR / filename

    try:
        with open(target_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return (
            True,
            f"文件已保存：{filename}",
            target_path,
        )

    except Exception as e:
        return (
            False,
            f"保存失败：{e}",
            None,
        )


def rebuild_knowledge_base():
    """
    调用 build_rag.py 重新构建知识库。
    """

    build_script = BASE_DIR / "build_rag.py"

    if not build_script.exists():
        return {
            "success": False,
            "output": "找不到 build_rag.py",
        }

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(build_script),
            ],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )

        output = (
            result.stdout
            + "\n"
            + result.stderr
        )

        return {
            "success": result.returncode == 0,
            "output": output,
            "returncode": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "知识库构建超过 10 分钟，已停止。",
        }

    except Exception as e:
        return {
            "success": False,
            "output": f"构建失败：{e}",
        }


def print_report():
    print()
    print("=" * 65)
    print("📚 AI Agent 知识库状态")
    print("=" * 65)

    files = get_knowledge_files()

    print(f"📂 知识库目录：{KNOWLEDGE_DIR}")
    print(f"📄 资料数量：{len(files)}")

    if files:
        print("-" * 65)

        for index, path in enumerate(files, 1):
            info = get_file_info(path)

            print(f"{index}. {info['name']}")
            print(f"   类型：{info['suffix'].upper()}")
            print(f"   大小：{info['size_mb']} MB")
            print(f"   修改时间：{info['modified']}")

    status = get_chroma_status()

    print("-" * 65)

    if status["exists"]:
        print("🟢 ChromaDB：正常")
        print(
            f"📦 知识块数量：{status['documents']}"
        )
    else:
        print("🔴 ChromaDB：未找到知识库")

        if "error" in status:
            print(f"错误：{status['error']}")

    print("=" * 65)


if __name__ == "__main__":
    print_report()