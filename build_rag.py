import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import os
import shutil
from pathlib import Path

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


# =========================================================
# 基础配置
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "software_engineer_notes"

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"

# 每个文本块的大致长度
CHUNK_SIZE = 800

# 文本块之间保留一定重叠，避免知识被切断
CHUNK_OVERLAP = 100


# =========================================================
# 读取 PDF
# =========================================================

def read_pdf(file_path):
    print(f"📄 正在读取 PDF：{file_path.name}")

    reader = PdfReader(str(file_path))

    pages = []

    for page_index, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            print(f"   ⚠️ 第 {page_index + 1} 页读取失败：{e}")
            text = ""

        text = text.strip()

        if text:
            pages.append(
                f"【第{page_index + 1}页】\n{text}"
            )

    return "\n\n".join(pages)


# =========================================================
# 读取 TXT
# =========================================================

def read_txt(file_path):
    print(f"📝 正在读取 TXT：{file_path.name}")

    encodings = [
        "utf-8",
        "utf-8-sig",
        "gb18030",
        "gbk",
    ]

    for encoding in encodings:
        try:
            return file_path.read_text(
                encoding=encoding
            )
        except UnicodeDecodeError:
            continue

    raise RuntimeError(
        f"无法识别文件编码：{file_path.name}"
    )


# =========================================================
# 自动读取所有资料
# =========================================================

def load_all_documents():
    documents = []

    if not KNOWLEDGE_DIR.exists():
        KNOWLEDGE_DIR.mkdir(parents=True)

    files = []

    # PDF
    files.extend(
        KNOWLEDGE_DIR.rglob("*.pdf")
    )

    # TXT
    files.extend(
        KNOWLEDGE_DIR.rglob("*.txt")
    )

    # 大小写扩展名兼容
    files.extend(
        KNOWLEDGE_DIR.rglob("*.PDF")
    )

    files.extend(
        KNOWLEDGE_DIR.rglob("*.TXT")
    )

    # 去重
    files = sorted(
        set(files),
        key=lambda x: str(x).lower()
    )

    if not files:
        print("⚠️ knowledge 文件夹中没有 PDF/TXT 文件")
        return documents

    print()
    print("=" * 60)
    print(f"📚 发现 {len(files)} 个知识库文件")
    print("=" * 60)

    for file_path in files:

        try:

            suffix = file_path.suffix.lower()

            if suffix == ".pdf":
                text = read_pdf(file_path)

            elif suffix == ".txt":
                text = read_txt(file_path)

            else:
                continue

            if not text.strip():
                print(
                    f"   ⚠️ 文件没有读取到有效文本：{file_path.name}"
                )
                continue

            documents.append(
                {
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "text": text,
                }
            )

            print(
                f"   ✅ {file_path.name} "
                f"({len(text):,} 字符)"
            )

        except Exception as e:

            print(
                f"   ❌ {file_path.name} 读取失败：{e}"
            )

    return documents


# =========================================================
# 文本切分
# =========================================================

def split_text(text, chunk_size=CHUNK_SIZE):
    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - CHUNK_OVERLAP

    return chunks


# =========================================================
# 构建知识块
# =========================================================

def build_chunks(documents):

    all_chunks = []
    all_metadatas = []

    chunk_id = 0

    print()
    print("=" * 60)
    print("✂️ 开始切分知识")
    print("=" * 60)

    for document in documents:

        file_name = document["file_name"]
        text = document["text"]

        chunks = split_text(text)

        print(
            f"📚 {file_name}: "
            f"{len(chunks)} 个知识块"
        )

        for index, chunk in enumerate(chunks):

            all_chunks.append(chunk)

            all_metadatas.append(
                {
                    "source": file_name,
                    "chunk_index": index,
                }
            )

            chunk_id += 1

    print()
    print(f"📦 总知识块数量：{len(all_chunks)}")

    return all_chunks, all_metadatas


# =========================================================
# 构建 ChromaDB
# =========================================================

def build_chroma(chunks, metadatas):

    print()
    print("=" * 60)
    print("🧠 加载 BGE Embedding 模型")
    print("=" * 60)

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )

    print("✅ Embedding 模型加载完成")

    print()
    print("=" * 60)
    print("🗄️ 初始化 ChromaDB")
    print("=" * 60)

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    # 删除旧集合
    try:
        client.delete_collection(
            COLLECTION_NAME
        )

        print("🗑️ 已删除旧知识库")

    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME
    )

    # 分批生成 embedding
    batch_size = 64

    total = len(chunks)

    for start in range(
        0,
        total,
        batch_size
    ):

        end = min(
            start + batch_size,
            total
        )

        batch_chunks = chunks[start:end]

        print(
            f"🔄 Embedding："
            f"{end}/{total}"
        )

        embeddings = model.encode(
            batch_chunks,
            normalize_embeddings=True
        ).tolist()

        ids = [
            f"chunk_{i}"
            for i in range(start, end)
        ]

        collection.add(
            ids=ids,
            documents=batch_chunks,
            embeddings=embeddings,
            metadatas=metadatas[start:end]
        )

    print()
    print("=" * 60)
    print("🎉 知识库构建完成")
    print("=" * 60)

    file_count = len(set(m["source"] for m in metadatas))

    print(f"📚 文件数量：{file_count}")
    print(
        f"📦 知识块数量：{len(chunks)}"
    )

    print(
        f"🗄️ ChromaDB：{CHROMA_DIR}"
    )


# =========================================================
# 主程序
# =========================================================

def main():

    print()
    print("=" * 60)
    print("🚀 软件设计师 AI Agent - 多资料 RAG 构建器")
    print("=" * 60)

    print()
    print(f"📂 知识库目录：{KNOWLEDGE_DIR}")

    documents = load_all_documents()

    if not documents:
        print()
        print("❌ 没有可用知识文件")
        return

    chunks, metadatas = build_chunks(
        documents
    )

    if not chunks:
        print()
        print("❌ 没有生成任何知识块")
        return

    build_chroma(
        chunks,
        metadatas
    )


if __name__ == "__main__":
    main()