import streamlit as st
from datetime import datetime, date, timedelta
from collections import defaultdict


# =========================================================
# V13 学习数据看板
# =========================================================

try:
    from database import (
        get_all_learning_records,
        get_all_wrong_questions,
        get_all_daily_tasks,
    )

    CLOUD_READY = True

except Exception:
    CLOUD_READY = False


def load_learning_records():
    if not CLOUD_READY:
        return []

    try:
        return get_all_learning_records(1000)
    except Exception:
        return []


def load_wrong_questions():
    if not CLOUD_READY:
        return []

    try:
        return get_all_wrong_questions(1000)
    except Exception:
        return []


def load_daily_tasks():
    if not CLOUD_READY:
        return []

    try:
        return get_all_daily_tasks(1000)
    except Exception:
        return []


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).date()
    except Exception:
        try:
            return date.fromisoformat(str(value)[:10])
        except Exception:
            return None


def render_dashboard():

    st.subheader("📊 V13 学习数据驾驶舱")

    records = load_learning_records()
    wrong_questions = load_wrong_questions()
    tasks = load_daily_tasks()

    # =====================================================
    # 基础数据
    # =====================================================

    total_questions = len(records)

    correct_questions = sum(
        1
        for r in records
        if isinstance(r, dict)
        and bool(r.get("is_correct"))
    )

    wrong_count = len(wrong_questions)

    accuracy = (
        correct_questions / total_questions * 100
        if total_questions
        else 0
    )

    # =====================================================
    # 今日数据
    # =====================================================

    today = date.today()

    today_records = [
        r for r in records
        if parse_date(r.get("created_at")) == today
    ]

    today_questions = len(today_records)

    today_correct = sum(
        1
        for r in today_records
        if bool(r.get("is_correct"))
    )

    today_accuracy = (
        today_correct / today_questions * 100
        if today_questions
        else 0
    )

    # =====================================================
    # 今日任务
    # =====================================================

    today_tasks = [
        t for t in tasks
        if parse_date(t.get("task_date")) == today
    ]

    today_tasks_total = len(today_tasks)

    today_tasks_done = sum(
        1
        for t in today_tasks
        if bool(t.get("completed"))
    )

    task_rate = (
        today_tasks_done / today_tasks_total * 100
        if today_tasks_total
        else 0
    )

    # =====================================================
    # 第一行核心指标
    # =====================================================

    st.markdown("### 📌 核心学习数据")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "累计做题",
        total_questions,
    )

    c2.metric(
        "累计正确率",
        f"{accuracy:.1f}%",
    )

    c3.metric(
        "未掌握错题",
        wrong_count,
    )

    c4.metric(
        "今日做题",
        today_questions,
    )

    st.divider()

    # =====================================================
    # 第二行
    # =====================================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "今日正确率",
        f"{today_accuracy:.1f}%",
    )

    c2.metric(
        "今日任务",
        f"{today_tasks_done}/{today_tasks_total}",
    )

    c3.metric(
        "任务完成率",
        f"{task_rate:.1f}%",
    )

    c4.metric(
        "学习天数",
        len(
            set(
                parse_date(r.get("created_at"))
                for r in records
                if parse_date(r.get("created_at"))
            )
        ),
    )

    st.divider()

    # =====================================================
    # 7日学习趋势
    # =====================================================

    st.markdown("### 📈 最近 7 天学习趋势")

    trend = {}

    for i in range(6, -1, -1):

        d = today - timedelta(days=i)

        day_records = [
            r for r in records
            if parse_date(r.get("created_at")) == d
        ]

        total = len(day_records)

        correct = sum(
            1
            for r in day_records
            if bool(r.get("is_correct"))
        )

        rate = (
            correct / total * 100
            if total
            else 0
        )

        trend[d.strftime("%m-%d")] = rate

    st.line_chart(
        {
            "正确率": trend
        },
        use_container_width=True,
    )

    # =====================================================
    # 每日做题量
    # =====================================================

    question_trend = {}

    for i in range(6, -1, -1):

        d = today - timedelta(days=i)

        count = sum(
            1
            for r in records
            if parse_date(r.get("created_at")) == d
        )

        question_trend[d.strftime("%m-%d")] = count

    st.line_chart(
        {
            "做题量": question_trend
        },
        use_container_width=True,
    )

    st.divider()

    # =====================================================
    # 知识点掌握度
    # =====================================================

    st.markdown("### 🧠 知识点掌握度")

    topic_data = defaultdict(
        lambda: {
            "total": 0,
            "correct": 0,
        }
    )

    for r in records:

        if not isinstance(r, dict):
            continue

        topic = (
            r.get("topic")
            or r.get("knowledge_point")
            or "未分类"
        )

        topic_data[topic]["total"] += 1

        if bool(r.get("is_correct")):
            topic_data[topic]["correct"] += 1

    topic_rows = []

    for topic, data in topic_data.items():

        total = data["total"]
        correct = data["correct"]

        mastery = (
            correct / total * 100
            if total
            else 0
        )

        if mastery < 60:
            level = "🔴 薄弱"

        elif mastery < 80:
            level = "🟡 一般"

        else:
            level = "🟢 较好"

        topic_rows.append(
            {
                "知识点": topic,
                "练习次数": total,
                "正确次数": correct,
                "掌握度": round(mastery, 1),
                "状态": level,
            }
        )

    topic_rows.sort(
        key=lambda x: x["掌握度"]
    )

    if topic_rows:

        st.dataframe(
            topic_rows,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "完成一些 AI 专项训练后，这里会自动形成知识点画像。"
        )

    st.divider()

    # =====================================================
    # AI强化建议
    # =====================================================

    st.markdown("### 🎯 V13 智能强化建议")

    if topic_rows:

        weak_topics = [
            x for x in topic_rows
            if x["掌握度"] < 60
        ]

        if weak_topics:

            st.warning(
                "系统检测到以下知识点需要优先强化："
            )

            for item in weak_topics[:5]:

                st.write(
                    f"🔴 **{item['知识点']}**"
                    f"　掌握度：{item['掌握度']}%"
                    f"　练习：{item['练习次数']} 次"
                )

        else:

            st.success(
                "🎉 当前没有明显低于 60% 掌握度的知识点，继续保持！"
            )

    # =====================================================
    # 错题分析
    # =====================================================

    st.markdown("### ❌ 错题分布")

    wrong_topics = defaultdict(int)

    for q in wrong_questions:

        if not isinstance(q, dict):
            continue

        topic = (
            q.get("topic")
            or q.get("knowledge_point")
            or "未分类"
        )

        wrong_topics[topic] += 1

    wrong_rows = [
        {
            "知识点": topic,
            "错题数量": count,
        }
        for topic, count
        in sorted(
            wrong_topics.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    if wrong_rows:

        st.dataframe(
            wrong_rows,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.success("🎉 当前没有未掌握错题。")

    # =====================================================
    # 任务完成情况
    # =====================================================

    st.markdown("### 📅 学习任务完成情况")

    if today_tasks:

        for i, task in enumerate(
            today_tasks,
            1
        ):

            status = (
                "✅ 已完成"
                if task.get("completed")
                else "⬜ 未完成"
            )

            content = task.get(
                "task_content",
                f"任务{i}"
            )

            st.write(
                f"**任务{i}**　{status}　{content}"
            )

    else:

        st.info(
            "今天还没有云端任务记录。"
        )

    # =====================================================
    # 数据刷新
    # =====================================================

    st.divider()

    if st.button(
        "🔄 刷新 V13 数据",
        type="primary",
    ):

        st.rerun()

    st.caption(
        "V13 学习数据驾驶舱 · Supabase 云端数据"
    )