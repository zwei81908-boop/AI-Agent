import os
import sys
import html
from datetime import date

import pandas as pd
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import agent

st.set_page_config(
    page_title='软件设计师 AI 自适应学习 Agent',
    page_icon='🤖',
    layout='wide',
    initial_sidebar_state='expanded',
)

# -------------------- UI --------------------
st.markdown('''
<style>
.main .block-container {max-width: 1400px; padding-top: 1.5rem; padding-bottom: 3rem;}
.hero {padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(135deg,#eef5ff,#f8fbff); border:1px solid #d9e7ff; margin-bottom:1rem;}
.hero h1 {margin:0; font-size:2rem;}
.hero p {margin:.45rem 0 0; color:#5b6472;}
.card {padding:1.05rem 1.15rem; border:1px solid #e8ebf0; border-radius:16px; background:#fff; box-shadow:0 2px 10px rgba(20,30,50,.04); margin-bottom:.8rem;}
.card-title {font-size:1.05rem; font-weight:700; margin-bottom:.35rem;}
.muted {color:#6b7280; font-size:.9rem;}
.question {font-size:1.15rem; font-weight:650; line-height:1.65; padding:1.1rem; background:#f8fafc; border-radius:14px; border:1px solid #e5e7eb; margin: .8rem 0;}
.answer-box {padding:1rem; border-radius:14px; background:#f8fafc; border:1px solid #e5e7eb; margin-top:.8rem;}
.small {font-size:.9rem;color:#667085;}
</style>
''', unsafe_allow_html=True)


def init_state():
    defaults = {
        'page': '今日任务',
        'train_topic': '软件测试',
        'train_q': None,
        'train_submitted': False,
        'train_answer': None,
        'train_count': 0,
        'train_correct': 0,
        'review_qs': [],
        'review_index': 0,
        'review_q': None,
        'review_submitted': False,
        'review_answer': None,
        'qa_answer': None,
        'qa_context': None,
        'notice': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


def get_today_plan():
    return agent.get_today_tasks()


def task_summary(plan):
    tasks = (plan or {}).get('tasks', [])
    done = sum(1 for x in tasks if x.get('completed'))
    total_minutes = sum(int(x.get('minutes', 0) or 0) for x in tasks)
    done_minutes = sum(int(x.get('minutes', 0) or 0) for x in tasks if x.get('completed'))
    return done, len(tasks), done_minutes, total_minutes


def render_top():
    plan = get_today_plan()
    stats = agent.get_today_stats()
    wrong = len([q for q in agent.load_wrong_questions() if not q.get('mastered')])
    due = len(agent.get_due_wrong_questions())
    done, total, done_min, plan_min = task_summary(plan)

    st.markdown('''<div class="hero"><h1>🤖 软件设计师 AI 自适应学习 Agent</h1><p>RAG 知识库 · AI 出题 · 自动批改 · 错题间隔复习 · 自适应分析 · 动态学习计划</p></div>''', unsafe_allow_html=True)
    a,b,c,d,e = st.columns(5)
    a.metric('今日任务', f'{done}/{total}')
    b.metric('今日做题', stats['questions'])
    c.metric('今日正确率', f"{stats['accuracy']:.1f}%")
    d.metric('未掌握错题', wrong)
    e.metric('今日待复习', due)
    if plan:
        st.progress(done / total if total else 0, text=f'今日计划进度：{done}/{total} · 已计入计划时间 {done_min}/{plan_min} 分钟')


render_top()

with st.sidebar:
    st.header('🧭 学习中心')
    pages = ['今日任务','专项训练','错题复习','复习安排','自适应分析','学习进度','学习报告','AI知识问答']
    page = st.radio('功能', pages, index=pages.index(st.session_state.page), label_visibility='collapsed')
    st.session_state.page = page
    st.divider()
    st.caption('数据文件与 agent.py 共用同一目录，网页端和命令行端数据保持一致。')
    if st.button('🔄 刷新数据', use_container_width=True):
        st.rerun()

page = st.session_state.page

# -------------------- 今日任务 --------------------
if page == '今日任务':
    st.subheader('📅 今日学习任务')
    plan = get_today_plan()
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button('✨ 生成/读取今日计划', type='primary', use_container_width=True):
            try:
                agent.create_dynamic_study_plan(False)
                st.rerun()
            except Exception as e:
                st.error(f'生成计划失败：{e}')
    with c2:
        if st.button('🧠 按最新数据重新制定', use_container_width=True):
            try:
                agent.create_dynamic_study_plan(True)
                st.rerun()
            except Exception as e:
                st.error(f'重新制定失败：{e}')

    plan = get_today_plan() or agent.create_dynamic_study_plan(False)
    done, total, done_min, plan_min = task_summary(plan)
    st.markdown(f'''<div class="card"><div class="muted">🎯 今日核心目标</div><div class="card-title">{html.escape(str(plan.get('goal','')))}</div><div class="small">任务：{done}/{total} · 计划时长：{plan_min}分钟 · 已完成：{done_min}分钟</div></div>''', unsafe_allow_html=True)

    for i, t in enumerate(plan.get('tasks', []), 1):
        completed = bool(t.get('completed'))
        with st.container(border=True):
            left, mid, right = st.columns([0.08, 0.72, 0.20])
            left.markdown('### ' + ('✅' if completed else '⬜'))
            mid.markdown(f"**{i}. {t.get('name','学习任务')}** · {t.get('minutes',0)} 分钟")
            mid.caption(t.get('description',''))
            if not completed:
                if right.button('完成任务', key=f'complete_{i}', use_container_width=True):
                    ok, msg = agent.complete_task(i)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)
            else:
                right.caption(f"完成于 {str(t.get('completed_at',''))[-8:]}")

    st.divider()
    if st.button('🚀 开始今天学习', type='primary'):
        pending = next((i for i,t in enumerate(plan.get('tasks',[]),1) if not t.get('completed')), None)
        if pending:
            st.session_state.page = '错题复习' if '错题' in plan['tasks'][pending-1].get('name','') else '专项训练'
            st.rerun()
        else:
            st.success('🎉 今天所有任务已经完成！')

# -------------------- 专项训练 --------------------
elif page == '专项训练':
    st.subheader('📝 AI 专项训练')
    st.caption('每次提交都会写入 learning_records.json；答错自动进入错题系统。')
    topic = st.text_input('训练知识点', value=st.session_state.train_topic)
    st.session_state.train_topic = topic
    c1,c2,c3 = st.columns([1,1,2])
    with c1:
        if st.button('🎯 生成新题', type='primary', use_container_width=True):
            try:
                with st.spinner('RAG检索 + AI命题中...'):
                    q = agent.generate_question(topic or agent.choose_adaptive_topic())
                st.session_state.train_q = q
                st.session_state.train_submitted = False
                st.session_state.train_answer = None
                st.rerun()
            except Exception as e:
                st.error(f'出题失败：{e}')
    with c2:
        if st.button('🔥 训练薄弱知识点', use_container_width=True):
            st.session_state.train_topic = agent.choose_adaptive_topic()
            st.session_state.train_q = None
            st.session_state.train_submitted = False
            st.rerun()
    with c3:
        st.info(f"本次页面累计：{st.session_state.train_count} 题 · 正确 {st.session_state.train_correct} 题")

    q = st.session_state.train_q
    if q:
        q = agent.normalize_question(q)
        st.markdown(f"**知识点：** `{q.get('knowledge_point','未分类')}`")
        st.markdown(f'<div class="question">{html.escape(q["question"])}</div>', unsafe_allow_html=True)
        opts = q['options']
        answer = st.radio('请选择一个答案', ['A','B','C','D'], format_func=lambda x: f'{x}. {opts[x]}', key='train_answer_radio')
        if not st.session_state.train_submitted:
            if st.button('✅ 提交答案', type='primary', use_container_width=True):
                ok = answer == q['correct_answer']
                agent.record_question_result(q, answer, ok, 'training_web')
                if not ok:
                    agent.save_wrong_question(q, answer)
                st.session_state.train_answer = answer
                st.session_state.train_submitted = True
                st.session_state.train_count += 1
                st.session_state.train_correct += int(ok)
                st.rerun()
        else:
            answer = st.session_state.train_answer
            ok = answer == q['correct_answer']
            if ok: st.success('🎉 回答正确！')
            else: st.error(f'❌ 回答错误。正确答案：{q["correct_answer"]}')
            st.markdown('### 📖 解析')
            st.write(q.get('explanation',''))
            if q.get('source'): st.caption(f"来源：{q['source']}")
            if st.button('➡️ 下一题', type='primary', use_container_width=True):
                try:
                    with st.spinner('正在生成下一题...'):
                        nq = agent.generate_question(q.get('knowledge_point') or topic or agent.choose_adaptive_topic())
                    st.session_state.train_q = nq
                    st.session_state.train_submitted = False
                    st.session_state.train_answer = None
                    st.rerun()
                except Exception as e:
                    st.error(f'下一题生成失败：{e}')
    else:
        st.info('点击“生成新题”开始专项训练。')

# -------------------- 错题复习 --------------------
elif page == '错题复习':
    st.subheader('❌ 错题间隔复习')
    due = agent.get_due_wrong_questions()
    all_wrong = [q for q in agent.load_wrong_questions() if not q.get('mastered')]
    a,b,c = st.columns(3)
    a.metric('当前未掌握错题', len(all_wrong))
    b.metric('今天到期', len(due))
    c.metric('已掌握', len(agent.load_wrong_questions()) - len(all_wrong))

    if not due:
        future = sorted(q.get('next_review_date') for q in all_wrong if q.get('next_review_date') and q.get('next_review_date') > agent.today_str())
        st.success('🎉 今天没有到期错题。')
        st.info(f"下一次复习：{future[0] if future else '暂无'}")
    else:
        if not st.session_state.review_qs or st.session_state.review_qs[0].get('question') not in [x.get('question') for x in due]:
            st.session_state.review_qs = due
            st.session_state.review_index = 0
            st.session_state.review_submitted = False
            st.session_state.review_answer = None
        idx = st.session_state.review_index
        qs = st.session_state.review_qs
        if idx >= len(qs):
            st.success('🎉 本轮错题复习完成！')
            if st.button('重新开始本轮复习'):
                st.session_state.review_qs = due
                st.session_state.review_index = 0
                st.session_state.review_submitted = False
                st.rerun()
        else:
            q = agent.normalize_question(qs[idx])
            st.progress(idx / len(qs), text=f'复习进度：{idx+1}/{len(qs)}')
            st.markdown(f"**知识点：** `{q.get('knowledge_point','未分类')}`")
            st.markdown(f'<div class="question">{html.escape(q["question"])}</div>', unsafe_allow_html=True)
            opts=q['options']
            answer=st.radio('请选择一个答案', ['A','B','C','D'], format_func=lambda x:f'{x}. {opts[x]}', key=f'review_radio_{idx}')
            if not st.session_state.review_submitted:
                if st.button('✅ 提交复习答案', type='primary', use_container_width=True):
                    ok = answer == q['correct_answer']
                    agent.record_question_result(q, answer, ok, 'wrong_review_web')
                    target = agent.update_wrong_review(q, ok)
                    st.session_state.review_answer = answer
                    st.session_state.review_submitted = True
                    st.rerun()
            else:
                answer=st.session_state.review_answer
                ok=answer==q['correct_answer']
                target=next((x for x in agent.load_wrong_questions() if agent.make_wrong_key(x)==agent.make_wrong_key(q)), None)
                if ok:
                    if target and target.get('mastered'):
                        st.success('🎉 连续答对3次，已掌握！')
                    else:
                        st.success(f"✅ 复习答对！下一次复习：{target.get('next_review_date','暂无') if target else '暂无'}")
                else:
                    st.error(f"❌ 仍然答错。正确答案：{q['correct_answer']} · 下一次复习：{target.get('next_review_date','明天') if target else '明天'}")
                st.markdown('### 📖 原解析')
                st.write(q.get('explanation',''))
                if st.button('➡️ 下一题', type='primary', use_container_width=True):
                    st.session_state.review_index += 1
                    st.session_state.review_submitted = False
                    st.session_state.review_answer = None
                    st.rerun()

# -------------------- 复习安排 --------------------
elif page == '复习安排':
    st.subheader('📅 错题复习安排')
    wrong = [q for q in agent.load_wrong_questions() if not q.get('mastered')]
    due = agent.get_due_wrong_questions()
    st.metric('今天到期', len(due))
    if due:
        for i,q in enumerate(due,1):
            level=q.get('review_level',0); nxt=q.get('next_review_date','今天')
            st.markdown(f'''<div class="card"><div class="card-title">{i}. {html.escape(q.get('knowledge_point','未分类'))}</div><div class="small">复习等级：{level} · 当前到期：{nxt}</div><div>{html.escape(q.get('question',''))}</div></div>''',unsafe_allow_html=True)
    else:
        st.success('今天没有到期错题。')
    future=sorted([(q.get('next_review_date'),q.get('knowledge_point')) for q in wrong if q.get('next_review_date') and q.get('next_review_date')>agent.today_str()])
    st.subheader('📚 后续安排')
    if future:
        df=pd.DataFrame(future,columns=['下次复习日期','知识点'])
        st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info('暂无后续复习安排。')

# -------------------- 自适应 --------------------
elif page == '自适应分析':
    st.subheader('🧠 AI 自适应学习分析')
    data=agent.adaptive_analysis(); status=data['status']
    a,b,c,d=st.columns(4)
    a.metric('今日做题',data['today']['questions'])
    b.metric('今日正确率',f"{data['today']['accuracy']:.1f}%")
    c.metric('未掌握错题',data['wrong_count'])
    d.metric('今日到期复习',data['due_count'])
    if status:
        top=status[0]
        st.markdown(f'''<div class="card"><div class="muted">🎯 当前优先强化</div><div class="card-title">{html.escape(top['knowledge_point'])}</div><div>掌握度 {top['mastery']}% · 正确率 {top['accuracy']}% · 未掌握错题 {top['wrong_questions']}题 · 优先级 {top['priority']}</div></div>''',unsafe_allow_html=True)
        df=pd.DataFrame([{'知识点':x['knowledge_point'],'答题数':x['total'],'正确率':x['accuracy'],'掌握度':x['mastery'],'未掌握错题':x['wrong_questions'],'优先级':x['priority']} for x in status])
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.info('判定逻辑同时考虑历史答题、正确率、未掌握错题和答题量；不会把“今天100%正确”直接当成完全掌握。')
        if st.button('🔄 根据当前数据重新制定今天计划',type='primary'):
            try:
                agent.create_dynamic_study_plan(True); st.success('计划已按最新学习数据更新。')
            except Exception as e: st.error(f'更新计划失败：{e}')
    else: st.info('完成一些题目后，这里会自动形成学习画像。')

# -------------------- 学习进度 --------------------
elif page == '学习进度':
    st.subheader('📈 学习进度')
    status=agent.calculate_learning_status(); records=agent.load_learning_records(); wrong=agent.load_wrong_questions()
    a,b,c=st.columns(3)
    a.metric('累计答题记录',len(records))
    b.metric('未掌握错题',len([x for x in wrong if not x.get('mastered')]))
    c.metric('已掌握错题',len([x for x in wrong if x.get('mastered')]))
    if status:
        df=pd.DataFrame([{'知识点':x['knowledge_point'],'答题数':x['total'],'正确':x['correct'],'错误':x['wrong'],'正确率':x['accuracy'],'掌握度':x['mastery'],'未掌握错题':x['wrong_questions'],'优先级':x['priority']} for x in status])
        st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info('还没有学习记录。')
    st.subheader('📘 今日记录')
    today=[r for r in records if str(r.get('date',''))[:10]==agent.today_str()]
    if today:
        df=pd.DataFrame([{'时间':str(r.get('date',''))[11:19],'知识点':r.get('knowledge_point'),'结果':'正确' if r.get('is_correct') else '错误','模式':r.get('mode','')} for r in reversed(today)])
        st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info('今天还没有答题记录。')

# -------------------- 学习报告 --------------------
elif page == '学习报告':
    st.subheader('📊 AI 学习报告')
    report=agent.learning_report(); t=report['today']; plan=report['plan']
    a,b,c,d,e=st.columns(5)
    a.metric('任务完成',f"{report['tasks_done']}/{report['tasks_total']}")
    b.metric('计划学习',f"{report['minutes']} 分钟")
    c.metric('今日做题',t['questions'])
    d.metric('今日正确',t['correct'])
    e.metric('正确率',f"{t['accuracy']:.1f}%")
    st.divider()
    a,b,c=st.columns(3)
    a.metric('当前未掌握错题',report['wrong_count'])
    b.metric('今日待复习',report['due_count'])
    c.metric('明日重点数量',len(report['tomorrow_basis']))
    st.subheader('🎯 当前薄弱知识点')
    if report['status']:
        df=pd.DataFrame([{'知识点':x['knowledge_point'],'正确率':x['accuracy'],'掌握度':x['mastery'],'答题数':x['total'],'未掌握错题':x['wrong_questions']} for x in report['status']])
        st.dataframe(df,use_container_width=True,hide_index=True)
    else: st.info('暂无足够数据。')
    st.subheader('📋 今日任务完成情况')
    for i,t in enumerate((plan or {}).get('tasks',[]),1):
        st.write(('✅' if t.get('completed') else '⬜') + f" {i}. {t.get('name')} · {t.get('minutes')}分钟")
    st.subheader('🔄 明日计划依据')
    for x in report['tomorrow_basis']:
        st.write('•',x)

# -------------------- RAG QA --------------------
else:
    st.subheader('💬 AI 知识库问答')
    st.caption('这里专门处理知识问题；“每日任务、学习进度、自适应分析”等功能命令不会再被送进 RAG。')
    query=st.text_area('输入你的问题',placeholder='例如：什么是动态规划法？结构化方法有哪些特点？',height=130)
    if st.button('🔎 查询知识库并回答',type='primary'):
        if not query.strip():
            st.warning('请先输入问题。')
        else:
            try:
                with st.spinner('正在检索知识库并生成回答...'):
                    ctx=agent.search_knowledge(query,5)
                    ans=agent.ai(f'''请根据以下软件设计师知识库回答用户问题。优先依据知识库；不能确定的内容明确说明；不要把系统功能命令当成知识概念。最后给出简短的“考试记忆点”。\n\n用户问题：{query}\n\n知识库：\n{ctx}''',temperature=0.25)
                st.session_state.qa_answer=ans; st.session_state.qa_context=ctx
            except Exception as e:
                st.error(f'问答失败：{e}')
    if st.session_state.qa_answer:
        st.markdown('### 🤖 AI回答')
        st.write(st.session_state.qa_answer)
        with st.expander('📚 查看本次RAG检索内容'):
            st.text(st.session_state.qa_context or '')

st.divider()
st.caption('软件设计师 AI 自适应学习 Agent · RAG + DeepSeek + ChromaDB + BGE · CLI 与 Streamlit 共用学习数据')
