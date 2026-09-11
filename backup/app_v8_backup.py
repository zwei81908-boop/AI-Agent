import streamlit as st
import subprocess
import sys
import os

# =========================
# 页面配置
# =========================

st.set_page_config(
    page_title="软件设计师 AI Agent",
    page_icon="🤖",
    layout="wide"
)

# =========================
# 标题
# =========================

st.title("🤖 软件设计师 AI 自适应学习 Agent")
st.caption("RAG + DeepSeek + 错题复习 + 自适应学习")

# =========================
# 侧边栏
# =========================

st.sidebar.title("📚 学习中心")

menu = st.sidebar.radio(
    "选择功能",
    [
        "🏠 首页",
        "📋 今日任务",
        "📝 专项训练",
        "❌ 错题复习",
        "🧠 自适应分析",
        "📊 学习报告",
        "💬 AI 知识问答"
    ]
)

# =========================
# 数据文件
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WRONG_FILE = os.path.join(
    BASE_DIR,
    "wrong_questions.json"
)

RECORD_FILE = os.path.join(
    BASE_DIR,
    "learning_records.json"
)

TASK_FILE = os.path.join(
    BASE_DIR,
    "daily_tasks.json"
)


def read_json(path):
    import json

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# =========================
# 首页
# =========================

if menu == "🏠 首页":

    st.header("欢迎使用 AI 学习 Agent")

    col1, col2, col3, col4 = st.columns(4)

    wrong = read_json(WRONG_FILE)
    records = read_json(RECORD_FILE)
    tasks = read_json(TASK_FILE)

    with col1:
        st.metric(
            "❌ 当前错题",
            len(wrong)
        )

    with col2:
        st.metric(
            "📚 学习记录",
            len(records)
        )

    with col3:
        st.metric(
            "📋 学习任务",
            len(tasks)
        )

    with col4:
        st.metric(
            "🤖 Agent",
            "运行中"
        )

    st.divider()

    st.subheader("🚀 核心能力")

    abilities = [
        "RAG 知识库问答",
        "AI 自动出题",
        "自动批改",
        "错题自动保存",
        "错题间隔复习",
        "自适应学习分析",
        "动态学习计划",
        "每日学习报告"
    ]

    for item in abilities:
        st.write("✅ " + item)


# =========================
# 今日任务
# =========================

elif menu == "📋 今日任务":

    st.header("📋 今日学习任务")

    if st.button("🔄 生成 / 更新今日计划"):

        result = subprocess.run(
            [
                sys.executable,
                "agent.py"
            ],
            input="制定今天的学习计划\nexit\n",
            text=True,
            capture_output=True,
            cwd=BASE_DIR
        )

        st.text(result.stdout)

    tasks = read_json(TASK_FILE)

    if tasks:

        st.subheader("今日任务")

        for i, task in enumerate(tasks, 1):

            if isinstance(task, dict):

                title = task.get(
                    "task",
                    task.get("title", f"任务 {i}")
                )

                duration = task.get(
                    "duration",
                    ""
                )

                st.write(
                    f"**{i}. {title}** {duration}"
                )

            else:
                st.write(
                    f"**{i}. {task}**"
                )

    else:

        st.info(
            "暂时没有读取到今日任务。"
        )


# =========================
# 专项训练
# =========================

elif menu == "📝 专项训练":

    st.header("📝 专项训练")

    st.write(
        "点击下面按钮启动 AI 专项训练。"
    )

    if st.button("🚀 开始专项训练"):

        st.info(
            "专项训练将在命令行 Agent 中启动。"
        )

        st.code(
            "开始专项训练"
        )


# =========================
# 错题复习
# =========================

elif menu == "❌ 错题复习":

    st.header("❌ 错题复习")

    wrong = read_json(WRONG_FILE)

    st.metric(
        "当前错题数量",
        len(wrong)
    )

    if wrong:

        for i, item in enumerate(
            wrong,
            1
        ):

            if isinstance(item, dict):

                question = item.get(
                    "question",
                    "未知题目"
                )

                knowledge = item.get(
                    "knowledge_point",
                    "未知知识点"
                )

                st.write(
                    f"### {i}. {knowledge}"
                )

                st.write(question)

    else:

        st.success(
            "🎉 当前没有错题！"
        )


# =========================
# 自适应分析
# =========================

elif menu == "🧠 自适应分析":

    st.header("🧠 AI 自适应分析")

    if st.button("🔍 开始分析"):

        result = subprocess.run(
            [
                sys.executable,
                "agent.py"
            ],
            input="自适应分析\nexit\n",
            text=True,
            capture_output=True,
            cwd=BASE_DIR
        )

        st.text(result.stdout)


# =========================
# 学习报告
# =========================

elif menu == "📊 学习报告":

    st.header("📊 AI 学习报告")

    if st.button("📈 生成学习报告"):

        result = subprocess.run(
            [
                sys.executable,
                "agent.py"
            ],
            input="学习报告\nexit\n",
            text=True,
            capture_output=True,
            cwd=BASE_DIR
        )

        st.text(result.stdout)


# =========================
# AI 知识问答
# =========================

elif menu == "💬 AI 知识问答":

    st.header("💬 AI 知识问答")

    question = st.text_area(
        "请输入你的问题",
        placeholder="例如：什么是结构化方法？"
    )

    if st.button("🤖 询问 AI"):

        if question.strip():

            with st.spinner(
                "AI 正在思考..."
            ):

                result = subprocess.run(
                    [
                        sys.executable,
                        "agent.py"
                    ],
                    input=f"{question}\nexit\n",
                    text=True,
                    capture_output=True,
                    cwd=BASE_DIR
                )

            st.markdown(
                result.stdout
            )

        else:

            st.warning(
                "请输入问题。"
            )