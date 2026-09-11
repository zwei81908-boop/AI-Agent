import re
import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

PDF_PATH = "软件设计师笔记—作者：rDawn.pdf"
DB_PATH = "./chroma_db"

print("正在加载向量模型...")
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
print("向量模型加载完成")

print("正在读取 PDF...")
reader = PdfReader(PDF_PATH)

# =========================
# 1. 按页面读取 PDF
# =========================

pages = []

for page_number, page in enumerate(reader.pages, start=1):

    text = page.extract_text()

    if not text:
        continue

    pages.append({
        "page": page_number,
        "text": text
    })

print("PDF读取完成")
print("有效页面数量：", len(pages))


# =========================
# 2. 识别章节标题
# =========================

section_pattern = re.compile(
    r"^(\d+(?:\.\d+)*\.)\s*(.+)$"
)

chunks = []

current_section = "未分类"
current_section_number = ""

chunk_index = 0

for page_data in pages:

    page_number = page_data["page"]
    text = page_data["text"]

    lines = text.splitlines()

    current_text = ""

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # 排除 PDF 页码
        if re.match(r"^No\.\s*\d+\s*/\s*\d+$", line):
            continue

        # 判断是不是章节标题
        match = section_pattern.match(line)

        if match:

            # 先保存之前的内容
            if current_text.strip():

                chunks.append({
                    "text": current_text.strip(),
                    "page": page_number,
                    "section": current_section,
                    "section_number": current_section_number
                })

                chunk_index += 1

                current_text = ""

            current_section_number = match.group(1)
            current_section = match.group(2).strip()

            current_text += line + "\n"

        else:

            current_text += line + "\n"


    # 保存页面剩余内容
    if current_text.strip():

        chunks.append({
            "text": current_text.strip(),
            "page": page_number,
            "section": current_section,
            "section_number": current_section_number
        })


# =========================
# 3. 对过长知识片段再次切分
# =========================

final_chunks = []

max_length = 800
overlap = 100

for item in chunks:

    text = item["text"]

    if len(text) <= max_length:

        final_chunks.append(item)

    else:

        start = 0

        while start < len(text):

            end = start + max_length

            chunk_text = text[start:end].strip()

            if chunk_text:

                final_chunks.append({
                    "text": chunk_text,
                    "page": item["page"],
                    "section": item["section"],
                    "section_number": item["section_number"]
                })

            start = end - overlap


print("知识切分完成")
print("知识片段数量：", len(final_chunks))


# =========================
# 4. 创建新的 ChromaDB
# =========================

print("正在创建向量数据库...")

client = chromadb.PersistentClient(
    path=DB_PATH
)

# 删除旧知识库
try:
    client.delete_collection(
        name="software_engineer_notes"
    )
    print("旧知识库已删除")
except Exception:
    pass

collection = client.get_or_create_collection(
    name="software_engineer_notes"
)


# =========================
# 5. 准备数据
# =========================

documents = [
    item["text"]
    for item in final_chunks
]

metadatas = [
    {
        "page": item["page"],
        "section": item["section"],
        "section_number": item["section_number"]
    }
    for item in final_chunks
]

ids = [
    f"chunk_{i}"
    for i in range(len(final_chunks))
]


# =========================
# 6. 向量化
# =========================

print("正在进行向量化，请稍等...")

embeddings = model.encode(
    documents,
    normalize_embeddings=True,
    show_progress_bar=True
)

print("向量化完成")


# =========================
# 7. 写入 ChromaDB
# =========================

collection.upsert(
    ids=ids,
    documents=documents,
    embeddings=embeddings.tolist(),
    metadatas=metadatas
)


print()
print("================================")
print("RAG知识库创建成功！")
print("知识片段数量：", collection.count())
print("数据库位置：", DB_PATH)
print("================================")