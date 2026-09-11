from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
import os

# =========================
# 读取 .env
# =========================
load_dotenv()

# =========================
# 创建 DeepSeek 客户端
# =========================
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)


# =========================
# 读取 PDF
# =========================
def read_pdf(filename):
    reader = PdfReader(filename)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


# =========================
# PDF 文件
# =========================
pdf_file = "软件设计师笔记—作者：rDawn.pdf"

print("正在读取 PDF...")

pdf_text = read_pdf(pdf_file)

print("PDF 读取完成！")
print("文字长度：", len(pdf_text))

# 暂时限制长度
pdf_text = pdf_text[:20000]


# =========================
# 开始问答
# =========================
while True:

    question = input("\n请输入你的问题（输入 q 退出）：")

    if question.lower() == "q":
        print("程序结束！")
        break

    prompt = f"""
你是一名专业的软件设计师考试辅导老师。

请严格根据下面这份 PDF 笔记回答问题。

【PDF内容】
{pdf_text}

【用户问题】
{question}

要求：

1. 优先根据 PDF 内容回答
2. 如果 PDF 中没有明确答案，请告诉用户
3. 用通俗易懂的中文解释
4. 如果适合考试，请告诉我考试时应该怎么记
5. 可以举一个简单例子帮助理解
"""

    print("\nAI 正在思考...\n")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    answer = response.choices[0].message.content

    print("================================")
    print("AI回答：")
    print(answer)
    print("================================")