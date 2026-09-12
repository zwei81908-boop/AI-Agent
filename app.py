import os
from datetime import date
import streamlit as st

import agent

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- 性能优化：云端读取短缓存 ----------
# Streamlit 每次交互都会重新运行脚本；不缓存会导致每次点击都请求 Supabase。
@st.cache_data(ttl=30, show_spinner=False)
def cached_learning_records():
    if not CLOUD_DB_READY:
        return []
    return get_cloud_learning_records(500)

@st.cache_data(ttl=30, show_spinner=False)
def cached_wrong_questions():
    if not CLOUD_DB_READY:
        return []
    return get_cloud_wrong_questions(500)

@st.cache_data(ttl=30, show_spinner=False)
def cached_daily_tasks(task_date):
    if not CLOUD_DB_READY:
        return []
    return get_cloud_daily_tasks(task_date)

def clear_cloud_cache():
    cached_learning_records.clear()
    cached_wrong_questions.clear()
    cached_daily_tasks.clear()

st.set_page_config(
    page_title="软件设计师 AI 自适应学习 Agent",
    page_icon="🤖",
    layout="wide",
)

# ---------- V11 科技深色 UI ----------
st.markdown("""
<style>
/* 页面整体 */
.stApp {
    background: radial-gradient(circle at 20% 0%, #102b55 0%, #06101f 38%, #030711 100%);
    color: #e8f1ff;
}
.block-container {
    max-width: 1450px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

/* 侧边栏 */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #06152b 0%, #020916 100%);
    border-right: 1px solid rgba(0, 153, 255, .35);
}
section[data-testid="stSidebar"] * {
    color: #e6f2ff !important;
}
section[data-testid="stSidebar"] .stRadio label {
    border-radius: 10px;
    padding: 7px 10px;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(0, 153, 255, .12);
}

/* 标题 */
h1, h2, h3 {
    color: #f4f8ff !important;
    letter-spacing: .2px;
}
h1 {
    text-shadow: 0 0 22px rgba(0, 153, 255, .35);
}

/* 卡片 */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(12,35,67,.92), rgba(4,15,29,.96));
    border: 1px solid rgba(0,153,255,.32);
    border-radius: 14px;
    padding: 14px;
    box-shadow: 0 0 22px rgba(0, 105, 255, .08);
}
div[data-testid="stMetricLabel"] {
    color: #8fb9e8 !important;
}
div[data-testid="stMetricValue"] {
    color: #f5f9ff !important;
}

/* 通用容器 */
div[data-testid="stExpander"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(0,153,255,.25);
    border-radius: 14px;
    background: rgba(5,18,35,.72);
}

/* 输入框 */
textarea, input {
    background: rgba(4,16,31,.92) !important;
    color: #edf6ff !important;
    border: 1px solid rgba(0,153,255,.35) !important;
    border-radius: 10px !important;
}

/* 按钮 */
.stButton > button {
    border-radius: 10px;
    border: 1px solid rgba(0,153,255,.55);
    background: linear-gradient(135deg, #075dcc, #073a82);
    color: white;
    font-weight: 600;
    box-shadow: 0 0 14px rgba(0,120,255,.16);
}
.stButton > button:hover {
    border-color: #19a7ff;
    box-shadow: 0 0 20px rgba(0,160,255,.32);
    transform: translateY(-1px);
}

/* 表格 */
div[data-testid="stDataFrame"] {
    border: 1px solid rgba(0,153,255,.25);
    border-radius: 12px;
    overflow: hidden;
}

/* 分隔线 */
hr {
    border-color: rgba(0,153,255,.22) !important;
}

/* 状态文字 */
.tech-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    border: 1px solid rgba(0, 255, 190, .35);
    background: rgba(0, 255, 190, .08);
    color: #66f5d0;
    font-size: 13px;
}
.hero {
    padding: 22px 26px;
    border-radius: 18px;
    border: 1px solid rgba(0,153,255,.35);
    background:
        radial-gradient(circle at 85% 25%, rgba(0,153,255,.28), transparent 30%),
        linear-gradient(135deg, rgba(8,39,77,.96), rgba(3,15,29,.96));
    box-shadow: 0 0 35px rgba(0,110,255,.10);
    margin-bottom: 18px;
}
.hero-title {
    font-size: 30px;
    font-weight: 800;
    margin-bottom: 8px;
}
.hero-sub {
    color: #a7c5e8;
    font-size: 15px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-title">🧠 软件设计师 AI 自适应学习 Agent</div>
  <div class="hero-sub">DeepSeek + RAG + ChromaDB + Supabase · 智能出题 · 错题复习 · 自适应学习</div>
</div>
<div class="tech-badge">● 云端 AI 学习系统</div>
""", unsafe_allow_html=True)

st.caption("你的 AI 驱动软件设计师学习工作台")

def cloud_status():
    if CLOUD_DB_READY:
        return "🟢 云端数据库已连接"
    return f"🟡 云端数据库暂不可用：{CLOUD_DB_ERROR}"

def sync_learning_record(q, user_answer, is_correct, mode):
    if not CLOUD_DB_READY:
        return
    try:
        save_learning_record(
            topic=q.get("knowledge_point", q.get("topic", "未分类")),
            question=q.get("question", ""),
            answer=user_answer,
            is_correct=bool(is_correct),
            score=100 if is_correct else 0,
        )
    except Exception as e:
        st.warning(f"学习记录云端同步失败：{e}")
    else:
        cached_learning_records.clear()
        st.session_state["_cloud_hydrated"] = False

def sync_wrong_question(q, user_answer):
    if not CLOUD_DB_READY:
        return
    try:
        save_cloud_wrong_question(
            question=q.get("question", ""),
            options=[q.get("A", ""), q.get("B", ""), q.get("C", ""), q.get("D", "")],
            correct_answer=q.get("correct_answer", ""),
            user_answer=user_answer,
            explanation=q.get("explanation", ""),
            topic=q.get("knowledge_point", q.get("topic", "未分类")),
        )
    except Exception as e:
        st.warning(f"错题云端同步失败：{e}")
    else:
        cached_wrong_questions.clear()
        st.session_state["_cloud_hydrated"] = False

def sync_today_plan(plan):
    if not CLOUD_DB_READY or not plan:
        return
    try:
        existing = cached_daily_tasks(plan.get("date", agent.today_str()))
        existing_indexes = {int(x.get("task_index")) for x in existing if str(x.get("task_index", "")).isdigit()}
        for i, task in enumerate(plan.get("tasks", []), 1):
            if i in existing_indexes:
                continue
            save_daily_task(
                task_date=plan.get("date", agent.today_str()),
                task_index=i,
                task_content=task.get("name", f"任务{i}"),
                completed=bool(task.get("completed")),
            )
    except Exception as e:
        st.warning(f"每日任务云端同步失败：{e}")

def sync_task_completion(plan, task_number):
    if not CLOUD_DB_READY or not plan:
        return
    try:
        cloud_tasks = get_cloud_daily_tasks(plan.get("date", agent.today_str()))
        target = next(
            (x for x in cloud_tasks if int(x.get("task_index", -1)) == int(task_number)),
            None
        )
        if target:
            complete_daily_task(target["id"])
            clear_cloud_cache()
    except Exception as e:
        st.warning(f"任务完成状态云端同步失败：{e}")

# ---------- sidebar ----------
with st.sidebar:
    st.markdown("## 🧠 AI 学习助手")
    st.caption("软件设计师 AI 自适应学习 Agent")
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
        ],
    )
    st.divider()
    st.caption(cloud_status())

# ---------- cloud/local data helpers ----------
def _write_local(path, data):
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hydrate_from_cloud():
    """把云端数据转换成现有 Agent 能识别的本地结构。
    这样原有的自适应、间隔复习和报告逻辑无需推倒重写。
    """
    if not CLOUD_DB_READY:
        return
    try:
        cloud_records = cached_learning_records()
        local_records = []
        for r in cloud_records:
            local_records.append({
                "date": r.get("created_at", ""),
                "knowledge_point": r.get("topic", "未分类"),
                "question": r.get("question", ""),
                "user_answer": r.get("answer", ""),
                "correct_answer": "",
                "is_correct": bool(r.get("is_correct")),
                "mode": "cloud",
                "total": 1,
                "correct": 1 if r.get("is_correct") else 0,
                "wrong": 0 if r.get("is_correct") else 1,
            })
        if cloud_records:
            _write_local(os.path.join(BASE_DIR, "learning_records.json"), local_records)

        cloud_wrong = cached_wrong_questions()
        local_wrong = []
        for r in cloud_wrong:
            opts = r.get("options") or {}
            if isinstance(opts, list):
                opts = {k: (opts[i] if i < len(opts) else "") for i, k in enumerate("ABCD")}
            local_wrong.append({
                "question": r.get("question", ""),
                "A": opts.get("A", ""),
                "B": opts.get("B", ""),
                "C": opts.get("C", ""),
                "D": opts.get("D", ""),
                "correct_answer": r.get("correct_answer", "A"),
                "explanation": r.get("explanation", ""),
                "knowledge_point": r.get("topic", "未分类"),
                "options": opts,
                "user_answer": r.get("user_answer", ""),
                "first_wrong_at": r.get("created_at", ""),
                "last_wrong_at": r.get("created_at", ""),
                "review_level": int(r.get("review_count", 0) or 0),
                "consecutive_correct": int(r.get("review_count", 0) or 0),
                "next_review_date": (str(r.get("next_review_at", ""))[:10] if r.get("next_review_at") else agent.today_str()),
                "mastered": bool(r.get("mastered")),
            })
        if cloud_wrong:
            _write_local(os.path.join(BASE_DIR, "wrong_questions.json"), local_wrong)

        cloud_tasks = cached_daily_tasks(agent.today_str())
        if cloud_tasks:
            existing = agent.get_today_tasks()
            if not existing:
                tasks = []
                for r in cloud_tasks:
                    tasks.append({
                        "name": r.get("task_content", "学习任务"),
                        "minutes": 20,
                        "description": "云端恢复的学习任务",
                        "completed": bool(r.get("completed")),
                        "completed_at": None,
                    })
                plan = {
                    "date": agent.today_str(),
                    "goal": "完成今日核心学习任务",
                    "tasks": tasks,
                    "created_at": agent.now_str(),
                }
                _write_local(os.path.join(BASE_DIR, "daily_tasks.json"), [plan])
    except Exception as e:
        st.warning(f"云端数据恢复失败，将继续使用本地数据：{e}")

hydrate_from_cloud()

def learning_records():
    return agent.load_learning_records()

def wrong_questions():
    return agent.load_wrong_questions()

# ---------- 今日任务 ----------
if menu == "📅 今日任务":
    st.subheader("📅 今日学习任务")

    plan = agent.get_today_tasks()
    if not plan:
        if st.button("🤖 AI生成今日计划", type="primary"):
            with st.spinner("正在分析学习数据并制定计划..."):
                try:
                    plan = agent.create_dynamic_study_plan()
                    sync_today_plan(plan)
                    clear_cloud_cache()
                    st.success("今日学习计划已生成。")
                    st.rerun()
                except Exception as e:
                    st.error(f"生成计划失败：{e}")
    else:
        sync_today_plan(plan)

    plan = agent.get_today_tasks()
    if plan:
        st.info(f"🎯 今日目标：{plan.get('goal', '完成今日核心学习任务')}")
        tasks = plan.get("tasks", [])
        for i, task in enumerate(tasks, 1):
            done = bool(task.get("completed"))
            title = task.get("name", f"任务{i}")
            mins = task.get("minutes", "")
            desc = task.get("description", "")
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"{'✅' if done else '⬜'} **任务{i}：{title}**")
                if mins:
                    st.caption(f"{mins} 分钟")
                if desc:
                    st.write(desc)
            with col2:
                if not done and st.button("完成", key=f"complete_{i}"):
                    ok, msg = agent.complete_task(i)
                    if ok:
                        sync_task_completion(plan, i)
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)
    else:
        st.info("今天还没有学习计划。")

# ---------- AI专项训练 ----------
elif menu == "📝 AI专项训练":
    st.subheader("📝 AI专项训练")

    # 关键修复：题目完全由 session_state 控制。
    # 页面刚打开/切换知识点时，不再把 agent.current_question 中的旧题目显示出来。
    if "training_question" not in st.session_state:
        st.session_state["training_question"] = None
    if "training_submitted" not in st.session_state:
        st.session_state["training_submitted"] = False
    if "last_result" not in st.session_state:
        st.session_state["last_result"] = None
    if "training_topic" not in st.session_state:
        st.session_state["training_topic"] = ""

    if "adaptive_default_topic" not in st.session_state:
        st.session_state["adaptive_default_topic"] = agent.choose_adaptive_topic()
    default_topic = st.session_state["adaptive_default_topic"]

    topic = st.text_input(
        "训练知识点",
        value=default_topic,
        placeholder="例如：软件测试、数据结构、软件开发方法",
        key="training_topic_input",
    )

    if st.button("🎯 生成一道题", type="primary"):
        # 先清空旧题，保证生成期间页面下方为空。
        st.session_state["training_question"] = None
        st.session_state["training_submitted"] = False
        st.session_state["last_result"] = None
        st.session_state["training_topic"] = topic

        with st.spinner("正在生成题目，请稍候..."):
            try:
                agent.start_training(topic)
                new_q = getattr(agent, "current_question", None)
                if not new_q:
                    raise RuntimeError("AI没有返回题目，请重试")
                st.session_state["training_question"] = agent.normalize_question(new_q)
                st.rerun()
            except Exception as e:
                st.error(f"出题失败：{e}")

    q = st.session_state.get("training_question")

    # 没点击“生成一道题”之前，这一块保持空白。
    if q:
        st.markdown("### 题目")
        st.write(q.get("question", ""))
        opts = q.get("options", {})
        answer = st.radio(
            "选择答案",
            ["A", "B", "C", "D"],
            format_func=lambda x: f"{x}. {opts.get(x, '')}",
            key="training_answer",
        )

        if not st.session_state.get("training_submitted"):
            if st.button("提交答案", type="primary"):
                before_q = dict(q)
                is_correct = answer == str(before_q.get("correct_answer", "")).upper()
                try:
                    agent.current_question = before_q
                    agent.grade_answer(answer)
                    sync_learning_record(before_q, answer, is_correct, "training")
                    if not is_correct:
                        sync_wrong_question(before_q, answer)
                    clear_cloud_cache()
                    st.session_state["training_submitted"] = True
                    st.session_state["last_result"] = is_correct
                    st.rerun()
                except Exception as e:
                    st.error(f"答题失败：{e}")

        if st.session_state.get("training_submitted"):
            correct = str(q.get("correct_answer", "")).upper()
            if st.session_state.get("last_result"):
                st.success("🎉 回答正确！学习记录已保存。")
            else:
                st.error("❌ 回答错误！错题和学习记录已保存。")

            # 新增：提交后明确显示标准答案和解析。
            st.markdown(f"### ✅ 正确答案：**{correct}**")
            if opts.get(correct):
                st.write(f"**{correct}. {opts.get(correct)}**")
            if q.get("explanation"):
                st.info(f"📖 **解析：** {q.get('explanation')}")

            if st.button("🎯 再生成一道题", type="primary"):
                st.session_state["training_question"] = None
                st.session_state["training_submitted"] = False
                st.session_state["last_result"] = None
                st.rerun()

# ---------- 错题复习 ----------
elif menu == "❌ 错题复习":
    st.subheader("❌ 错题复习")
    # 云端错题是权威来源；hydrate 已把 next_review_at 为空的新增错题按“今天到期”恢复。
    due = agent.get_due_wrong_questions()

    if not due:
        # 兜底：如果旧云端数据 next_review_at 为空，直接把它们视为今天到期。
        cloud_all = cached_wrong_questions()
        if cloud_all:
            local_wrong = []
            for r in cloud_all:
                opts = r.get("options") or {}
                if isinstance(opts, list):
                    opts = {k: (opts[i] if i < len(opts) else "") for i, k in enumerate("ABCD")}
                local_wrong.append({
                    "question": r.get("question", ""),
                    "A": opts.get("A", ""),
                    "B": opts.get("B", ""),
                    "C": opts.get("C", ""),
                    "D": opts.get("D", ""),
                    "correct_answer": r.get("correct_answer", "A"),
                    "explanation": r.get("explanation", ""),
                    "knowledge_point": r.get("topic", "未分类"),
                    "options": opts,
                    "user_answer": r.get("user_answer", ""),
                    "first_wrong_at": r.get("created_at", ""),
                    "last_wrong_at": r.get("created_at", ""),
                    "review_level": int(r.get("review_count", 0) or 0),
                    "consecutive_correct": int(r.get("review_count", 0) or 0),
                    "next_review_date": str(r.get("next_review_at", ""))[:10] or agent.today_str(),
                    "mastered": bool(r.get("mastered")),
                })
            _write_local(os.path.join(BASE_DIR, "wrong_questions.json"), local_wrong)
            due = agent.get_due_wrong_questions()

    if not due:
        st.success("🎉 今天没有到期错题。")
        future = sorted(
            q.get("next_review_date")
            for q in agent.load_wrong_questions()
            if q.get("next_review_date")
            and not q.get("mastered")
            and q.get("next_review_date") > agent.today_str()
        )
        if future:
            st.info(f"下一次复习：{future[0]}")
    else:
        st.info(f"今天到期：{len(due)} 道")
        q = agent.current_question if agent.wrong_review_mode else None

        if not q:
            if st.button("▶️ 开始错题复习", type="primary"):
                try:
                    agent.start_wrong_review()
                    st.rerun()
                except Exception as e:
                    st.error(f"开始复习失败：{e}")
        else:
            q = agent.normalize_question(q)
            st.markdown("### 错题")
            st.write(q.get("question", ""))
            opts = q.get("options", {})
            answer = st.radio(
                "选择答案",
                ["A", "B", "C", "D"],
                format_func=lambda x: f"{x}. {opts.get(x, '')}",
                key="review_answer",
            )
            if st.button("提交复习答案", type="primary"):
                before_q = dict(q)
                is_correct = answer == str(before_q.get("correct_answer", "")).upper()
                try:
                    agent.grade_answer(answer, review=True)
                    sync_learning_record(before_q, answer, is_correct, "wrong_review")
                    if not is_correct:
                        sync_wrong_question(before_q, answer)
                    st.success("复习结果已保存。")
                    st.rerun()
                except Exception as e:
                    st.error(f"复习失败：{e}")

# ---------- 自适应分析 ----------
elif menu == "🧠 自适应分析":
    st.subheader("🧠 AI 自适应学习分析")
    status = agent.calculate_learning_status()

    if not status:
        st.info("先完成几道题，系统会建立学习画像。")
    else:
        st.dataframe(
            [
                {
                    "知识点": x["knowledge_point"],
                    "答题数": x["total"],
                    "正确率": x["accuracy"],
                    "掌握度": x["mastery"],
                    "未掌握错题": x["wrong_questions"],
                    "优先级": x["priority"],
                }
                for x in status
            ],
            use_container_width=True,
            hide_index=True,
        )
        top = status[0]
        st.success(
            f"🎯 当前优先强化：{top['knowledge_point']}｜"
            f"掌握度 {top['mastery']}%｜正确率 {top['accuracy']}%"
        )
        if st.button("🔄 根据最新数据重新制定今天计划"):
            try:
                plan = agent.create_dynamic_study_plan(True)
                sync_today_plan(plan)
                st.success("计划已重新制定。")
            except Exception as e:
                st.error(f"重新制定计划失败：{e}")

# ---------- 学习报告 ----------
elif menu == "📊 学习报告":
    st.subheader("📊 学习报告")
    report = agent.learning_report()
    a, b, c, d = st.columns(4)
    a.metric("今日任务", f"{report['tasks_done']}/{report['tasks_total']}")
    b.metric("今日学习", f"{report['minutes']} 分钟")
    c.metric("今日做题", report["today"]["questions"])
    d.metric("正确率", f"{report['today']['accuracy']:.1f}%")

    st.divider()
    st.write(f"**当前未掌握错题：** {report['wrong_count']}　　**今日待复习：** {report['due_count']}")

    if report["status"]:
        st.dataframe(
            [
                {
                    "知识点": x["knowledge_point"],
                    "正确率": x["accuracy"],
                    "掌握度": x["mastery"],
                    "答题数": x["total"],
                    "未掌握错题": x["wrong_questions"],
                }
                for x in report["status"]
            ],
            use_container_width=True,
            hide_index=True,
        )

# ---------- AI知识库问答 ----------
elif menu == "💬 AI知识库问答":
    st.subheader("💬 AI知识库问答")
    query = st.text_area(
        "输入你的问题",
        placeholder="例如：结构化方法是什么？黑盒测试和白盒测试有什么区别？",
        height=120,
    )

    if st.button("🔎 查询知识库并回答", type="primary"):
        if not query.strip():
            st.warning("请先输入问题。")
        else:
            with st.spinner("正在检索知识库..."):
                try:
                    ctx = agent.search_knowledge(query, 5)
                    answer = agent.ai(
                        f"""请根据下面的软件设计师知识库回答用户问题。
优先依据知识库，不要编造资料中没有的信息；资料不足时明确说明。
最后给出“考试记忆点”。

用户问题：
{query}

知识库：
{ctx}"""
                    )
                    st.markdown("### 🤖 AI回答")
                    st.write(answer)
                    with st.expander("📚 查看本次检索到的知识"):
                        st.text(ctx)
                except Exception as e:
                    st.error(f"问答失败：{e}")

st.divider()
st.caption("软件设计师 AI 自适应学习 Agent · RAG + DeepSeek + ChromaDB + BGE + Supabase")
