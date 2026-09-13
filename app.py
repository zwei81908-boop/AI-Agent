import os
import streamlit as st

import agent

# ============================================================
# V33：最终稳定优化版｜性能 + 去重 + 云端同步优化
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    import cloud_rag
    agent.search_knowledge = cloud_rag.search_knowledge
    CLOUD_RAG_READY = True
    CLOUD_RAG_ERROR = ""
except Exception as e:
    CLOUD_RAG_READY = False
    CLOUD_RAG_ERROR = str(e)

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
    CLOUD_DB_ERROR = ""
except Exception as e:
    CLOUD_DB_READY = False
    CLOUD_DB_ERROR = str(e)

try:
    import knowledge_manager
    KNOWLEDGE_MANAGER_READY = True
except Exception as e:
    KNOWLEDGE_MANAGER_READY = False
    KNOWLEDGE_MANAGER_ERROR = str(e)

st.set_page_config(
    page_title="软件设计师 AI 自适应学习 Agent",
    page_icon="🤖",
    layout="wide",
)

# ============================================================
# 缓存
# ============================================================

@st.cache_data(ttl=20, show_spinner=False)
def cached_learning_records():
    if not CLOUD_DB_READY:
        return []
    return get_cloud_learning_records(500)

@st.cache_data(ttl=20, show_spinner=False)
def cached_wrong_questions():
    if not CLOUD_DB_READY:
        return []
    return get_cloud_wrong_questions(500)

@st.cache_data(ttl=20, show_spinner=False)
def cached_daily_tasks(task_date):
    if not CLOUD_DB_READY:
        return []
    return get_cloud_daily_tasks(task_date)

@st.cache_data(ttl=10, show_spinner=False)
def cached_learning_status():
    return agent.calculate_learning_status()

def reset_training_state():
    """V33：统一清理专项训练状态，防止上一题答案残留。"""
    for key in (
        "training_question", "training_submitted", "last_result",
        "training_answer_v33", "training_answer_v33", "training_answer",
    ):
        st.session_state.pop(key, None)
    st.session_state.training_question = None
    st.session_state.training_submitted = False
    st.session_state.last_result = None


def is_question_exhausted_error(exc):
    text = str(exc)
    return any(k in text for k in (
        "没有新的", "没有可用", "题目已耗尽", "新题", "Exhausted", "exhausted"
    ))


def get_training_question(topic):
    q = agent.start_training(topic)
    if not q:
        q = getattr(agent, "current_question", None)
    if not q:
        raise RuntimeError("AI没有返回题目")
    return agent.normalize_question(q)


def clear_cloud_cache():
    cached_learning_records.clear()
    cached_wrong_questions.clear()
    cached_daily_tasks.clear()
    cached_learning_status.clear()

# ============================================================
# 样式
# ============================================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg,#f7fbff 0%,#eef5fb 100%);
    color:#18324f;
}
.block-container {
    max-width:1450px;
    padding-top:1.2rem;
    padding-bottom:2rem;
}
h1,h2,h3 { color:#163b68 !important; }
.hero {
    padding:24px 28px;
    border-radius:18px;
    border:1px solid #d7e8f8;
    background:linear-gradient(120deg,#eaf6ff 0%,#fff 58%,#eaf3ff 100%);
    box-shadow:0 8px 28px rgba(37,99,155,.08);
    margin-bottom:18px;
}
.stButton > button {
    border-radius:10px;
    font-weight:600;
}
div[data-testid="stMetric"] {
    background:#fff;
    border:1px solid #dceaf6;
    border-radius:14px;
    padding:14px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<div style="font-size:30px;font-weight:800;color:#173d6b;">
🤖 软件设计师 AI 自适应学习 Agent
</div>
<div style="color:#607d9d;font-size:15px;margin-top:8px;">
AI个性化学习 · 智能出题 · 错题复习 · RAG知识库 · Supabase云端数据
</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 同步函数
# ============================================================

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
        cached_learning_records.clear()
        cached_learning_status.clear()
    except Exception as e:
        st.warning(f"学习记录云端同步失败：{e}")

def sync_wrong_question(q, user_answer):
    if not CLOUD_DB_READY:
        return
    try:
        save_cloud_wrong_question(
            question=q.get("question", ""),
            options=[
                q.get("A", q.get("options", {}).get("A", "")),
                q.get("B", q.get("options", {}).get("B", "")),
                q.get("C", q.get("options", {}).get("C", "")),
                q.get("D", q.get("options", {}).get("D", "")),
            ],
            correct_answer=q.get("correct_answer", ""),
            user_answer=user_answer,
            explanation=q.get("explanation", ""),
            topic=q.get("knowledge_point", q.get("topic", "未分类")),
        )
        cached_wrong_questions.clear()
        cached_learning_status.clear()
    except Exception as e:
        st.warning(f"错题云端同步失败：{e}")

def sync_today_plan(plan):
    if not CLOUD_DB_READY or not plan:
        return
    try:
        task_date = plan.get("date", agent.today_str())
        existing = cached_daily_tasks(task_date)
        existing_indexes = {
            int(x.get("task_index"))
            for x in existing
            if str(x.get("task_index", "")).isdigit()
        }
        for i, task in enumerate(plan.get("tasks", []), 1):
            if i in existing_indexes:
                continue
            save_daily_task(
                task_date=task_date,
                task_index=i,
                task_content=task.get("name", f"任务{i}"),
                completed=bool(task.get("completed")),
            )
        cached_daily_tasks.clear()
    except Exception as e:
        st.warning(f"每日任务云端同步失败：{e}")

def sync_task_completion(plan, task_number):
    if not CLOUD_DB_READY or not plan:
        return
    try:
        rows = get_cloud_daily_tasks(plan.get("date", agent.today_str()))
        target = next(
            (
                x for x in rows
                if int(x.get("task_index", -1)) == int(task_number)
            ),
            None,
        )
        if target:
            complete_daily_task(target["id"])
            clear_cloud_cache()
    except Exception as e:
        st.warning(f"任务完成状态云端同步失败：{e}")

# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.markdown("## 🎓 AI 学习助手")
    st.caption("软件设计师 AI 自适应学习 Agent")
    st.divider()

    menu = st.radio(
        "选择功能",
        [
            "📅 今日任务",
            "📝 AI专项训练",
            "❌ 错题复习",
            "📊 错题分析",
            "🧠 自适应分析",
            "📊 学习报告",
            "💬 AI知识库问答",
            "📚 知识库管理",
        ],
    )

    st.divider()
    st.caption(
        "🟢 云端数据库已连接"
        if CLOUD_DB_READY
        else f"🟡 云端数据库不可用：{CLOUD_DB_ERROR}"
    )
    st.caption(
        "🧠 云端 RAG：已连接"
        if CLOUD_RAG_READY
        else f"🟡 云端 RAG：不可用 {CLOUD_RAG_ERROR}"
    )

# ============================================================
# 今日任务
# ============================================================

if menu == "📅 今日任务":
    st.subheader("📅 今日学习任务")

    plan = agent.get_today_tasks()

    if not plan:
        if st.button("🤖 AI生成今日计划", type="primary"):
            with st.spinner("正在分析学习数据并制定计划..."):
                try:
                    plan = agent.create_dynamic_study_plan()
                    sync_today_plan(plan)
                    st.success("今日学习计划已生成。")
                    st.rerun()
                except Exception as e:
                    st.error(f"生成计划失败：{e}")

    plan = agent.get_today_tasks()

    if plan:
        st.info(f"🔔 今日目标：{plan.get('goal', '完成今日核心学习任务')}")

        for i, task in enumerate(plan.get("tasks", []), 1):
            done = bool(task.get("completed"))
            c1, c2 = st.columns([5, 1])

            with c1:
                st.markdown(
                    f"{'✅' if done else '⬜'} **任务{i}："
                    f"{task.get('name', f'任务{i}')}**"
                )
                if task.get("minutes"):
                    st.caption(f"{task['minutes']} 分钟")
                if task.get("description"):
                    st.write(task["description"])

            with c2:
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

# ============================================================
# AI专项训练 V32
# ============================================================

elif menu == "📝 AI专项训练":
    st.subheader("📝 AI专项训练")
    st.caption("先答题，提交后才显示正确答案和解析。")

    if "training_question" not in st.session_state:
        st.session_state.training_question = None
    if "training_submitted" not in st.session_state:
        st.session_state.training_submitted = False
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "training_topic" not in st.session_state:
        st.session_state.training_topic = ""

    default_topic = st.session_state.get(
        "training_topic"
    ) or agent.choose_adaptive_topic()

    topic = st.text_input(
        "训练知识点",
        value=default_topic,
        placeholder="例如：软件测试、数据结构、软件开发方法",
        key="training_topic_input",
    )

    if st.button("🎯 生成一道题", type="primary"):
        reset_training_state()
        st.session_state.training_topic = topic.strip() or default_topic

        with st.spinner("正在生成题目，请稍候..."):
            try:
                st.session_state.training_question = get_training_question(
                    st.session_state.training_topic
                )
                st.rerun()
            except Exception as e:
                if is_question_exhausted_error(e):
                    st.warning(f"📭 {e}")
                else:
                    st.error(f"出题失败：{e}")

    q = st.session_state.get("training_question")

    if q:
        st.markdown("### 📖 题目")
        st.write(q.get("question", ""))

        opts = q.get("options", {})
        if not isinstance(opts, dict):
            opts = {}

        answer_key = "training_answer_v33"
        if st.session_state.training_submitted:
            answer = st.session_state.get(answer_key, "A")
        else:
            answer = st.radio(
                "选择答案",
                ["A", "B", "C", "D"],
                format_func=lambda x: f"{x}. {opts.get(x, '')}",
                key=answer_key,
            )

        if not st.session_state.training_submitted:
            if st.button("提交答案", type="primary"):
                before_q = dict(q)
                is_correct = (
                    answer.upper()
                    == str(before_q.get("correct_answer", "")).upper()
                )

                try:
                    agent.current_question = before_q

                    # V32：禁止提交后自动生成下一题。
                    # 新版 agent.py 支持 advance=False；
                    # 老版 agent.py 则通过关闭 training_mode 兼容。
                    try:
                        agent.grade_answer(answer, advance=False)
                    except TypeError:
                        old_training_mode = getattr(agent, "training_mode", False)
                        try:
                            agent.training_mode = False
                            agent.grade_answer(answer)
                        finally:
                            agent.training_mode = old_training_mode

                    # V33：agent.grade_answer 已负责本地 + 云端保存，避免重复写入 Supabase。
                    clear_cloud_cache()

                    st.session_state.training_submitted = True
                    st.session_state.last_result = is_correct
                    st.rerun()

                except Exception as e:
                    st.error(f"答题失败：{e}")

        else:
            correct = str(q.get("correct_answer", "")).upper()

            if st.session_state.last_result:
                st.success("🎉 回答正确！学习记录已保存。")
            else:
                st.error("❌ 回答错误！错题和学习记录已保存。")

            st.markdown(f"### ✅ 正确答案：**{correct}**")

            if opts.get(correct):
                st.write(f"**{correct}. {opts.get(correct)}**")

            explanation = q.get("explanation", "")
            if explanation:
                st.info(f"📖 **解析：** {explanation}")

            st.divider()

            if st.button("➡️ 下一题", type="primary"):
                st.session_state.training_question = None
                st.session_state.training_submitted = False
                st.session_state.last_result = None
                st.session_state.pop("training_answer_v33", None)

                with st.spinner("正在生成下一题..."):
                    try:
                        agent.start_training(
                            st.session_state.training_topic
                        )
                        new_q = getattr(agent, "current_question", None)
                        if not new_q:
                            raise RuntimeError("没有生成新的题目")

                        st.session_state.training_question = agent.normalize_question(new_q)
                        st.rerun()

                    except Exception as e:
                        if "没有新的" in str(e) or "新题" in str(e) or "Exhausted" in str(e):
                            st.warning(str(e))
                        else:
                            st.error(f"生成下一题失败：{e}")

# ============================================================
# 错题复习
# ============================================================

elif menu == "❌ 错题复习":
    st.subheader("❌ 错题复习")

    due = agent.get_due_wrong_questions()

    if not due and CLOUD_DB_READY:
        cloud_all = cached_wrong_questions()
        if cloud_all:
            # 尽量让本地算法使用最新云端错题
            local_wrong = []
            for r in cloud_all:
                opts = r.get("options") or {}
                if isinstance(opts, list):
                    opts = {
                        k: opts[i] if i < len(opts) else ""
                        for i, k in enumerate("ABCD")
                    }
                local_wrong.append({
                    "question": r.get("question", ""),
                    "A": opts.get("A", ""),
                    "B": opts.get("B", ""),
                    "C": opts.get("C", ""),
                    "D": opts.get("D", ""),
                    "options": opts,
                    "correct_answer": r.get("correct_answer", "A"),
                    "explanation": r.get("explanation", ""),
                    "knowledge_point": r.get("topic", "未分类"),
                    "user_answer": r.get("user_answer", ""),
                    "first_wrong_at": r.get("created_at", ""),
                    "last_wrong_at": r.get("created_at", ""),
                    "review_level": int(r.get("review_count", 0) or 0),
                    "consecutive_correct": int(r.get("review_count", 0) or 0),
                    "next_review_date": str(
                        r.get("next_review_at", "")
                    )[:10] or agent.today_str(),
                    "mastered": bool(r.get("mastered")),
                })

            with open(
                os.path.join(BASE_DIR, "wrong_questions.json"),
                "w",
                encoding="utf-8",
            ) as f:
                import json
                json.dump(local_wrong, f, ensure_ascii=False, indent=2)

            due = agent.get_due_wrong_questions()

    if not due:
        st.success("🎉 今天没有到期错题。")
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
                key="review_answer_v32",
            )

            if st.button("提交复习答案", type="primary"):
                before_q = dict(q)
                is_correct = (
                    answer.upper()
                    == str(before_q.get("correct_answer", "")).upper()
                )

                try:
                    try:
                        agent.grade_answer(
                            answer,
                            review=True,
                            advance=False,
                        )
                    except TypeError:
                        agent.grade_answer(answer, review=True)

                    # V33：agent.grade_answer 已负责本地 + 云端保存，避免重复写入 Supabase。
                    clear_cloud_cache()
                    st.success("复习结果已保存。")
                    st.rerun()

                except Exception as e:
                    st.error(f"复习失败：{e}")

# ============================================================
# 错题分析
# ============================================================

elif menu == "📊 错题分析":
    st.subheader("📊 错题分析")

    try:
        analysis = agent.analyze_wrong_questions()
    except Exception as e:
        st.error(f"错题分析失败：{e}")
        analysis = None

    if analysis:
        total = analysis.get("total", 0)
        due = analysis.get("due_count", 0)

        c1, c2 = st.columns(2)
        c1.metric("错题总数", total)
        c2.metric("今日待复习", due)

        points = analysis.get("knowledge_points", [])

        if points:
            st.markdown("### 🎯 薄弱知识点")

            rows = []
            for x in points:
                rows.append({
                    "知识点": x.get("knowledge_point", "未分类"),
                    "错题数": x.get("count", 0),
                    "正确率": x.get("accuracy", "-"),
                    "掌握度": x.get("mastery", "-"),
                    "优先级": x.get("priority", "-"),
                })

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True,
            )

            recommendation = analysis.get("recommendation")
            if recommendation:
                st.info(f"💡 {recommendation}")
        else:
            st.success("🎉 暂时没有错题，继续保持！")

# ============================================================
# 自适应分析
# ============================================================

elif menu == "🧠 自适应分析":
    st.subheader("🧠 AI 自适应学习分析")

    try:
        status = cached_learning_status()
    except Exception as e:
        st.error(f"学习状态分析失败：{e}")
        status = []

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
                st.rerun()
            except Exception as e:
                st.error(f"重新制定计划失败：{e}")

# ============================================================
# 学习报告
# ============================================================

elif menu == "📊 学习报告":
    st.subheader("📊 学习报告")

    try:
        report = agent.learning_report()
    except Exception as e:
        st.error(f"学习报告生成失败：{e}")
        report = None

    if report:
        a, b, c, d = st.columns(4)
        a.metric(
            "今日任务",
            f"{report['tasks_done']}/{report['tasks_total']}",
        )
        b.metric("今日学习", f"{report['minutes']} 分钟")
        c.metric("今日做题", report["today"]["questions"])
        d.metric("正确率", f"{report['today']['accuracy']:.1f}%")

        st.divider()

        st.write(
            f"**当前未掌握错题：** {report['wrong_count']}　　"
            f"**今日待复习：** {report['due_count']}"
        )

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

# ============================================================
# AI知识库问答
# ============================================================

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
            with st.spinner("正在检索知识库并生成回答..."):
                try:
                    ctx = agent.search_knowledge(query, 3)
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

                    st.markdown("### 🤖 AI回答")
                    st.write(answer)

                    with st.expander("📚 查看本次检索到的知识"):
                        st.text(ctx)

                except Exception as e:
                    st.error(f"问答失败：{e}")

# ============================================================
# 知识库管理
# ============================================================

elif menu == "📚 知识库管理":
    st.title("📚 知识库管理")

    if not KNOWLEDGE_MANAGER_READY:
        st.error(f"知识库管理模块加载失败：{KNOWLEDGE_MANAGER_ERROR}")
        st.stop()

    km = knowledge_manager

    st.caption("☁️ Supabase 云端知识库 + 本地知识库缓存")

    try:
        cloud_files = km.get_cloud_knowledge_files()
        if not isinstance(cloud_files, list):
            cloud_files = []
    except Exception as e:
        cloud_files = []
        st.warning(f"云端知识库暂时无法读取：{e}")

    try:
        local_files = km.get_knowledge_files()
    except Exception:
        local_files = []

    try:
        chroma_status = km.get_chroma_status()
    except Exception:
        chroma_status = {}

    c1, c2, c3 = st.columns(3)
    c1.metric("☁️ 云端资料", len(cloud_files))
    c2.metric("💻 本地资料", len(local_files))
    c3.metric(
        "🧠 RAG知识块",
        chroma_status.get("documents", 0),
    )

    st.divider()
    st.subheader("☁️ 云端学习资料")

    if not cloud_files:
        st.info("当前 Supabase 云端知识库还没有资料。")
    else:
        for index, item in enumerate(cloud_files, 1):
            if not isinstance(item, dict):
                continue

            name = item.get("file_name", "未知文件")
            size = item.get("file_size", 0)
            status = item.get("status", "uploaded")
            created = item.get("created_at", "")

            size_text = (
                f"{size / 1024 / 1024:.2f} MB"
                if size else "未知大小"
            )

            col1, col2 = st.columns([5, 1])

            with col1:
                st.write(f"**{index}. {name}**")
                st.caption(f"{size_text} · {status} · {created}")

            with col2:
                document_id = item.get("id")
                if document_id is not None:
                    if st.button(
                        "🗑️ 删除",
                        key=f"delete_cloud_{document_id}",
                    ):
                        try:
                            result = km.delete_cloud_knowledge_file(
                                document_id
                            )
                            if result.get("success"):
                                st.success("云端文件已删除")
                                st.rerun()
                            else:
                                st.error(
                                    result.get("message", "删除失败")
                                )
                        except Exception as e:
                            st.error(f"删除失败：{e}")

    st.divider()
    st.subheader("📤 上传学习资料")

    uploaded_files = st.file_uploader(
        "选择 PDF / TXT 学习资料",
        type=["pdf", "txt"],
        accept_multiple_files=True,
        help="支持一次选择多个 PDF / TXT 文件",
    )

    if uploaded_files and st.button(
        "☁️ 上传到云端知识库",
        type="primary",
        use_container_width=True,
    ):
        progress = st.progress(0)
        total = len(uploaded_files)
        success_count = 0
        duplicate_count = 0
        fail_count = 0

        for index, uploaded_file in enumerate(uploaded_files, 1):
            try:
                result = km.upload_to_cloud(
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                )

                if result.get("success"):
                    if result.get("duplicate"):
                        duplicate_count += 1
                    else:
                        success_count += 1

                    try:
                        km.save_uploaded_file(uploaded_file)
                    except Exception as local_error:
                        st.warning(
                            f"{uploaded_file.name} 本地缓存失败："
                            f"{local_error}"
                        )
                else:
                    fail_count += 1
                    st.error(
                        f"{uploaded_file.name} 上传失败："
                        f"{result.get('message', '未知错误')}"
                    )

            except Exception as e:
                fail_count += 1
                st.error(f"{uploaded_file.name} 处理失败：{e}")

            progress.progress(index / total)

        st.success(
            f"上传完成：成功 {success_count}，"
            f"重复 {duplicate_count}，失败 {fail_count}"
        )
        st.rerun()

    st.divider()
    st.subheader("🧠 RAG 重建")

    if st.button(
        "🔄 重新构建 RAG 知识库",
        use_container_width=True,
    ):
        with st.spinner("正在构建 RAG，请稍候..."):
            try:
                result = km.rebuild_knowledge_base()
            except Exception as e:
                result = {"success": False, "output": str(e)}

        if result.get("success"):
            st.success("🎉 RAG 知识库构建完成！")
            output = result.get("output", "")
            if output:
                with st.expander("📋 查看构建日志"):
                    st.code(output, language="text")
        else:
            st.error("❌ RAG 知识库构建失败")
            st.code(
                result.get("output", "未知错误"),
                language="text",
            )

# ============================================================
# 页脚
# ============================================================

st.divider()
st.caption(
    "软件设计师 AI 自适应学习 Agent · "
    "RAG + DeepSeek + ChromaDB + BGE + Supabase · V32"
)
