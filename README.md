# 软件设计师 AI 自适应学习 Agent

> 基于 DeepSeek + RAG + ChromaDB + Supabase + Streamlit 构建的智能学习系统  
> 面向软件设计师考试场景，实现知识库问答、AI 自动出题、智能判题、错题管理、学习记录、自适应学习任务以及云端数据持久化。

---

## 📌 项目简介

本项目是一套面向软件设计师考试的 AI 自适应学习 Agent。

传统的刷题系统通常只能完成：

- 题目展示
- 用户答题
- 判断对错
- 保存错题

本项目在此基础上引入 **大语言模型（LLM）+ RAG + 学习行为分析**，让系统能够根据用户的学习记录和答题情况，动态分析薄弱知识点，并生成针对性的学习任务和练习内容。

系统采用前后端一体化的轻量 Web 架构，通过 Streamlit 提供用户界面，通过 DeepSeek 提供大模型能力，通过 ChromaDB 实现知识库向量检索，通过 Supabase 实现云端数据持久化。

目前系统已经完成本地运行、GitHub 管理、Streamlit Community Cloud 云端部署，并支持手机、平板等设备直接访问。

---

# 🎯 项目目标

项目主要解决传统学习系统中以下问题：

1. 学习内容缺乏针对性
2. 刷题后缺少系统分析
3. 错题不能进行有效复习
4. 学习记录无法长期保存
5. 知识库内容与 AI 问答脱节
6. 学习任务通常需要用户手动制定

因此，本项目希望实现：

> **让 AI 根据用户的学习数据自动判断“哪里不会”，然后决定“接下来学什么”。**

---

# ✨ 核心功能

## 1. 🤖 AI 知识库问答

基于 RAG（Retrieval-Augmented Generation）实现软件设计师知识库问答。

用户输入问题后：

```text
用户问题
   ↓
问题向量化
   ↓
ChromaDB 向量检索
   ↓
获取相关知识
   ↓
构建上下文
   ↓
DeepSeek
   ↓
生成回答
例如：

用户：
什么是结构化方法？

系统：
根据知识库中的相关内容进行检索，
再结合 DeepSeek 生成针对性的解释。

相比直接调用大模型，RAG 可以让回答更多地参考项目自己的专业知识库。

2. 🎯 AI 专项训练

系统能够根据指定知识点生成练习题。

训练流程：

选择知识点
    ↓
AI 生成题目
    ↓
用户选择答案
    ↓
提交
    ↓
AI / Agent 判断结果
    ↓
显示正确答案
    ↓
显示解析
    ↓
保存学习记录
    ↓
错误题目进入错题系统

当前支持：

AI 自动出题
选择题训练
用户答题
自动判题
显示正确答案
显示题目解析
学习记录保存
错题自动保存
3. ❌ 智能错题系统

用户答错题目后，系统会自动将错题记录下来。

错题包含：

题目
选项
正确答案
用户答案
题目解析
所属知识点
复习次数
下次复习时间
是否已经掌握

错题学习流程：

答错
 ↓
自动记录
 ↓
进入错题库
 ↓
根据复习安排再次出现
 ↓
重新作答
 ↓
判断是否掌握
 ↓
更新错题状态

系统不会只简单保存错题，而是将错题作为后续自适应学习的重要数据来源。

4. 📋 每日学习任务

系统可以根据用户当前学习情况生成每日学习任务。

任务可以包含：

知识点学习
错题复习
专项训练
概念辨析
综合练习
模拟训练

任务完成状态会被记录。

例如：

今日学习任务

1. 单元测试驱动模块与桩模块强化       ✅
2. 软件开发方法错题重做               ⬜
3. 软件开发方法专项练习               ⬜
4. 软件生存周期阶段划分巩固           ⬜
5. 综合模拟与错题整理                 ⬜
5. 🧠 自适应学习分析

系统会根据用户的历史学习数据分析知识点掌握情况。

基本流程：

学习记录
   ↓
统计答题结果
   ↓
分析知识点
   ↓
计算掌握情况
   ↓
识别薄弱知识点
   ↓
选择重点学习方向
   ↓
生成学习任务

例如：

软件开发方法      掌握度：43%
操作系统          掌握度：68%
数据库            掌握度：82%

系统会优先推荐掌握度较低的知识点。

6. 📊 学习数据记录

系统记录用户学习行为，包括：

学习题目
用户答案
是否正确
得分
知识点
学习时间

这些数据可以用于后续：

错题分析
知识点掌握度分析
自适应学习
学习报告
学习计划调整
7. ☁️ 云端数据持久化

项目使用 Supabase 保存学习数据。

数据库主要包括：

learning_records
    ↓
学习记录

wrong_questions
    ↓
错题数据

daily_tasks
    ↓
每日任务

系统结构：

Streamlit
    ↓
AI Agent
    ↓
Supabase
    ├── learning_records
    ├── wrong_questions
    └── daily_tasks

这样可以避免学习数据只保存在本地电脑。

8. 📱 多设备访问

项目已经部署到 Streamlit Community Cloud。

用户可以通过：

Windows 电脑
手机
平板

直接访问 Web 应用。

部署后的系统不要求用户本地安装 Python 环境，也不要求用户启动本地 Streamlit 服务。

🏗️ 系统架构

整体系统架构如下：

                         用户
                          │
             ┌────────────┼────────────┐
             │            │            │
            PC           手机         平板
             │            │            │
             └────────────┼────────────┘
                          │
                          ▼
                ┌─────────────────┐
                │    Streamlit    │
                │     Web UI      │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │     AI Agent    │
                │   核心业务逻辑   │
                └───────┬─────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
     ┌─────────┐   ┌─────────┐   ┌─────────┐
     │ DeepSeek│   │  RAG    │   │学习分析 │
     │   LLM   │   │知识检索 │   │自适应系统│
     └─────────┘   └────┬────┘   └────┬────┘
                        │             │
                        ▼             │
                   ┌─────────┐        │
                   │ChromaDB │        │
                   │向量数据库│        │
                   └─────────┘        │
                                      │
                        ┌─────────────┘
                        ▼
                  ┌────────────┐
                  │  Supabase  │
                  │ 云端数据库  │
                  └─────┬──────┘
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          学习记录     错题       每日任务
🔍 RAG 工作流程

项目的知识库问答采用 RAG 架构。

完整流程：

                 用户问题
                    │
                    ▼
             文本 Embedding
                    │
                    ▼
             ChromaDB 检索
                    │
              Top-K 相关知识
                    │
                    ▼
             构建 Prompt
                    │
                    ▼
                DeepSeek
                    │
                    ▼
               AI 最终回答

RAG 的主要作用是：

在生成答案之前先从项目知识库中检索相关内容，再让大模型基于检索结果生成回答。

这样可以减少模型完全依赖自身参数知识的情况。

🧩 技术栈
技术	用途
Python	核心开发语言
DeepSeek API	大语言模型
OpenAI SDK	调用 DeepSeek API
RAG	知识增强生成
ChromaDB	向量数据库
BGE Embedding	文本向量化
Streamlit	Web 应用界面
Supabase	云端数据库
JSON	本地数据及配置
Git	版本控制
GitHub	项目代码托管
Streamlit Community Cloud	云端部署
📁 项目结构
AI-Agent/
│
├── app.py
│       Streamlit Web 应用
│
├── agent.py
│       AI Agent 核心逻辑
│
├── database.py
│       Supabase 数据库操作
│
├── rag_chat.py
│       RAG 知识库问答相关逻辑
│
├── build_rag.py
│       构建知识库
│
├── main.py
│       项目测试 / 调试入口
│
├── day01.py
│       项目学习 / 开发测试代码
│
├── requirements.txt
│       Python 依赖
│
├── start.bat
│       Windows 本地快速启动
│
├── knowledge/
│       知识库相关文件
│
├── chroma_db/
│       ChromaDB 向量数据库
│
├── README.md
│       项目说明
│
├── .gitignore
│       Git 忽略配置
│
└── .env
        本地环境变量
🗄️ 数据库设计

项目使用 Supabase 保存核心学习数据。

learning_records

用于保存用户学习行为。

主要字段：

id
user_id
topic
question
answer
is_correct
score
created_at
wrong_questions

用于保存错题。

主要字段：

id
user_id
question
options
correct_answer
user_answer
explanation
topic
review_count
next_review_at
mastered
created_at
daily_tasks

用于保存每日学习任务。

主要字段：

id
user_id
task_date
task_index
task_content
completed
created_at
🔄 核心业务闭环

本项目最核心的设计不是单独的 AI 问答，而是：

                  用户学习
                     │
                     ▼
                  AI出题
                     │
                     ▼
                  用户答题
                     │
              ┌──────┴──────┐
              │             │
             正确           错误
              │             │
              ▼             ▼
          学习记录        错题记录
              │             │
              └──────┬──────┘
                     ▼
                  数据分析
                     │
                     ▼
               知识点掌握度
                     │
                     ▼
                薄弱知识点
                     │
                     ▼
               自适应学习任务
                     │
                     ▼
                  再次学习
                     │
                     └──────────► 循环

这构成了项目的核心：

学习 → 记录 → 分析 → 调整 → 再学习

🧠 Agent 设计

Agent 并不是简单的聊天机器人，而是负责协调多个模块。

主要职责包括：

AI Agent
│
├── 知识库问答
│
├── AI出题
│
├── 自动判题
│
├── 错题记录
│
├── 错题复习
│
├── 学习记录
│
├── 每日任务
│
├── 自适应分析
│
└── 学习报告

Agent 根据用户当前操作选择对应功能，而不是所有请求都直接发送给大模型。

🖥️ Web 功能页面

当前 Web 系统主要包含：

🏠 今日任务

🎯 AI专项训练

❌ 错题复习

🧠 自适应分析

📊 学习报告

📚 AI知识库问答
🚀 本地运行
1. 克隆项目
git clone https://github.com/zwei81908-boop/AI-Agent.git

进入项目：

cd AI-Agent
2. 创建虚拟环境
python -m venv .venv

激活环境：

Windows PowerShell：

.\.venv\Scripts\Activate.ps1
3. 安装依赖
pip install -r requirements.txt
4. 配置环境变量

创建：

.env

配置：

DEEPSEEK_API_KEY=你的DeepSeek_API_Key
SUPABASE_URL=你的Supabase_URL
SUPABASE_KEY=你的Supabase_Key

注意：

.env 不应该提交到 GitHub。

5. 启动 Web 应用
streamlit run app.py

也可以在 Windows 下直接双击：

start.bat
☁️ 云端部署

项目使用：

Streamlit Community Cloud

进行部署。

基本流程：

GitHub
   ↓
Streamlit Community Cloud
   ↓
部署 app.py
   ↓
配置 Secrets
   ↓
启动 Web 应用
   ↓
手机 / 平板访问

云端需要配置：

DEEPSEEK_API_KEY = "你的DeepSeek_API_Key"
SUPABASE_URL = "你的Supabase_URL"
SUPABASE_KEY = "你的Supabase_Key"

敏感信息不提交到 GitHub。

🔐 安全说明

项目中的 API Key、数据库 Key 等敏感信息通过环境变量或云端 Secrets 管理。

本地：

.env

云端：

Streamlit Secrets

并通过 .gitignore 避免敏感配置进入 Git 仓库。

📈 当前项目完成情况
功能	状态
Python Agent	✅
DeepSeek 接入	✅
RAG 知识库	✅
ChromaDB	✅
AI 知识库问答	✅
AI 自动出题	✅
自动判题	✅
正确答案显示	✅
错题记录	✅
错题复习	✅
学习记录	✅
每日任务	✅
任务完成记录	✅
自适应分析	✅
学习报告	✅
Supabase 云端数据库	✅
Streamlit Web	✅
GitHub 项目管理	✅
Streamlit Cloud 部署	✅
手机 / 平板访问	✅
云端 RAG	✅
跨设备使用	✅
AI 响应性能进一步优化	🔄 后续优化
多用户数据隔离	🔄 后续优化
💡 项目亮点
亮点一：AI + RAG

不是简单调用大模型，而是结合自己的专业知识库：

知识库
 +
向量检索
 +
DeepSeek
 =
知识增强问答
亮点二：学习数据驱动

系统会记录用户的实际学习行为：

答题结果
+
知识点
+
错题
+
学习任务

然后用于后续学习分析。

亮点三：自适应学习

根据学习结果识别薄弱知识点，并调整后续学习任务。

实现：

数据
 ↓
分析
 ↓
决策
 ↓
任务

而不是固定学习计划。

亮点四：云端化

项目已经从单纯的本地 Python 项目升级为：

本地开发
    ↓
GitHub
    ↓
Streamlit Cloud
    ↓
Supabase
    ↓
移动端访问

用户不需要一直打开电脑运行程序。