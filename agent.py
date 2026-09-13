import os, json, re, hashlib, time
from datetime import datetime, date, timedelta
from collections import Counter, defaultdict
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from database import (
    save_learning_record,
    get_learning_records,
    save_wrong_question as save_cloud_wrong_question,
    get_wrong_questions,
    save_daily_task,
    get_daily_tasks,
    complete_daily_task,
)
# V33 FINAL
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
WRONG_QUESTIONS_FILE = os.path.join(BASE_DIR, 'wrong_questions.json')
LEARNING_RECORDS_FILE = os.path.join(BASE_DIR, 'learning_records.json')
DAILY_TASKS_FILE = os.path.join(BASE_DIR, 'daily_tasks.json')
GENERATED_QUESTIONS_FILE = os.path.join(BASE_DIR, 'generated_questions.json')
CHROMA_DIR = os.path.join(BASE_DIR, 'chroma_db')
COLLECTION_NAME = 'software_engineer_notes'
_embedding_model = None
_collection = None
_client = None
_KNOWLEDGE_CACHE = {}
def get_ai_client():
    global _client
    if _client is None:
        key = os.getenv('DEEPSEEK_API_KEY')
        if not key:
            try:
                import streamlit as st
                key = st.secrets.get('DEEPSEEK_API_KEY')
            except Exception:
                key = None
        if not key:
            raise RuntimeError('没有找到 DEEPSEEK_API_KEY，请检查 .env 或 Streamlit Cloud Secrets。')
        _client = OpenAI(api_key=key, base_url='https://api.deepseek.com')
    return _client
def get_rag_resources():
    global _embedding_model, _collection
    if _embedding_model is None:
        print('正在加载向量模型...')
        _embedding_model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        print('向量模型加载完成')
    if _collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        try:
            _collection = chroma_client.get_collection(name=COLLECTION_NAME)
        except Exception as e:
            raise RuntimeError(f'知识库集合 {COLLECTION_NAME!r} 不存在，请先完成知识库构建。') from e
        print('知识库加载完成')
    return _embedding_model, _collection
# -------------------- JSON --------------------
def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception:
        return default
def save_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
def today_str():
    return date.today().isoformat()
def now_str():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
# -------------------- RAG --------------------
def search_knowledge(query, n=5):
    """V33：知识检索短缓存，减少重复训练时的向量计算/云端查询。"""
    key = (str(query).strip(), int(n))
    now = time.time()
    cached = _KNOWLEDGE_CACHE.get(key)
    if cached and now - cached[0] < 300:
        return cached[1]

    model, collection = get_rag_resources()
    vector = model.encode(query).tolist()
    result = collection.query(query_embeddings=[vector], n_results=max(1, n))
    docs = result.get('documents', [[]])[0] or []
    metas = result.get('metadatas', [[]])[0] or []
    parts = []
    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) and metas[i] else {}
        parts.append(
            f'【知识片段{i + 1}｜第{meta.get("page", "?")}页｜{meta.get("section", "")}】\n{doc}'
        )
    value = '\n\n'.join(parts) if parts else '没有检索到相关知识。'
    if len(_KNOWLEDGE_CACHE) > 64:
        _KNOWLEDGE_CACHE.clear()
    _KNOWLEDGE_CACHE[key] = (now, value)
    return value

def ai(prompt, system='你是严谨的软件设计师考试学习助手。', temperature=0.2, json_mode=False, max_tokens=None):
    """统一 AI 调用入口。支持较小 max_tokens，减少出题/批改等待时间。"""
    kwargs = {
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': temperature,
    }
    if max_tokens:
        kwargs['max_tokens'] = int(max_tokens)
    if json_mode:
        kwargs['response_format'] = {'type': 'json_object'}
    response = get_ai_client().chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()

def extract_json(text):
    text = (text or '').strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.I)
    text = re.sub(r'\s*```$', '', text).strip()
    start = text.find('{')
    if start < 0:
        raise ValueError('AI没有返回JSON对象')
    depth = 0
    quoted = False
    escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                quoted = False
        else:
            if c == '"':
                quoted = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError as e:
                        raise ValueError(f'AI返回JSON格式错误：{e}') from e
    raise ValueError('AI返回的JSON不完整')
# -------------------- learning data --------------------
def load_wrong_questions():
    data = load_json_file(WRONG_QUESTIONS_FILE, [])
    if isinstance(data, dict):
        data = data.get('wrong_questions', data.get('questions', data.get('data', [])))
    return data if isinstance(data, list) else []
def load_learning_records():
    data = load_json_file(LEARNING_RECORDS_FILE, [])
    if isinstance(data, dict):
        data = data.get('records', data.get('learning_records', data.get('data', [])))
    return data if isinstance(data, list) else []
def load_daily_tasks():
    data = load_json_file(DAILY_TASKS_FILE, [])
    if isinstance(data, dict):
        data = data.get('daily_tasks', data.get('tasks', data.get('data', [])))
    return data if isinstance(data, list) else []
def save_wrong_questions(items): save_json_file(WRONG_QUESTIONS_FILE, items)
def save_learning_records(items): save_json_file(LEARNING_RECORDS_FILE, items)
def save_daily_tasks(items): save_json_file(DAILY_TASKS_FILE, items)
class QuestionExhaustedError(RuntimeError):
    """当前知识点暂时无法再生成新的、不重复的题目。"""


def load_generated_questions():
    data = load_json_file(GENERATED_QUESTIONS_FILE, [])
    return data if isinstance(data, list) else []


def save_generated_questions(items):
    save_json_file(GENERATED_QUESTIONS_FILE, items)


def question_key(q):
    q = normalize_question(q)
    raw = '|'.join([
        q.get('knowledge_point', '').strip(),
        q.get('question', '').strip(),
        q.get('A', '').strip(), q.get('B', '').strip(),
        q.get('C', '').strip(), q.get('D', '').strip(),
    ])
    normalized = re.sub(r'[\s\u3000，。、“”‘’：；！？（）()、/\\]+', '', raw).lower()
    return hashlib.sha1(normalized.encode('utf-8')).hexdigest()


def _canonical_topic(topic):
    return re.sub(r'\s+', '', str(topic or '').strip()).lower()


def generated_question_keys(topic):
    topic = str(topic).strip()
    canonical = _canonical_topic(topic)
    keys = set()
    for item in load_generated_questions():
        if _canonical_topic(item.get('knowledge_point', '')) == canonical and item.get('key'):
            keys.add(item['key'])
    # 兼容旧数据：已做过/错题也算已出现，避免重复。
    for item in load_learning_records() + load_wrong_questions():
        if _canonical_topic(item.get('knowledge_point', item.get('topic', ''))) == canonical:
            try:
                keys.add(question_key(item))
            except Exception:
                pass
    return keys


def remember_generated_question(q):
    items = load_generated_questions()
    key = question_key(q)
    if any(x.get('key') == key for x in items):
        return
    items.append({
        'key': key,
        'knowledge_point': q.get('knowledge_point', '未分类'),
        'question': q.get('question', ''),
        'created_at': now_str(),
    })
    # 只保留最近2000道，避免文件无限增长。
    save_generated_questions(items[-2000:])


def normalize_question(q):
    q = dict(q or {})
    opts = q.get('options', {}) if isinstance(q.get('options'), dict) else {}
    for k in 'ABCD':
        if not q.get(k):
            q[k] = opts.get(k, '')
    q['options'] = {k: str(q.get(k, opts.get(k, ''))) for k in 'ABCD'}
    for k in 'ABCD':
        q[k] = q['options'][k]
    q['correct_answer'] = str(q.get('correct_answer', 'A')).strip().upper()[:1]
    if q['correct_answer'] not in 'ABCD':
        q['correct_answer'] = 'A'
    q['question'] = str(q.get('question', '')).strip()
    q['knowledge_point'] = str(q.get('knowledge_point', q.get('topic', '未分类'))).strip() or '未分类'
    q['explanation'] = str(q.get('explanation', '')).strip()
    return q
def make_wrong_key(q):
    q = normalize_question(q)
    return re.sub(r'\s+', '', q.get('question', '')).lower()
def save_wrong_question(question, user_answer):
    question = normalize_question(question)
    items = load_wrong_questions()
    key = make_wrong_key(question)
    for item in items:
        if make_wrong_key(item) == key:
            item['user_answer'] = user_answer
            item['last_wrong_at'] = now_str()
            item.setdefault('review_level', 0)
            item.setdefault('consecutive_correct', 0)
            item.setdefault('next_review_date', today_str())
            item.setdefault('mastered', False)
            save_wrong_questions(items)
            # ====== 云端保存（找到旧错题，同步到supabase）======
            try:
                save_cloud_wrong_question(
                    question=question.get("question", ""),
                    options=[
                        question.get("A", ""),
                        question.get("B", ""),
                        question.get("C", ""),
                        question.get("D", "")
                    ],
                    correct_answer=question.get("correct_answer", ""),
                    user_answer=user_answer,
                    explanation=question.get("explanation", ""),
                    topic=question.get("knowledge_point", "未分类")
                )
            except Exception as e:
                print(f"⚠️ 云端错题保存失败：{e}")
            return item
    item = {
        **{k: question.get(k, '') for k in ['question', 'A', 'B', 'C', 'D', 'correct_answer', 'explanation', 'knowledge_point', 'source']},
        'options': question.get('options', {k: question.get(k, '') for k in 'ABCD'}),
        'user_answer': user_answer,
        'first_wrong_at': now_str(),
        'last_wrong_at': now_str(),
        'review_level': 0,
        'consecutive_correct': 0,
        'next_review_date': today_str(),
        'mastered': False,
    }
    items.append(item)
    save_wrong_questions(items)
    # ====== 云端保存（新增错题，同步到supabase）======
    try:
        save_cloud_wrong_question(
            question=question.get("question", ""),
            options=[
                question.get("A", ""),
                question.get("B", ""),
                question.get("C", ""),
                question.get("D", "")
            ],
            correct_answer=question.get("correct_answer", ""),
            user_answer=user_answer,
            explanation=question.get("explanation", ""),
            topic=question.get("knowledge_point", "未分类")
        )
    except Exception as e:
        print(f"⚠️ 云端错题保存失败：{e}")
    return item
def get_due_wrong_questions():
    today = today_str()
    result = []
    for q in load_wrong_questions():
        if q.get('mastered') is True:
            continue
        due = str(q.get('next_review_date', q.get('next_review', '')))[:10]
        if due and due <= today:
            result.append(q)
    return result
def update_wrong_review(question, is_correct):
    key = make_wrong_key(question)
    items = load_wrong_questions()
    target = next((item for item in items if make_wrong_key(item) == key), None)
    if target is None:
        return None
    if is_correct:
        level = int(target.get('review_level', 0) or 0) + 1
        target['review_level'] = level
        target['consecutive_correct'] = int(target.get('consecutive_correct', 0) or 0) + 1
        intervals = [3, 7]
        if level >= 3:
            target['mastered'] = True
            target['next_review_date'] = None
        else:
            target['mastered'] = False
            target['next_review_date'] = (date.today() + timedelta(days=intervals[level - 1])).isoformat()
    else:
        target['review_level'] = 0
        target['consecutive_correct'] = 0
        target['mastered'] = False
        target['next_review_date'] = (date.today() + timedelta(days=1)).isoformat()
    target['last_review_at'] = now_str()
    save_wrong_questions(items)
    return target
def record_question_result(question, user_answer, is_correct, mode='training'):
    q = normalize_question(question)
    records = load_learning_records()
    records.append({
        'date': now_str(),
        'knowledge_point': q.get('knowledge_point', '未分类'),
        'question': q.get('question', ''),
        'user_answer': user_answer,
        'correct_answer': q.get('correct_answer', ''),
        'is_correct': bool(is_correct),
        'mode': mode,
        'total': 1,
        'correct': 1 if is_correct else 0,
        'wrong': 0 if is_correct else 1,
    })
    save_learning_records(records)
    # 同步学习记录到Supabase
    try:
        save_learning_record(
            topic=q.get('knowledge_point','未分类'),
            question=q.get('question',''),
            answer=user_answer,
            is_correct=is_correct,
            score=100 if is_correct else 0
        )
    except Exception as e:
        print(f"⚠️ 云端学习记录保存失败：{e}")
# -------------------- learning analysis --------------------
def calculate_learning_status():
    buckets = defaultdict(lambda: {'total': 0, 'correct': 0, 'wrong': 0, 'sessions': 0})
    for r in load_learning_records():
        if not isinstance(r, dict):
            continue
        p = str(r.get('knowledge_point', r.get('topic', '未分类'))) or '未分类'
        try:
            total = int(r.get('total', 1) or 1)
        except Exception:
            total = 1
        if 'is_correct' in r:
            correct = 1 if r.get('is_correct') is True else 0
        else:
            try:
                correct = int(r.get('correct', 0) or 0)
            except Exception:
                correct = 0
        correct = min(max(correct, 0), total)
        buckets[p]['total'] += total
        buckets[p]['correct'] += correct
        buckets[p]['wrong'] += max(0, total - correct)
        buckets[p]['sessions'] += 1
    wrong_counts = Counter(
        q.get('knowledge_point', '未分类')
        for q in load_wrong_questions()
        if not q.get('mastered')
    )
    out = []
    for p, d in buckets.items():
        acc = d['correct'] / d['total'] * 100 if d['total'] else 0
        w = wrong_counts.get(p, 0)
        # 掌握度不能只看今天；历史答题 + 未掌握错题共同决定。
        mastery = min(100, max(0, acc * 0.7 + (30 if w == 0 else max(0, 30 - w * 5))))
        out.append({
            'knowledge_point': p,
            'total': d['total'],
            'correct': d['correct'],
            'wrong': d['wrong'],
            'sessions': d['sessions'],
            'accuracy': round(acc, 1),
            'wrong_questions': w,
            'mastery': round(mastery, 1),
        })
    for p, c in wrong_counts.items():
        if p not in buckets:
            out.append({'knowledge_point': p, 'total': 0, 'correct': 0, 'wrong': 0, 'sessions': 0,
                        'accuracy': 0.0, 'wrong_questions': c, 'mastery': 0.0})
    for x in out:
        x['priority'] = round((100 - x['mastery']) + x['wrong_questions'] * 8 + (10 if x['total'] < 5 else 0), 1)
    out.sort(key=lambda x: x['priority'], reverse=True)
    return out
def choose_adaptive_topic():
    status = calculate_learning_status()
    return status[0]['knowledge_point'] if status else '软件开发方法'
def analyze_wrong_questions():
    """返回可直接给Web/CLI展示的错题分析，不调用AI。"""
    wrong = [normalize_question(q) for q in load_wrong_questions() if not q.get('mastered')]
    counts = Counter(q.get('knowledge_point', '未分类') for q in wrong)
    status = calculate_learning_status()
    ranked = []
    for topic, count in counts.most_common():
        item = next((x for x in status if x.get('knowledge_point') == topic), {})
        ranked.append({
            'knowledge_point': topic,
            'count': count,
            'accuracy': item.get('accuracy', 0),
            'mastery': item.get('mastery', 0),
            'priority': item.get('priority', item.get('weakness_score', 0)),
        })
    return {
        'total': len(wrong),
        'due_count': len(get_due_wrong_questions()),
        'knowledge_points': ranked,
        'status': status,
        'recommendation': ranked[0]['knowledge_point'] if ranked else (status[0]['knowledge_point'] if status else '软件开发方法'),
    }

def adaptive_analysis():
    status = calculate_learning_status()
    today = get_today_stats()
    due = get_due_wrong_questions()
    return {
        'today': today,
        'wrong_count': len([q for q in load_wrong_questions() if not q.get('mastered')]),
        'due_count': len(due),
        'priority_topic': status[0]['knowledge_point'] if status else '软件开发方法',
        'status': status[:10],
    }
# -------------------- question generation --------------------
def generate_question(knowledge_point):
    """快速出题 + 持久化去重；连续生成不到新题时明确提示题目已耗尽。"""
    topic = str(knowledge_point or '').strip() or '软件开发方法'
    used_keys = generated_question_keys(topic)

    try:
        knowledge = search_knowledge(topic, 3)
    except TypeError:
        knowledge = search_knowledge(topic)

    used_text = []
    for item in load_generated_questions():
        if str(item.get('knowledge_point', '')).strip() == topic and item.get('question'):
            used_text.append(item['question'])
    used_text = used_text[-12:]

    prompt = f"""根据给出的软件设计师知识库，围绕“{topic}”生成1道高质量单项选择题。
只允许一个正确答案，必须有A/B/C/D四个选项，必须依据知识库。
不要与“已生成题目”重复；如果知识库内容不足以产生新的独立题目，直接返回：{{"exhausted":true}}。
返回严格JSON，不要Markdown。
格式：{{"question":"","options":{{"A":"","B":"","C":"","D":""}},"correct_answer":"A","explanation":"","knowledge_point":"{topic}","source":"知识库"}}

知识库：
{knowledge}

已生成题目（仅用于去重）：
{json.dumps(used_text, ensure_ascii=False)}"""

    last_q = None
    for attempt in range(3):
        data = extract_json(ai(
            prompt,
            system='你是软件设计师考试命题专家。严格依据知识库，快速生成单选题。',
            temperature=0.1,
            json_mode=True,
            max_tokens=700,
        ))
        if data.get('exhausted'):
            raise QuestionExhaustedError(
                f'⚠️ 当前知识点“{topic}”没有检测到新的可用题目；已生成题目不会重复。'
            )
        q = normalize_question(data)
        if not q.get('question') or any(not q.get(k) for k in 'ABCD') or q.get('correct_answer') not in 'ABCD':
            raise ValueError('AI返回的题目格式不正确。')
        last_q = q
        key = question_key(q)
        if key not in used_keys:
            q['_training_topic'] = topic
            remember_generated_question(q)
            return q
        # 第二次尝试明确要求换角度。
        prompt += '\n刚才生成的题目重复了。请换一个考查角度，重新生成完全不同的新题。'

    raise QuestionExhaustedError(
        f'⚠️ 当前知识点“{topic}”可生成的新题有限，未找到新的不重复题目。'
    )

# -------------------- daily plan --------------------
def get_today_tasks():
    for plan in load_daily_tasks():
        if str(plan.get('date', ''))[:10] == today_str():
            return plan
    return None
def _fallback_plan(weakest, due_count):
    tasks = []
    if due_count:
        tasks.append({'name': '到期错题间隔复习', 'minutes': 20,
                      'description': f'逐题复习今天到期的{due_count}道错题；答对进入下一周期，答错安排1天后。'})
    tasks += [
        {'name': f'{weakest}专项强化', 'minutes': 35, 'description': '围绕当前薄弱知识点完成专项题，记录错误原因。'},
        {'name': '知识点梳理与对比', 'minutes': 25, 'description': '整理核心概念、易混概念和考试关键词，形成一页笔记。'},
        {'name': '综合自测', 'minutes': 25, 'description': '完成混合题并统计正确率，重点复盘错误选项。'},
    ]
    return tasks
def create_dynamic_study_plan(force=False):
    existing = get_today_tasks()
    if existing and not force:
        return existing
    status = calculate_learning_status()
    weakest = choose_adaptive_topic()
    due = get_due_wrong_questions()
    previous = None
    for p in load_daily_tasks():
        d = str(p.get('date', ''))[:10]
        if d < today_str() and (previous is None or d > str(previous.get('date', ''))[:10]):
            previous = p
    unfinished = []
    if previous:
        unfinished = [x.get('name', '') for x in previous.get('tasks', []) if not x.get('completed')]
    prompt = f'''
根据学生真实学习数据制定今天约120分钟的学习计划。
当前最薄弱知识点：{weakest}
学习状态：{json.dumps(status[:8], ensure_ascii=False)}
今天到期错题：{len(due)}，知识点：{[q.get('knowledge_point') for q in due[:10]]}
上一学习日未完成任务：{unfinished}
要求：正确率低/错题多优先；今天有到期错题必须优先安排错题复习；已掌握内容减少重复；每项任务有分钟数和具体执行方法；总时长约120分钟；不能把今天100%正确直接当成完全掌握。
只返回JSON：{{"goal":"今天核心目标","tasks":[{{"name":"任务名称","minutes":20,"description":"具体执行方法"}}]}}
'''
    try:
        plan = extract_json(ai(prompt, system='你是专业的软件设计师考试AI学习规划师。', temperature=0.2, json_mode=True))
    except Exception:
        plan = {'goal': f'强化{weakest}并完成到期错题复习', 'tasks': _fallback_plan(weakest, len(due))}
    tasks = []
    for t in plan.get('tasks', []):
        if not isinstance(t, dict):
            continue
        try:
            mins = max(5, int(t.get('minutes', 20)))
        except Exception:
            mins = 20
        tasks.append({'name': str(t.get('name', '学习任务')), 'minutes': mins,
                      'description': str(t.get('description', '')), 'completed': False, 'completed_at': None})
    if due and not any('错题' in t['name'] and '复习' in t['name'] for t in tasks):
        tasks.insert(0, {'name': '到期错题间隔复习', 'minutes': 20,
                          'description': f'逐题复习今天到期的{len(due)}道错题并更新间隔复习状态。',
                          'completed': False, 'completed_at': None})
    if not tasks:
        tasks = [{**x, 'completed': False, 'completed_at': None} for x in _fallback_plan(weakest, len(due))]
    # 防止AI生成极端长计划；保留所有任务，不删除任务。
    total = sum(t['minutes'] for t in tasks)
    if total > 150:
        scale = 120 / total
        for t in tasks:
            t['minutes'] = max(5, round(t['minutes'] * scale))
    goal = str(plan.get('goal') or f'强化{weakest}并完成今日核心学习任务')
    day = {'date': today_str(), 'goal': goal, 'tasks': tasks, 'created_at': now_str()}
    all_plans = [p for p in load_daily_tasks() if str(p.get('date', ''))[:10] != today_str()]
    all_plans.append(day)
    save_daily_tasks(all_plans)
    return day
def complete_task(task_number):
    plan = get_today_tasks()
    if not plan:
        return False, '今天还没有学习计划，请先输入“每日任务”。'
    try:
        idx = int(task_number) - 1
    except Exception:
        return False, '请输入正确的任务编号。'
    tasks = plan.get('tasks', [])
    if idx < 0 or idx >= len(tasks):
        return False, f'没有这个任务。当前任务范围：1-{len(tasks)}。'
    task = tasks[idx]
    if task.get('completed'):
        return False, '这个任务已经完成。'
    task['completed'] = True
    task['completed_at'] = now_str()
    plans = load_daily_tasks()
    for p in plans:
        if str(p.get('date', ''))[:10] == today_str():
            p.update(plan)
            break
    save_daily_tasks(plans)
    return True, f"已完成任务 {idx + 1}：{task.get('name', '')}"
# -------------------- reports --------------------
def get_today_stats():
    records = [r for r in load_learning_records() if str(r.get('date', ''))[:10] == today_str()]
    correct = sum(1 for r in records if r.get('is_correct') is True or r.get('correct') == 1)
    questions = len(records)
    return {'questions': questions, 'correct': correct, 'wrong': questions - correct,
            'accuracy': round(correct / questions * 100, 1) if questions else 0.0}
def learning_report():
    plan = get_today_tasks()
    stats = get_today_stats()
    status = calculate_learning_status()
    wrong = [x for x in load_wrong_questions() if not x.get('mastered')]
    due = get_due_wrong_questions()
    tasks = (plan or {}).get('tasks', [])
    done = sum(1 for t in tasks if t.get('completed'))
    total = len(tasks)
    minutes = sum(int(t.get('minutes', 0) or 0) for t in tasks if t.get('completed'))
    return {
        'date': today_str(), 'tasks_done': done, 'tasks_total': total, 'minutes': minutes,
        'today': stats, 'wrong_count': len(wrong), 'due_count': len(due),
        'status': status[:8],
        'tomorrow_basis': [x['knowledge_point'] for x in status[:3]],
        'plan': plan,
    }
def show_today_tasks():
    plan = get_today_tasks() or create_dynamic_study_plan()
    print('\n' + '=' * 60 + '\n📋 今日学习任务\n' + '=' * 60)
    print('🎯 今日目标：', plan.get('goal', ''))
    for i, t in enumerate(plan.get('tasks', []), 1):
        print(f"\n{'✅' if t.get('completed') else '⬜'} {i}. {t.get('name')}\n   {t.get('minutes')}分钟\n   {t.get('description')}")
    done = sum(1 for t in plan.get('tasks', []) if t.get('completed'))
    total = sum(int(t.get('minutes', 0) or 0) for t in plan.get('tasks', []))
    mins = sum(int(t.get('minutes', 0) or 0) for t in plan.get('tasks', []) if t.get('completed'))
    print(f'\n📊 完成：{done}/{len(plan.get("tasks", []))}\n⏱️ 学习时间：{mins}/{total}分钟')
    return plan
def start_today_learning():
    plan = get_today_tasks() or create_dynamic_study_plan()
    for i, t in enumerate(plan.get('tasks', []), 1):
        if not t.get('completed'):
            print(f"\n🚀 第{i}项：{t.get('name')}\n⏱️ {t.get('minutes')}分钟\n📌 {t.get('description')}\n完成后输入：完成任务{i}")
            return plan
    print('🎉 今天所有任务都完成了！')
    return plan
# -------------------- question session --------------------
current_question = None
training_mode = False
training_total = 5
training_index = 0
training_correct = 0
training_results = []
wrong_review_mode = False
wrong_review_questions = []
wrong_review_index = 0
def start_training(topic=None):
    global current_question, training_mode, training_index, training_correct, training_results, wrong_review_mode
    training_mode = True
    wrong_review_mode = False
    training_index = 0
    training_correct = 0
    training_results = []
    topic = topic or choose_adaptive_topic()
    q = generate_question(topic)
    q['_training_topic'] = topic
    current_question = q
    show_question(q)
    return q
def show_question(q):
    q = normalize_question(q)
    print('\n' + '=' * 60 + '\n📝 软件设计师训练\n' + '=' * 60)
    print('知识点：', q.get('knowledge_point'))
    print(f"\n{q.get('question', '')}")
    for k in 'ABCD':
        print(f'{k}. {q.get(k, "")}')
    print('\n请输入 A / B / C / D')
def grade_answer(user_answer, review=False, advance=True):
    """本地快速判题；默认保持CLI行为，Web可传 advance=False 先展示答案再进入下一题。"""
    global current_question, training_index, training_correct, training_results, training_mode, wrong_review_index, wrong_review_mode
    if not current_question:
        return None
    ans = str(user_answer).strip().upper()[:1]
    if ans not in 'ABCD':
        print('请输入 A / B / C / D。')
        return None
    correct = str(current_question.get('correct_answer', '')).upper()[:1]
    ok = ans == correct

    if review:
        record_question_result(current_question, ans, ok, 'wrong_review')
        target = update_wrong_review(current_question, ok)
        if ok:
            next_date = target.get('next_review_date') if target else None
            msg = '🎉 连续答对3次，已掌握！' if target and target.get('mastered') else f'✅ 复习答对！下一次复习：{next_date}'
        else:
            msg = f'❌ 仍答错，正确答案：{correct}；下一次复习：{target.get("next_review_date") if target else "明天"}'
        print(msg)
        print('📖 原解析：', current_question.get('explanation', '暂无解析'))
        if advance:
            wrong_review_index += 1
            if wrong_review_index >= len(wrong_review_questions):
                print('🎉 错题复习完成！')
                current_question = None
                wrong_review_mode = False
            else:
                current_question = normalize_question(wrong_review_questions[wrong_review_index])
                show_question(current_question)
        return ok

    # 判题只做本地字符串比较，不再调用AI，因此响应应为瞬时。
    record_question_result(current_question, ans, ok, 'training' if training_mode else 'single')
    if not ok:
        save_wrong_question(current_question, ans)

    print('✅ 回答正确！' if ok else f'❌ 回答错误！正确答案：{correct}')
    print('📖 解析：', current_question.get('explanation', '暂无解析'))

    if training_mode:
        training_index += 1
        training_correct += int(ok)
        training_results.append({
            'question': current_question.get('question'),
            'knowledge_point': current_question.get('knowledge_point'),
            'user_answer': ans,
            'correct_answer': correct,
            'is_correct': ok,
        })
        if advance:
            if training_index >= training_total:
                print(f'\n🏆 专项训练完成：{training_correct}/{training_total}，正确率 {training_correct / training_total * 100:.1f}%')
                training_mode = False
                current_question = None
            else:
                topic = current_question.get('_training_topic') or choose_adaptive_topic()
                current_question = generate_question(topic)
                show_question(current_question)
    else:
        if advance:
            current_question = None
    return ok

def start_wrong_review():
    global wrong_review_mode, wrong_review_questions, wrong_review_index, current_question, training_mode
    wrong_review_questions = get_due_wrong_questions()
    training_mode = False
    if not wrong_review_questions:
        future = sorted(q.get('next_review_date') for q in load_wrong_questions()
                        if q.get('next_review_date') and not q.get('mastered') and q.get('next_review_date') > today_str())
        print('🎉 今天没有到期错题。')
        print('下一次复习：', future[0] if future else '暂无')
        return None
    wrong_review_mode = True
    wrong_review_index = 0
    current_question = normalize_question(wrong_review_questions[0])
    print(f'📚 今天到期：{len(wrong_review_questions)}题')
    show_question(current_question)
    return current_question
# -------------------- CLI views --------------------
def show_learning_progress():
    s = calculate_learning_status()
    print('\n📊 我的学习进度')
    print('累计答题记录：', len(load_learning_records()), '条')
    print('当前未掌握错题：', len([q for q in load_wrong_questions() if not q.get('mastered')]))
    for i, x in enumerate(s, 1):
        print(f"{i}. {x['knowledge_point']}｜正确率 {x['accuracy']}%｜答题 {x['total']}｜错题 {x['wrong_questions']}｜掌握度 {x['mastery']}%｜优先级 {x['priority']}")
    return s
def normal_chat(user_input):
    knowledge = search_knowledge(user_input, 5)
    return ai(
        f'''请根据软件设计师知识库回答用户的知识问题。
不要把“系统功能命令”当成知识问题；这里只处理普通知识问答。
优先依据知识库，不要编造；资料不足时明确说明。
问题：{user_input}
知识库：
{knowledge}''',
        temperature=0.25,
    )
def command_help():
    print('''\n可用命令：
每日任务 / 查看每日任务 / 今天要做什么
完成任务1 / 完成任务 1 / 完成第1项任务
开始专项训练 / AI出题 / AI出题关于软件工程 / 退出专项训练
开始错题复习 / 错题复习
查看复习安排 / 给我今天的复习计划 / 间隔复习
学习进度 / 学习记录
分析我的错题 / 错题分析
自适应分析 / 自适应专项训练
开始今天学习
动态计划 / 重新制定今天计划
学习报告 / 总结今天学习
帮助 / 你好 / 普通知识问题 / exit''')
def show_review_schedule():
    due = get_due_wrong_questions()
    allq = [q for q in load_wrong_questions() if not q.get('mastered')]
    print('\n📅 错题复习安排')
    print('🔥 今天到期：', len(due), '题')
    for i, q in enumerate(due, 1):
        print(f"- {i}. {q.get('knowledge_point', '未分类')} — {q.get('question', '')[:60]}")
    upcoming = sorted((q.get('next_review_date'), q.get('knowledge_point')) for q in allq
                      if q.get('next_review_date') and q.get('next_review_date') > today_str())
    print('📚 后续安排：')
    if not upcoming:
        print('- 暂无')
    for d, p in upcoming[:15]:
        print('-', d, p)
def show_learning_records():
    records = load_learning_records()
    today = [r for r in records if str(r.get('date', ''))[:10] == today_str()]
    correct = sum(1 for r in today if r.get('is_correct') is True)
    print('\n📘 学习记录')
    print(f'今日答题：{len(today)}题｜正确：{correct}题｜错误：{len(today)-correct}题｜正确率：{correct/len(today)*100:.1f}%' if today else '今日还没有答题记录。')
    print(f'累计答题记录：{len(records)}条')
    return records
def _complete_task_match(text):
    patterns = [
        r'^完成\s*任务\s*(\d+)$',
        r'^完成\s*第\s*(\d+)\s*项?\s*任务?$',
        r'^完成\s*任务\s*(\d+)\s*$',
        r'^完成\s*第\s*(\d+)\s*个?任务$',
    ]
    for p in patterns:
        m = re.match(p, text)
        if m:
            return m.group(1)
    return None
def _training_topic_from_text(text):
    m = re.match(r'^(?:AI\s*出题|出题)(?:关于|：|:)?\s*(.+)?$', text, flags=re.I)
    if m:
        return (m.group(1) or choose_adaptive_topic()).strip() or choose_adaptive_topic()
    return None
def run_cli():
    global current_question, wrong_review_mode, training_mode
    print('\n' + '=' * 65)
    print('🤖 软件设计师 AI 自适应学习 Agent')
    print('=' * 65)
    print('① RAG知识问答 ② AI出题 ③ 自动批改 ④ 错题系统 ⑤ 间隔复习 ⑥ 自适应分析 ⑦ 动态计划 ⑧ 学习报告')
    print('输入 exit 退出。')
    while True:
        try:
            text = input('\n你：').strip()
        except (KeyboardInterrupt, EOFError):
            print('\nAgent：已退出。')
            break
        if text.lower() == 'exit':
            print('Agent：再见！')
            break
        if not text:
            print('Agent：请输入内容。')
            continue
        # 答题模式：退出/导航命令优先处理，避免被锁死在答题状态。
        if wrong_review_mode:
            if text in ['退出错题复习', '退出复习', '取消答题', 'exit training', '退出训练']:
                wrong_review_mode = False
                current_question = None
                wrong_review_questions = []
                print('已退出错题复习。')
                continue
            if text in ['复习安排', '查看复习安排', '给我今天的复习计划', '间隔复习']:
                show_review_schedule()
                continue
            if text.upper()[:1] in 'ABCD':
                try:
                    grade_answer(text, review=True)
                except Exception as e:
                    print('⚠️ 错题复习失败：', e)
                continue
            print('当前正在错题复习，请输入 A / B / C / D。')
            continue
        if current_question:
            if text in ['退出专项训练', '退出训练', '取消答题', '结束训练']:
                current_question = None
                training_mode = False
                print('已退出专项训练。')
                continue
            if text in ['复习安排', '查看复习安排', '给我今天的复习计划', '间隔复习']:
                current_question = None
                training_mode = False
                show_review_schedule()
                continue
            if text.upper()[:1] in 'ABCD':
                try:
                    grade_answer(text)
                except Exception as e:
                    print('⚠️ 答题失败：', e)
                continue
            print('当前正在答题，请输入 A / B / C / D。')
            continue
        # 功能命令必须在RAG之前识别。
        if text in ['每日任务', '查看今日任务', '查看每日任务', '查看任务', '今天要做什么']:
            show_today_tasks(); continue
        if text in ['查看复习安排', '复习安排', '给我今天的复习计划', '间隔复习']:
            show_review_schedule(); continue
        if text in ['开始错题复习', '复习错题', '刷错题', '错题复习']:
            start_wrong_review(); continue
        if text in ['开始专项训练', '专项训练', '开始刷题']:
            try: start_training()
            except Exception as e: print('⚠️ 出题失败：', e)
            continue
        topic = _training_topic_from_text(text)
        if topic:
            try: start_training(topic)
            except Exception as e: print('⚠️ 出题失败：', e)
            continue
        if text in ['学习进度', '我的学习进度', '查看学习进度', '学习记录']:
            show_learning_progress() if text != '学习记录' else show_learning_records(); continue
        if text in ['分析我的错题', '错题分析']:
            a = analyze_wrong_questions()
            print(f"\n📊 错题总数：{a['total']}｜今日到期：{a['due_count']}题")
            if not a['knowledge_points']:
                print('目前没有未掌握错题。')
            for i, x in enumerate(a['knowledge_points'], 1):
                print(f"{i}. {x['knowledge_point']}：{x['count']}题")
            continue
        if text in ['自适应分析', '分析自适应状态', '自适应专项训练', '适应专项训练']:
            a = adaptive_analysis()
            print('\n🧠 AI自适应分析')
            print(f"今日做题：{a['today']['questions']}题｜正确率：{a['today']['accuracy']}%")
            print(f"当前未掌握错题：{a['wrong_count']}题｜今日到期：{a['due_count']}题")
            print('当前优先知识点：', a['priority_topic'])
            for i, x in enumerate(a['status'], 1):
                print(f"{i}. {x['knowledge_point']}｜掌握度{x['mastery']}%｜正确率{x['accuracy']}%｜错题{x['wrong_questions']}｜优先级{x['priority']}")
            continue
        if text in ['学习报告', '总结今天学习', '今日报告']:
            print(json.dumps(learning_report(), ensure_ascii=False, indent=2)); continue
        if text in ['AI知识问答', 'AI 知识问答', '问答', '知识问答']:
            print('进入 AI 知识问答模式：直接输入你的知识问题即可；功能命令不会发送到知识库。')
            continue
        if text in ['开始今天学习', '开始今日学习']:
            start_today_learning(); continue
        if text in ['动态计划', '动态制定计划', '动态计划 / 重新制定今天计划', '重新制定今天的计划', '重新生成今天的计划']:
            create_dynamic_study_plan(True); show_today_tasks(); continue
        task_num = _complete_task_match(text)
        if task_num:
            print(complete_task(task_num)[1]); continue
        if text in ['帮助', 'help']:
            command_help(); continue
        if text in ['你好', '您好']:
            print('你好！我是软件设计师 AI 学习助手。你可以直接提问，也可以使用“每日任务、开始专项训练、开始错题复习、自适应分析、学习报告”等功能。')
            continue
        try:
            print('\nAgent：\n' + normal_chat(text))
        except Exception as e:
            print('⚠️ Agent运行错误：', e)
if __name__ == '__main__':
    run_cli()

def test_cloud_database():
    print("\n==============================")
    print("☁️ 云端数据库测试")
    print("==============================")
    # 测试学习记录
    save_learning_record(
        topic="测试知识点",
        question="这是云端数据库测试题",
        answer="测试答案",
        is_correct=True,
        score=100
    )
    records = get_learning_records()
    print(f"✅ 学习记录：{len(records)} 条")
    # 测试错题
    save_cloud_wrong_question(
        question="这是云端错题测试",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        user_answer="B",
        explanation="这是测试解释",
        topic="测试知识点"
    )
    wrong = get_wrong_questions()
    print(f"✅ 错题记录：{len(wrong)} 条")
    print("\n🎉 Supabase 云端数据测试成功！")

# 新增：调用测试函数，运行直接测试数据库连接
if __name__ == '__main__':
    # 取消下面注释即可测试云端数据库
    # test_cloud_database()
    run_cli()
