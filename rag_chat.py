import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# =========================
# 1. DeepSeek
# =========================

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


# =========================
# 2. 加载向量模型
# =========================

print("正在加载向量模型...")

model = SentenceTransformer(
    "BAAI/bge-small-zh-v1.5"
)

print("向量模型加载完成")


# =========================
# 3. 加载知识库
# =========================

chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_collection(
    name="software_engineer_notes"
)

print("知识库加载成功")
print("知识片段数量：", collection.count())


# =========================
# 4. 开始聊天
# =========================

while True:

    question = input("\n请输入你的问题（输入 q 退出）：")

    if question.lower() == "q":
        print("程序结束")
        break


    # =========================
    # 5. 把问题转换成向量
    # =========================

    question_embedding = model.encode(
        question,
        normalize_embeddings=True
    ).tolist()


    # =========================
    # 6. 从知识库检索
    # =========================

    results = collection.query(
    query_embeddings=[question_embedding],
    n_results=8,
    include=["documents", "metadatas", "distances"]
)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]


    # =========================
    # 7. 显示检索结果
    # =========================

    print("\n========== 检索到的知识 ==========")

    for i, (doc, metadata, distance) in enumerate(
    zip(documents, metadatas, distances)
):

        print(
            f"\n--- 知识片段 {i + 1} ---"
        )

        print(
            f"章节：{metadata.get('section_number', '')} "
            f"{metadata.get('section', '')}"
        )

        print(
            f"页码：第 {metadata.get('page', '?')} 页"
        )
        print(
        f"相似度距离：{distance:.4f}"
        )

        print(doc)


    # =========================
    # 8. 整理知识库内容
    # =========================

    context_parts = []

    for doc, metadata in zip(
        documents,
        metadatas
    ):

        section_number = metadata.get(
            "section_number",
            ""
        )

        section = metadata.get(
            "section",
            ""
        )

        page = metadata.get(
            "page",
            "?"
        )

        context_parts.append(
            f"""
【章节】
{section_number} {section}

【页码】
第 {page} 页

【知识内容】
{doc}
"""
        )

    context = "\n\n".join(
        context_parts
    )


    # =========================
    # 9. 让 DeepSeek 回答
    # =========================

    prompt = f"""
你是一个软件设计师考试 AI 学习助手。

请严格根据下面提供的知识库内容回答问题。

不要凭空编造知识库中没有的信息。

如果知识库没有足够的信息，请明确回答：

“知识库中没有找到足够的信息。”

回答格式必须是：

【知识点】
用一句话说明这个知识点。

【通俗解释】
用初学者容易理解的方式解释。

【考试重点】
告诉我这个知识点考试时重点记什么。

【知识库依据】
说明答案来自知识库中的哪些内容。

【记忆方法】
给出一个简单好记的记忆方法。

最后，如果知识库中提供了章节和页码，请告诉我相关位置。

====================
知识库内容
====================

{context}

====================
用户问题
====================

{question}
"""


    response = client.chat.completions.create(
        model="deepseek-chat",

        messages=[
            {
                "role": "system",
                "content": "你是一个严谨的软件设计师考试学习助手。"
            },

            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.2
    )


    # =========================
    # 10. 输出 AI 回答
    # =========================

    answer = response.choices[0].message.content

    print("\n========== AI回答 ==========")

    print(answer)


    # =========================
    # 11. 显示来源
    # =========================

    print("\n========== 知识来源 ==========")

    for i, metadata in enumerate(metadatas):

        print(
            f"{i + 1}. "
            f"{metadata.get('section_number', '')} "
            f"{metadata.get('section', '')} "
            f"（第 {metadata.get('page', '?')} 页）"
        )