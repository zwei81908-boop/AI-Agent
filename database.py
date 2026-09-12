import os
from datetime import date
from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError("未配置 SUPABASE_URL 或 SUPABASE_KEY")

    return create_client(url, key)


def save_learning_record(topic, question, answer, is_correct, score=0):
    client = get_supabase()
    data = {
        "user_id": "default_user",
        "topic": topic,
        "question": question,
        "answer": answer,
        "is_correct": bool(is_correct),
        "score": int(score or 0),
    }
    return client.table("learning_records").insert(data).execute()


def get_learning_records(limit=500):
    client = get_supabase()
    return (
        client.table("learning_records")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def save_wrong_question(
    question,
    correct_answer,
    user_answer,
    explanation,
    topic,
    options=None,
):
    client = get_supabase()

    # 个人项目阶段采用“同题更新”思路，避免重复写入同一道错题。
    existing = (
        client.table("wrong_questions")
        .select("id")
        .eq("user_id", "default_user")
        .eq("question", question)
        .limit(1)
        .execute()
        .data
    )

    data = {
        "user_id": "default_user",
        "question": question,
        "options": options or [],
        "correct_answer": correct_answer,
        "user_answer": user_answer,
        "explanation": explanation,
        "topic": topic,
        "review_count": 0,
        "mastered": False,
        # 新错题默认今天即可进入复习，避免 next_review_at 为 NULL 导致页面找不到错题。
        "next_review_at": date.today().isoformat(),
    }

    if existing:
        return (
            client.table("wrong_questions")
            .update({
                "user_answer": user_answer,
                "explanation": explanation,
                "topic": topic,
                "options": options or [],
                "correct_answer": correct_answer,
            })
            .eq("id", existing[0]["id"])
            .execute()
        )

    return client.table("wrong_questions").insert(data).execute()


def get_wrong_questions(limit=500):
    client = get_supabase()
    return (
        client.table("wrong_questions")
        .select("*")
        .eq("mastered", False)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def save_daily_task(task_date, task_index, task_content, completed=False):
    client = get_supabase()

    existing = (
        client.table("daily_tasks")
        .select("id")
        .eq("user_id", "default_user")
        .eq("task_date", task_date)
        .eq("task_index", int(task_index))
        .limit(1)
        .execute()
        .data
    )

    data = {
        "user_id": "default_user",
        "task_date": task_date,
        "task_index": int(task_index),
        "task_content": task_content,
        "completed": bool(completed),
    }

    if existing:
        return (
            client.table("daily_tasks")
            .update({
                "task_content": task_content,
                "completed": bool(completed),
            })
            .eq("id", existing[0]["id"])
            .execute()
        )

    return client.table("daily_tasks").insert(data).execute()


def get_daily_tasks(task_date=None, limit=100):
    client = get_supabase()
    query = (
        client.table("daily_tasks")
        .select("*")
        .eq("user_id", "default_user")
        .order("task_index")
        .limit(limit)
    )
    if task_date:
        query = query.eq("task_date", task_date)
    return query.execute().data


def complete_daily_task(task_id):
    client = get_supabase()
    return (
        client.table("daily_tasks")
        .update({"completed": True})
        .eq("id", task_id)
        .execute()
    )
