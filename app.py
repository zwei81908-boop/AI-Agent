import os
from datetime import date

import streamlit as st

import agent
# ============================================================
# V23：切换到 Supabase 云端 RAG
# ============================================================

try:
    import cloud_rag

    agent.search_knowledge = cloud_rag.search_knowledge

    CLOUD_RAG_READY = True

except Exception as e:

    CLOUD_RAG_READY = False
    CLOUD_RAG_ERROR = str(e)
# =========================================================
# V19 知识库管理
# =========================================================

from knowledge_manager import (
    get_knowledge_files,
    get_file_info,
    get_chroma_status,
)


# =========================================================
# 云端数据库
# =========================================================

try:
    from database import (
        save_learning_record,
        save_wrong_question as save_cloud_wrong_question,
        get_learning_records as get_cloud_learning_records,
        get_wrong_questions as get_cloud_wrong_questions,
        save_daily_task,
        get_daily_tasks as get_cloud_daily_tasks,
        complete_daily_task,
    )

    CLOUD_DB_READY = True

except Exception as e:

    CLOUD_DB_READY = False
    CLOUD_DB_ERROR = str(e)


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# =========================================================
# 云端读取缓存
# =========================================================

@st.cache_data(
    ttl=30,
    show_spinner=False
)
def cached_learning_records():

    if not CLOUD_DB_READY:
        return []

    return get_cloud_learning_records(500)


@st.cache_data(
    ttl=30,
    show_spinner=False
)
def cached_wrong_questions():

    if not CLOUD_DB_READY:
        return []

    return get_cloud_wrong_questions(500)


@st.cache_data(
    ttl=30,
    show_spinner=False
)
def cached_daily_tasks(task_date):

    if not CLOUD_DB_READY:
        return []

    return get_cloud_daily_tasks(task_date)


def clear_cloud_cache():

    cached_learning_records.clear()
    cached_wrong_questions.clear()
    cached_daily_tasks.clear()


# =========================================================
# Streamlit 页面配置
# =========================================================

st.set_page_config(
    page_title="软件设计师 AI 自适应学习 Agent",
    page_icon="🤖",
    layout="wide",
)


# =========================================================
# 页面样式
# =========================================================

st.markdown(
    """
<style>

.stApp {
    background: linear-gradient(
        180deg,
        #f7fbff 0%,
        #eef5fb 100%
    );
    color: #18324f;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    color: #163b68 !important;
}

h1 {
    font-weight: 800;
}

.hero {
    padding: 24px 28px;
    border-radius: 18px;
    border: 1px solid #d7e8f8;
    background: linear-gradient(
        120deg,
        #eaf6ff 0%,
        #ffffff 58%,
        #eaf3ff 100%
    );
    box-shadow: 0 8px 28px rgba(
        37,
        99,
        155,
        .08
    );
    margin-bottom: 18px;
}

.hero-title {
    font-size: 30px;
    font-weight: 800;
    color: #173d6b;
    margin-bottom: 8px;
}

.hero-sub {
    color: #607d9d;
    font-size: 15px;
}

.tech-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid #ccebdd;
    background: #f0fbf6;
    color: #169b69;
    font-size: 13px;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #ffffff 0%,
        #f4f9fe 100%
    );
    border-right: 1px solid #dbe8f4;
}

section[data-testid="stSidebar"] * {
    color: #315273 !important;
}

section[data-testid="stSidebar"] .stRadio label {
    border-radius: 10px;
    padding: 7px 10px;
}

section[data-testid="stSidebar"]
.stRadio label:hover {
    background: #eaf4ff;
}

div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #dceaf6;
    border-radius: 14px;
    padding: 14px;
    box-shadow: 0 6px 20px rgba(
        41,
        94,
        145,
        .07
    );
}

div[data-testid="stMetricLabel"] {
    color: #6885a3 !important;
}

div[data-testid="stMetricValue"] {
    color: #173f70 !important;
}

div[data-testid="stExpander"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid #dceaf6;
    border-radius: 14px;
    background: rgba(
        255,
        255,
        255,
        .94
    );
    box-shadow: 0 5px 18px rgba(
        41,
        94,
        145,
        .05
    );
}

textarea,
input {
    background: #ffffff !important;
    color: #18324f !important;
    border: 1px solid #cfe0ee !important;
    border-radius: 10px !important;
}

.stButton > button {
    border-radius: 10px;
    border: 1px solid #bdd7ee;
    background: linear-gradient(
        135deg,
        #287fe0,
        #1765b6
    );
    color: white;
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(
        37,
        113,
        190,
        .14
    );
}

.stButton > button:hover {
    border-color: #76b4ea;
    box-shadow: 0 6px 16px rgba(
        37,
        113,
        190,
        .22
    );
}

div[data-testid="stDataFrame"] {
    border: 1px solid #dceaf6;
    border-radius: 12px;
    overflow: hidden;
}

hr {
    border-color: #dce8f2 !important;
}

</style>
""",
    unsafe_allow_html=True,
)


# =========================================================
# 顶部 Hero
# =========================================================

st.markdown(
    """
    <div class="hero-sub">
        AI 个性化学习系统 · 智能出题 · 错题复习 ·
        RAG 知识库 · 云端数据
    </div>
    """,
    unsafe_allow_html=True
)

st.caption(
    "AI 驱动的软件设计师学习工作台"
)


# =========================================================
# 云端状态
# =========================================================

def cloud_status():

    if CLOUD_DB_READY:
        return "🟢 云端数据库已连接"

    return (
        f"🟡 云端数据库暂不可用："
        f"{CLOUD_DB_ERROR}"
    )


# =========================================================
# V19：知识库状态
# =========================================================

def render_knowledge_status():

    try:

        files = get_knowledge_files()
        status = get_chroma_status()

        st.sidebar.markdown("---")

        st.sidebar.subheader(
            "📚 知识库"
        )

        if status.get("exists"):

            st.sidebar.success(
                "🟢 知识库正常"
            )

            st.sidebar.caption(
                f"知识块："
                f"{status.get('documents', 0)}"
            )

        else:

            st.sidebar.error(
                "🔴 知识库异常"
            )

        st.sidebar.caption(
            f"资料数量：{len(files)}"
        )

        with st.sidebar.expander(
            "查看资料"
        ):

            if not files:

                st.write(
                    "暂无 PDF/TXT"
                )

            else:

                for path in files:

                    info = get_file_info(
                        path
                    )

                    st.write(
                        f"**{info['name']}**"
                    )

                    st.caption(
                        f"{info['size_mb']} MB · "
                        f"{info['modified']}"
                    )

    except Exception as e:

        st.sidebar.error(
            f"知识库状态读取失败：{e}"
        )


# =========================================================
# 云端学习记录同步
# =========================================================

def sync_learning_record(
    q,
    user_answer,
    is_correct,
    mode
):

    if not CLOUD_DB_READY:
        return

    try:

        save_learning_record(
            topic=q.get(
                "knowledge_point",
                q.get(
                    "topic",
                    "未分类"
                )
            ),

            question=q.get(
                "question",
                ""
            ),

            answer=user_answer,

            is_correct=bool(
                is_correct
            ),

            score=(
                100
                if is_correct
                else 0
            ),
        )

    except Exception as e:

        st.warning(
            f"学习记录云端同步失败：{e}"
        )

    else:

        cached_learning_records.clear()

        st.session_state[
            "_cloud_hydrated"
        ] = False


# =========================================================
# 云端错题同步
# =========================================================

def sync_wrong_question(
    q,
    user_answer
):

    if not CLOUD_DB_READY:
        return

    try:

        save_cloud_wrong_question(

            question=q.get(
                "question",
                ""
            ),

            options=[
                q.get("A", ""),
                q.get("B", ""),
                q.get("C", ""),
                q.get("D", ""),
            ],

            correct_answer=q.get(
                "correct_answer",
                ""
            ),

            user_answer=user_answer,

            explanation=q.get(
                "explanation",
                ""
            ),

            topic=q.get(
                "knowledge_point",
                q.get(
                    "topic",
                    "未分类"
                )
            ),
        )

    except Exception as e:

        st.warning(
            f"错题云端同步失败：{e}"
        )

    else:

        cached_wrong_questions.clear()

        st.session_state[
            "_cloud_hydrated"
        ] = False


# =========================================================
# 云端今日任务同步
# =========================================================

def sync_today_plan(plan):

    if (
        not CLOUD_DB_READY
        or not plan
    ):
        return

    try:

        existing = cached_daily_tasks(
            plan.get(
                "date",
                agent.today_str()
            )
        )

        existing_indexes = {
            int(x.get("task_index"))
            for x in existing
            if str(
                x.get(
                    "task_index",
                    ""
                )
            ).isdigit()
        }

        for i, task in enumerate(
            plan.get("tasks", []),
            1
        ):

            if i in existing_indexes:
                continue

            save_daily_task(

                task_date=plan.get(
                    "date",
                    agent.today_str()
                ),

                task_index=i,

                task_content=task.get(
                    "name",
                    f"任务{i}"
                ),

                completed=bool(
                    task.get(
                        "completed"
                    )
                ),
            )

    except Exception as e:

        st.warning(
            f"每日任务云端同步失败：{e}"
        )


# =========================================================
# 云端任务完成同步
# =========================================================

def sync_task_completion(
    plan,
    task_number
):

    if (
        not CLOUD_DB_READY
        or not plan
    ):
        return

    try:

        cloud_tasks = (
            get_cloud_daily_tasks(
                plan.get(
                    "date",
                    agent.today_str()
                )
            )
        )

        target = next(
            (
                x
                for x in cloud_tasks
                if int(
                    x.get(
                        "task_index",
                        -1
                    )
                )
                == int(task_number)
            ),
            None
        )

        if target:

            complete_daily_task(
                target["id"]
            )

            clear_cloud_cache()

    except Exception as e:

        st.warning(
            f"任务完成状态云端同步失败：{e}"
        )


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:

    st.markdown(
        "## 🎓 AI 学习助手"
    )

    st.caption(
        "软件设计师 AI 自适应学习 Agent"
    )

    st.divider()

    st.header("功能")

    menu = st.radio(

        "选择功能",

        [
            "📅 今日任务",
            "📝 AI专项训练",
            "❌ 错题复习",
            "🧠 自适应分析",
            "📊 学习报告",
            "💬 AI知识库问答",
            "📚 知识库管理",
        ],
    )

    st.divider()

    st.caption(
        cloud_status()
    )
    if CLOUD_RAG_READY:
        st.caption("🧠 云端 RAG：已连接")
    else:
        st.caption(
        f"🟡 云端 RAG：不可用 {CLOUD_RAG_ERROR}"
    )


# =========================================================
# V19 知识库状态显示
# =========================================================

render_knowledge_status()


# =========================================================
# 本地 JSON 工具
# =========================================================

def _write_local(
    path,
    data
):

    import json

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# 云端数据恢复
# =========================================================

def hydrate_from_cloud():

    if not CLOUD_DB_READY:
        return

    try:

        cloud_records = (
            cached_learning_records()
        )

        local_records = []

        for r in cloud_records:

            local_records.append({

                "date": r.get(
                    "created_at",
                    ""
                ),

                "knowledge_point": r.get(
                    "topic",
                    "未分类"
                ),

                "question": r.get(
                    "question",
                    ""
                ),

                "user_answer": r.get(
                    "answer",
                    ""
                ),

                "correct_answer": "",

                "is_correct": bool(
                    r.get(
                        "is_correct"
                    )
                ),

                "mode": "cloud",

                "total": 1,

                "correct": (
                    1
                    if r.get(
                        "is_correct"
                    )
                    else 0
                ),

                "wrong": (
                    0
                    if r.get(
                        "is_correct"
                    )
                    else 1
                ),
            })

        if cloud_records:

            _write_local(
                os.path.join(
                    BASE_DIR,
                    "learning_records.json"
                ),
                local_records
            )

        # -----------------------------------------
        # 错题
        # -----------------------------------------

        cloud_wrong = (
            cached_wrong_questions()
        )

        local_wrong = []

        for r in cloud_wrong:

            opts = (
                r.get("options")
                or {}
            )

            if isinstance(
                opts,
                list
            ):

                opts = {
                    k: (
                        opts[i]
                        if i < len(opts)
                        else ""
                    )
                    for i, k
                    in enumerate(
                        "ABCD"
                    )
                }

            local_wrong.append({

                "question": r.get(
                    "question",
                    ""
                ),

                "A": opts.get(
                    "A",
                    ""
                ),

                "B": opts.get(
                    "B",
                    ""
                ),

                "C": opts.get(
                    "C",
                    ""
                ),

                "D": opts.get(
                    "D",
                    ""
                ),

                "correct_answer": r.get(
                    "correct_answer",
                    "A"
                ),

                "explanation": r.get(
                    "explanation",
                    ""
                ),

                "knowledge_point": r.get(
                    "topic",
                    "未分类"
                ),

                "options": opts,

                "user_answer": r.get(
                    "user_answer",
                    ""
                ),

                "first_wrong_at": r.get(
                    "created_at",
                    ""
                ),

                "last_wrong_at": r.get(
                    "created_at",
                    ""
                ),

                "review_level": int(
                    r.get(
                        "review_count",
                        0
                    )
                    or 0
                ),

                "consecutive_correct": int(
                    r.get(
                        "review_count",
                        0
                    )
                    or 0
                ),

                "next_review_date": (
                    str(
                        r.get(
                            "next_review_at",
                            ""
                        )
                    )[:10]
                    if r.get(
                        "next_review_at"
                    )
                    else agent.today_str()
                ),

                "mastered": bool(
                    r.get(
                        "mastered"
                    )
                ),
            })

        if cloud_wrong:

            _write_local(
                os.path.join(
                    BASE_DIR,
                    "wrong_questions.json"
                ),
                local_wrong
            )

        # -----------------------------------------
        # 今日任务
        # -----------------------------------------

        cloud_tasks = (
            cached_daily_tasks(
                agent.today_str()
            )
        )

        if cloud_tasks:

            existing = (
                agent.get_today_tasks()
            )

            if not existing:

                tasks = []

                for r in cloud_tasks:

                    tasks.append({

                        "name": r.get(
                            "task_content",
                            "学习任务"
                        ),

                        "minutes": 20,

                        "description":
                            "云端恢复的学习任务",

                        "completed": bool(
                            r.get(
                                "completed"
                            )
                        ),

                        "completed_at": None,
                    })

                plan = {

                    "date":
                        agent.today_str(),

                    "goal":
                        "完成今日核心学习任务",

                    "tasks": tasks,

                    "created_at":
                        agent.now_str(),
                }

                _write_local(

                    os.path.join(
                        BASE_DIR,
                        "daily_tasks.json"
                    ),

                    [plan]
                )

    except Exception as e:

        st.warning(
            "云端数据恢复失败，"
            f"将继续使用本地数据：{e}"
        )


# =========================================================
# 初始化云端数据
# =========================================================

hydrate_from_cloud()


# =========================================================
# 本地数据辅助函数
# =========================================================

def learning_records():

    return agent.load_learning_records()


def wrong_questions():

    return agent.load_wrong_questions()


# =========================================================
# 今日任务
# =========================================================

if menu == "📅 今日任务":

    st.subheader(
        "📅 今日学习任务"
    )

    plan = (
        agent.get_today_tasks()
    )

    if not plan:

        if st.button(
            "🤖 AI生成今日计划",
            type="primary"
        ):

            with st.spinner(
                "正在分析学习数据并制定计划..."
            ):

                try:

                    plan = (
                        agent.create_dynamic_study_plan()
                    )

                    sync_today_plan(
                        plan
                    )

                    clear_cloud_cache()

                    st.success(
                        "今日学习计划已生成。"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"生成计划失败：{e}"
                    )

    else:

        sync_today_plan(
            plan
        )

    plan = (
        agent.get_today_tasks()
    )

    if plan:
        goal = plan.get("goal", "完成今日核心学习任务")
        st.info(f"🔔 今日目标：{goal}")

        tasks = plan.get(
            "tasks",
            []
        )

        for i, task in enumerate(
            tasks,
            1
        ):

            done = bool(
                task.get(
                    "completed"
                )
            )

            title = task.get(
                "name",
                f"任务{i}"
            )

            mins = task.get(
                "minutes",
                ""
            )

            desc = task.get(
                "description",
                ""
            )

            col1, col2 = st.columns(
                [5, 1]
            )

            with col1:

                st.markdown(
                    f"{'✅' if done else '⬜'} "
                    f"**任务{i}：{title}**"
                )

                if mins:

                    st.caption(
                        f"{mins} 分钟"
                    )

                if desc:

                    st.write(
                        desc
                    )

            with col2:

                if (
                    not done
                    and st.button(
                        "完成",
                        key=f"complete_{i}"
                    )
                ):

                    ok, msg = (
                        agent.complete_task(i)
                    )

                    if ok:

                        sync_task_completion(
                            plan,
                            i
                        )

                        st.success(
                            msg
                        )

                        st.rerun()

                    else:

                        st.warning(
                            msg
                        )

    else:

        st.info(
            "今天还没有学习计划。"
        )


# =========================================================
# AI专项训练
# =========================================================

elif menu == "📝 AI专项训练":

    st.subheader(
        "📝 AI专项训练"
    )

    if (
        "training_question"
        not in st.session_state
    ):

        st.session_state[
            "training_question"
        ] = None

    if (
        "training_submitted"
        not in st.session_state
    ):

        st.session_state[
            "training_submitted"
        ] = False

    if (
        "last_result"
        not in st.session_state
    ):

        st.session_state[
            "last_result"
        ] = None

    if (
        "training_topic"
        not in st.session_state
    ):

        st.session_state[
            "training_topic"
        ] = ""

    if (
        "adaptive_default_topic"
        not in st.session_state
    ):

        st.session_state[
            "adaptive_default_topic"
        ] = (
            agent.choose_adaptive_topic()
        )

    default_topic = (
        st.session_state[
            "adaptive_default_topic"
        ]
    )

    topic = st.text_input(

        "训练知识点",

        value=default_topic,

        placeholder=(
            "例如：软件测试、"
            "数据结构、软件开发方法"
        ),

        key="training_topic_input",
    )

    if st.button(
        "🎯 生成一道题",
        type="primary"
    ):

        st.session_state[
            "training_question"
        ] = None

        st.session_state[
            "training_submitted"
        ] = False

        st.session_state[
            "last_result"
        ] = None

        st.session_state[
            "training_topic"
        ] = topic

        with st.spinner(
            "正在生成题目，请稍候..."
        ):

            try:

                agent.start_training(
                    topic
                )

                new_q = getattr(
                    agent,
                    "current_question",
                    None
                )

                if not new_q:

                    raise RuntimeError(
                        "AI没有返回题目，请重试"
                    )

                st.session_state[
                    "training_question"
                ] = (
                    agent.normalize_question(
                        new_q
                    )
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"出题失败：{e}"
                )

    q = st.session_state.get(
        "training_question"
    )

    if q:

        st.markdown(
            "### 题目"
        )

        st.write(
            q.get(
                "question",
                ""
            )
        )

        opts = q.get(
            "options",
            {}
        )

        answer = st.radio(

            "选择答案",

            [
                "A",
                "B",
                "C",
                "D"
            ],

            format_func=lambda x:
                f"{x}. {opts.get(x, '')}",

            key="training_answer",
        )

        if not st.session_state.get(
            "training_submitted"
        ):

            if st.button(
                "提交答案",
                type="primary"
            ):

                before_q = dict(q)

                is_correct = (
                    answer
                    == str(
                        before_q.get(
                            "correct_answer",
                            ""
                        )
                    ).upper()
                )

                try:

                    agent.current_question = (
                        before_q
                    )

                    agent.grade_answer(
                        answer
                    )

                    sync_learning_record(
                        before_q,
                        answer,
                        is_correct,
                        "training"
                    )

                    if not is_correct:

                        sync_wrong_question(
                            before_q,
                            answer
                        )

                    clear_cloud_cache()

                    st.session_state[
                        "training_submitted"
                    ] = True

                    st.session_state[
                        "last_result"
                    ] = is_correct

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"答题失败：{e}"
                    )

        if st.session_state.get(
            "training_submitted"
        ):

            correct = str(
                q.get(
                    "correct_answer",
                    ""
                )
            ).upper()

            if st.session_state.get(
                "last_result"
            ):

                st.success(
                    "🎉 回答正确！"
                    "学习记录已保存。"
                )

            else:

                st.error(
                    "❌ 回答错误！"
                    "错题和学习记录已保存。"
                )

            st.markdown(
                f"### ✅ 正确答案：**{correct}**"
            )

            if opts.get(correct):

                st.write(
                    f"**{correct}. "
                    f"{opts.get(correct)}**"
                )

            if q.get(
                "explanation"
            ):

                st.info(
                    "📖 **解析：** "
                    f"{q.get('explanation')}"
                )

            if st.button(
                "🎯 再生成一道题",
                type="primary"
            ):

                st.session_state[
                    "training_question"
                ] = None

                st.session_state[
                    "training_submitted"
                ] = False

                st.session_state[
                    "last_result"
                ] = None

                st.rerun()


# =========================================================
# 错题复习
# =========================================================

elif menu == "❌ 错题复习":

    st.subheader(
        "❌ 错题复习"
    )

    due = (
        agent.get_due_wrong_questions()
    )

    if not due:

        cloud_all = (
            cached_wrong_questions()
        )

        if cloud_all:

            local_wrong = []

            for r in cloud_all:

                opts = (
                    r.get("options")
                    or {}
                )

                if isinstance(
                    opts,
                    list
                ):

                    opts = {
                        k: (
                            opts[i]
                            if i < len(opts)
                            else ""
                        )
                        for i, k
                        in enumerate(
                            "ABCD"
                        )
                    }

                local_wrong.append({

                    "question": r.get(
                        "question",
                        ""
                    ),

                    "A": opts.get(
                        "A",
                        ""
                    ),

                    "B": opts.get(
                        "B",
                        ""
                    ),

                    "C": opts.get(
                        "C",
                        ""
                    ),

                    "D": opts.get(
                        "D",
                        ""
                    ),

                    "correct_answer":
                        r.get(
                            "correct_answer",
                            "A"
                        ),

                    "explanation":
                        r.get(
                            "explanation",
                            ""
                        ),

                    "knowledge_point":
                        r.get(
                            "topic",
                            "未分类"
                        ),

                    "options": opts,

                    "user_answer":
                        r.get(
                            "user_answer",
                            ""
                        ),

                    "first_wrong_at":
                        r.get(
                            "created_at",
                            ""
                        ),

                    "last_wrong_at":
                        r.get(
                            "created_at",
                            ""
                        ),

                    "review_level":
                        int(
                            r.get(
                                "review_count",
                                0
                            )
                            or 0
                        ),

                    "consecutive_correct":
                        int(
                            r.get(
                                "review_count",
                                0
                            )
                            or 0
                        ),

                    "next_review_date":
                        str(
                            r.get(
                                "next_review_at",
                                ""
                            )
                        )[:10]
                        or agent.today_str(),

                    "mastered":
                        bool(
                            r.get(
                                "mastered"
                            )
                        ),
                })

            _write_local(

                os.path.join(
                    BASE_DIR,
                    "wrong_questions.json"
                ),

                local_wrong
            )

            due = (
                agent.get_due_wrong_questions()
            )

    if not due:

        st.success(
            "🎉 今天没有到期错题。"
        )

        future = sorted(

            q.get(
                "next_review_date"
            )

            for q in agent.load_wrong_questions()

            if q.get(
                "next_review_date"
            )

            and not q.get(
                "mastered"
            )

            and q.get(
                "next_review_date"
            ) > agent.today_str()
        )

        if future:

            st.info(
                f"下一次复习：{future[0]}"
            )

    else:

        st.info(
            f"今天到期：{len(due)} 道"
        )

        q = (
            agent.current_question
            if agent.wrong_review_mode
            else None
        )

        if not q:

            if st.button(
                "▶️ 开始错题复习",
                type="primary"
            ):

                try:

                    agent.start_wrong_review()

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"开始复习失败：{e}"
                    )

        else:

            q = (
                agent.normalize_question(q)
            )

            st.markdown(
                "### 错题"
            )

            st.write(
                q.get(
                    "question",
                    ""
                )
            )

            opts = q.get(
                "options",
                {}
            )

            answer = st.radio(

                "选择答案",

                [
                    "A",
                    "B",
                    "C",
                    "D"
                ],

                format_func=lambda x:
                    f"{x}. {opts.get(x, '')}",

                key="review_answer",
            )

            if st.button(
                "提交复习答案",
                type="primary"
            ):

                before_q = dict(q)

                is_correct = (
                    answer
                    == str(
                        before_q.get(
                            "correct_answer",
                            ""
                        )
                    ).upper()
                )

                try:

                    agent.grade_answer(
                        answer,
                        review=True
                    )

                    sync_learning_record(
                        before_q,
                        answer,
                        is_correct,
                        "wrong_review"
                    )

                    if not is_correct:

                        sync_wrong_question(
                            before_q,
                            answer
                        )

                    st.success(
                        "复习结果已保存。"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"复习失败：{e}"
                    )


# =========================================================
# 自适应分析
# =========================================================

elif menu == "🧠 自适应分析":

    st.subheader(
        "🧠 AI 自适应学习分析"
    )

    status = (
        agent.calculate_learning_status()
    )

    if not status:

        st.info(
            "先完成几道题，"
            "系统会建立学习画像。"
        )

    else:

        st.dataframe(

            [

                {
                    "知识点":
                        x["knowledge_point"],

                    "答题数":
                        x["total"],

                    "正确率":
                        x["accuracy"],

                    "掌握度":
                        x["mastery"],

                    "未掌握错题":
                        x["wrong_questions"],

                    "优先级":
                        x["priority"],
                }

                for x in status

            ],

            use_container_width=True,

            hide_index=True,
        )

        top = status[0]

        st.success(

            f"🎯 当前优先强化："
            f"{top['knowledge_point']}｜"
            f"掌握度 {top['mastery']}%｜"
            f"正确率 {top['accuracy']}%"
        )

        if st.button(
            "🔄 根据最新数据重新制定今天计划"
        ):

            try:

                plan = (
                    agent.create_dynamic_study_plan(
                        True
                    )
                )

                sync_today_plan(
                    plan
                )

                st.success(
                    "计划已重新制定。"
                )

            except Exception as e:

                st.error(
                    f"重新制定计划失败：{e}"
                )


# =========================================================
# 学习报告
# =========================================================

elif menu == "📊 学习报告":

    st.subheader(
        "📊 学习报告"
    )

    report = (
        agent.learning_report()
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "今日任务",
        f"{report['tasks_done']}/"
        f"{report['tasks_total']}"
    )

    b.metric(
        "今日学习",
        f"{report['minutes']} 分钟"
    )

    c.metric(
        "今日做题",
        report["today"]["questions"]
    )

    d.metric(
        "正确率",
        f"{report['today']['accuracy']:.1f}%"
    )

    st.divider()

    st.write(

        f"**当前未掌握错题：** "
        f"{report['wrong_count']}　　"

        f"**今日待复习：** "
        f"{report['due_count']}"
    )

    if report["status"]:

        st.dataframe(

            [

                {
                    "知识点":
                        x["knowledge_point"],

                    "正确率":
                        x["accuracy"],

                    "掌握度":
                        x["mastery"],

                    "答题数":
                        x["total"],

                    "未掌握错题":
                        x["wrong_questions"],
                }

                for x in report["status"]

            ],

            use_container_width=True,

            hide_index=True,
        )


# =========================================================
# AI知识库问答
# =========================================================

elif menu == "💬 AI知识库问答":

    st.subheader(
        "💬 AI知识库问答"
    )

    query = st.text_area(

        "输入你的问题",

        placeholder=(
            "例如：结构化方法是什么？"
            "黑盒测试和白盒测试有什么区别？"
        ),

        height=120,
    )

    if st.button(
        "🔎 查询知识库并回答",
        type="primary"
    ):

        if not query.strip():

            st.warning(
                "请先输入问题。"
            )

        else:

            with st.spinner(
                "正在检索知识库..."
            ):

                try:

                    # V14：检索 3 个知识块
                    ctx = (
                        agent.search_knowledge(
                            query,
                            3
                        )
                    )

                    answer = agent.ai(

                        f"""
请根据下面的软件设计师知识库回答用户问题。

要求：
1. 优先依据知识库。
2. 不要编造知识库中没有的信息。
3. 如果资料不足，请明确说明。
4. 最后给出“考试记忆点”。

用户问题：
{query}

知识库：
{ctx}
"""
                    )

                    st.markdown(
                        "### 🤖 AI回答"
                    )

                    st.write(
                        answer
                    )

                    with st.expander(
                        "📚 查看本次检索到的知识"
                    ):

                        st.text(
                            ctx
                        )

                except Exception as e:

                    st.error(
                        f"问答失败：{e}"
                    )


# =========================================================
# V19：知识库管理
# =========================================================

elif menu == "📚 知识库管理":

    st.title("📚 知识库管理")

    st.caption(
        "☁️ Supabase 云端知识库 + 本地 RAG 缓存"
    )

    try:
        import knowledge_manager
    except Exception as e:
        st.error(f"知识库管理模块加载失败：{e}")
        st.stop()

    # =====================================================
    # 云端知识库状态
    # =====================================================

    st.subheader("☁️ 云端知识库状态")

    try:
        cloud_files = knowledge_manager.get_cloud_knowledge_files()

        if not isinstance(cloud_files, list):
            cloud_files = []

        cloud_count = len(cloud_files)

    except Exception as e:
        cloud_files = []
        cloud_count = 0
        st.warning(f"云端知识库暂时无法读取：{e}")

    # 本地文件
    try:
        local_files = knowledge_manager.get_knowledge_files()
    except Exception:
        local_files = []

    # Chroma
    try:
        chroma_status = knowledge_manager.get_chroma_status()
    except Exception:
        chroma_status = {}

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "☁️ 云端资料",
            cloud_count
        )

    with c2:
        st.metric(
            "💻 本地资料",
            len(local_files)
        )

    with c3:
        st.metric(
            "🧠 RAG知识块",
            chroma_status.get("documents", 0)
        )

    with c4:
        if chroma_status.get("exists"):
            st.metric(
                "数据库状态",
                "🟢 正常"
            )
        else:
            st.metric(
                "数据库状态",
                "🔴 未构建"
            )

    st.divider()

    # =====================================================
    # 云端资料列表
    # =====================================================

    st.subheader("☁️ 云端学习资料")

    if not cloud_files:

        st.info(
            "当前 Supabase 云端知识库还没有资料。"
        )

    else:

        for index, item in enumerate(cloud_files, 1):

            if not isinstance(item, dict):
                continue

            file_name = item.get(
                "file_name",
                "未知文件"
            )

            file_size = item.get(
                "file_size",
                0
            )

            status = item.get(
                "status",
                "uploaded"
            )

            created_at = item.get(
                "created_at",
                ""
            )

            if file_size:

                size_mb = file_size / 1024 / 1024

                size_text = (
                    f"{size_mb:.2f} MB"
                )

            else:

                size_text = "未知大小"

            col_a, col_b, col_c = st.columns(
                [5, 2, 1]
            )

            with col_a:

                st.write(
                    f"**{index}. {file_name}**"
                )

                st.caption(
                    f"{size_text} · {status} · {created_at}"
                )

            with col_b:

                st.write("☁️ Supabase Storage")

            with col_c:

                document_id = item.get("id")

                if document_id is not None:

                    if st.button(
                        "🗑️ 删除",
                        key=f"delete_cloud_{document_id}"
                    ):

                        try:

                            result = (
                                knowledge_manager
                                .delete_cloud_knowledge_file(
                                    document_id
                                )
                            )

                            if result.get("success"):

                                st.success(
                                    "云端文件已删除"
                                )

                                st.rerun()

                            else:

                                st.error(
                                    result.get(
                                        "message",
                                        "删除失败"
                                    )
                                )

                        except Exception as e:

                            st.error(
                                f"删除失败：{e}"
                            )

    st.divider()

    # =====================================================
    # 上传资料
    # =====================================================

    st.subheader("📤 上传学习资料")

    st.info(
        "上传后会同时保存到 Supabase 云端 Storage，"
        "并保存到当前运行环境的 knowledge/ 目录作为 RAG 构建缓存。"
    )

    uploaded_files = st.file_uploader(
        "选择 PDF / TXT 学习资料",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        help="支持一次选择多个 PDF / TXT 文件",
    )

    if uploaded_files:

        if st.button(
            "☁️ 上传到云端知识库",
            type="primary",
            use_container_width=True,
        ):

            success_count = 0
            duplicate_count = 0
            fail_count = 0

            progress = st.progress(0)

            total = len(uploaded_files)

            for index, uploaded_file in enumerate(
                uploaded_files,
                1
            ):

                try:

                    file_bytes = uploaded_file.getvalue()

                    result = (
                        knowledge_manager
                        .upload_to_cloud(
                            uploaded_file.name,
                            file_bytes
                        )
                    )

                    if result.get("success"):

                        if result.get("duplicate"):

                            duplicate_count += 1

                            st.warning(
                                f"⚠️ 已存在："
                                f"{uploaded_file.name}"
                            )

                        else:

                            success_count += 1

                            st.success(
                                f"☁️ 云端上传成功："
                                f"{uploaded_file.name}"
                            )

                        # 同时保存本地 RAG 缓存
                        try:

                            local_success, local_message, local_path = (
                                knowledge_manager
                                .save_uploaded_file(
                                    uploaded_file
                                )
                            )

                            if local_success:

                                st.caption(
                                    f"💻 本地 RAG 缓存："
                                    f"{local_message}"
                                )

                            else:

                                st.warning(
                                    f"本地缓存失败："
                                    f"{local_message}"
                                )

                        except Exception as local_error:

                            st.warning(
                                f"本地缓存异常："
                                f"{local_error}"
                            )

                    else:

                        fail_count += 1

                        st.error(
                            f"❌ 上传失败："
                            f"{uploaded_file.name}"
                            f"："
                            f"{result.get('message', '未知错误')}"
                        )

                except Exception as e:

                    fail_count += 1

                    st.error(
                        f"❌ 处理 {uploaded_file.name} "
                        f"失败：{e}"
                    )

                progress.progress(
                    index / total
                )

            st.divider()

            st.write(
                f"📊 上传结果："
                f"成功 {success_count} 个，"
                f"重复 {duplicate_count} 个，"
                f"失败 {fail_count} 个"
            )

            if success_count > 0:

                st.success(
                    "🎉 云端知识库更新成功！"
                )

            st.rerun()

    st.divider()

    # =====================================================
    # RAG 重建
    # =====================================================

    st.subheader("🧠 重建 RAG 知识库")

    st.warning(
        "新增资料后，需要重新构建 RAG 索引，"
        "AI 才能检索到最新内容。"
    )

    if st.button(
        "🔄 重新构建 RAG 知识库",
        use_container_width=True,
    ):

        with st.spinner(
            "正在扫描 PDF / TXT 并构建 RAG，请稍候..."
        ):

            try:

                result = (
                    knowledge_manager
                    .rebuild_knowledge_base()
                )

            except Exception as e:

                result = {
                    "success": False,
                    "output": str(e)
                }

        if result.get("success"):

            st.success(
                "🎉 RAG 知识库构建完成！"
            )

            output = result.get(
                "output",
                ""
            )

            if output:

                with st.expander(
                    "📋 查看构建日志"
                ):

                    st.code(
                        output,
                        language="text"
                    )

            st.rerun()

        else:

            st.error(
                "❌ RAG 知识库构建失败"
            )

            st.code(
                result.get(
                    "output",
                    "未知错误"
                ),
                language="text"
            )

    st.divider()

    # =====================================================
    # 使用流程
    # =====================================================

    st.subheader("💡 使用流程")

    st.markdown(
        """
        **① 上传资料**

        上传 PDF / TXT → 自动保存到 Supabase Storage

        **② 本地缓存**

        同时保存到 `knowledge/`，用于构建 RAG

        **③ 重建 RAG**

        点击「重新构建 RAG 知识库」

        **④ AI 问答**

        前往「💬 AI知识库问答」

        **⑤ 云端持久化**

        原始学习资料保存在 Supabase，
        即使 Streamlit Cloud 重启，资料也不会丢失。
        """
    )


# =========================================================
# 页面底部
# =========================================================

st.divider()

st.caption(
    "软件设计师 AI 自适应学习 Agent "
    "· RAG + DeepSeek + ChromaDB + BGE + Supabase"
)