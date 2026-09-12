import os
import time
from datetime import date

from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta


# =========================================================
# 基础配置
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


USER_ID = "default_user"


# =========================================================
# Supabase 客户端
# =========================================================

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError(
            "未配置 SUPABASE_URL 或 SUPABASE_KEY"
        )

    return create_client(url, key)


# =========================================================
# 通用重试
# =========================================================

def _execute_with_retry(operation, retries=3, delay=0.8):
    last_error = None

    for attempt in range(retries):
        try:
            return operation()

        except Exception as e:
            last_error = e

            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))

    raise last_error


# =========================================================
# 学习记录
# =========================================================

def save_learning_record(
    topic,
    question,
    answer,
    is_correct,
    score=0
):
    client = get_supabase()

    data = {
        "user_id": USER_ID,
        "topic": topic,
        "question": question,
        "answer": answer,
        "is_correct": bool(is_correct),
        "score": int(score or 0),
    }

    return _execute_with_retry(
        lambda: client
        .table("learning_records")
        .insert(data)
        .execute()
    )


def get_learning_records(limit=500):
    client = get_supabase()

    return _execute_with_retry(
        lambda: (
            client
            .table("learning_records")
            .select("*")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    ).data


# =========================================================
# 错题
# =========================================================

def save_wrong_question(
    question,
    correct_answer,
    user_answer,
    explanation,
    topic,
    options=None,
):
    client = get_supabase()

    existing = _execute_with_retry(
        lambda: (
            client
            .table("wrong_questions")
            .select("id")
            .eq("user_id", USER_ID)
            .eq("question", question)
            .limit(1)
            .execute()
        )
    ).data

    data = {
        "user_id": USER_ID,
        "question": question,
        "options": options or [],
        "correct_answer": correct_answer,
        "user_answer": user_answer,
        "explanation": explanation,
        "topic": topic,
        "review_count": 0,
        "next_review_at": date.today().isoformat(),
        "mastered": False,
    }

    if existing:
        return _execute_with_retry(
            lambda: (
                client
                .table("wrong_questions")
                .update({
                    "user_answer": user_answer,
                    "explanation": explanation,
                    "topic": topic,
                    "options": options or [],
                    "correct_answer": correct_answer,
                    "next_review_at": date.today().isoformat(),
                    "mastered": False,
                })
                .eq("id", existing[0]["id"])
                .execute()
            )
        )

    return _execute_with_retry(
        lambda: (
            client
            .table("wrong_questions")
            .insert(data)
            .execute()
        )
    )


def get_wrong_questions(limit=500):
    client = get_supabase()

    return _execute_with_retry(
        lambda: (
            client
            .table("wrong_questions")
            .select("*")
            .eq("user_id", USER_ID)
            .eq("mastered", False)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    ).data


# =========================================================
# 错题复习
# =========================================================

def update_wrong_question_review(
    question_id,
    review_count,
    next_review_at,
    mastered=False,
):
    client = get_supabase()

    return _execute_with_retry(
        lambda: (
            client
            .table("wrong_questions")
            .update({
                "review_count": int(review_count),
                "next_review_at": next_review_at,
                "mastered": bool(mastered),
            })
            .eq("id", question_id)
            .eq("user_id", USER_ID)
            .execute()
        )
    )


# =========================================================
# 每日任务
# =========================================================

def save_daily_task(
    task_date,
    task_index,
    task_content,
    completed=False
):
    client = get_supabase()

    existing = _execute_with_retry(
        lambda: (
            client
            .table("daily_tasks")
            .select("id")
            .eq("user_id", USER_ID)
            .eq("task_date", task_date)
            .eq("task_index", int(task_index))
            .limit(1)
            .execute()
        )
    ).data

    data = {
        "user_id": USER_ID,
        "task_date": task_date,
        "task_index": int(task_index),
        "task_content": task_content,
        "completed": bool(completed),
    }

    if existing:
        return _execute_with_retry(
            lambda: (
                client
                .table("daily_tasks")
                .update({
                    "task_content": task_content,
                    "completed": bool(completed),
                })
                .eq("id", existing[0]["id"])
                .execute()
            )
        )

    return _execute_with_retry(
        lambda: (
            client
            .table("daily_tasks")
            .insert(data)
            .execute()
        )
    )


def get_daily_tasks(
    task_date=None,
    limit=100
):
    client = get_supabase()

    query = (
        client
        .table("daily_tasks")
        .select("*")
        .eq("user_id", USER_ID)
        .order("task_index")
        .limit(limit)
    )

    if task_date:
        query = query.eq("task_date", task_date)

    return _execute_with_retry(
        lambda: query.execute()
    ).data


def complete_daily_task(task_id):
    client = get_supabase()

    return _execute_with_retry(
        lambda: (
            client
            .table("daily_tasks")
            .update({"completed": True})
            .eq("id", task_id)
            .eq("user_id", USER_ID)
            .execute()
        )
    )


# =========================================================
# 云端健康检查
# =========================================================

def check_cloud_database():
    try:
        client = get_supabase()

        _execute_with_retry(
            lambda: (
                client
                .table("learning_records")
                .select("id")
                .limit(1)
                .execute()
            )
        )

        return True, "Supabase 连接正常"

    except Exception as e:
        return False, str(e)



def review_wrong_question(
    question_id,
    is_correct,
    current_review_count=0
):
    """
    错题复习调度：

    答错：
        +1天

    答对：
        第1次 -> +3天
        第2次 -> +7天
        第3次 -> 掌握
    """

    if is_correct:
        if current_review_count >= 2:
            mastered = True
            next_review_at = None
            new_count = current_review_count + 1
        elif current_review_count == 1:
            mastered = False
            next_review_at = (
                datetime.now() + timedelta(days=7)
            ).date().isoformat()
            new_count = current_review_count + 1
        else:
            mastered = False
            next_review_at = (
                datetime.now() + timedelta(days=3)
            ).date().isoformat()
            new_count = current_review_count + 1

    else:
        mastered = False
        next_review_at = (
            datetime.now() + timedelta(days=1)
        ).date().isoformat()
        new_count = current_review_count

    return update_wrong_question_review(
        question_id=question_id,
        review_count=new_count,
        next_review_at=next_review_at,
        mastered=mastered,
    )
def get_all_learning_records(limit=1000):
    client = get_supabase()

    return _execute_with_retry(
        lambda: (
            client
            .table("learning_records")
            .select("*")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    ).data


def get_all_wrong_questions(limit=1000):
    client = get_supabase()

    return _execute_with_retry(
        lambda: (
            client
            .table("wrong_questions")
            .select("*")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
    ).data


def get_all_daily_tasks(limit=1000):
    client = get_supabase()

    return _execute_with_retry(
        lambda: (
            client
            .table("daily_tasks")
            .select("*")
            .eq("user_id", USER_ID)
            .order("task_date", desc=True)
            .order("task_index")
            .limit(limit)
            .execute()
        )
    ).data