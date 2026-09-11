

RAG知识库
   ↓
DeepSeek
   ↓
AI出题
   ↓
自动批改
   ↓
学习记录
   ↓
错题库
   ↓
间隔复习
   ↓
自适应分析
   ↓
动态学习计划
   ↓
学习报告

接下来进入最后的项目整理阶段。

V9：把项目整理成真正的作品

我们先做第一件事：生成 requirements.txt，以后换电脑可以一键安装环境。

在 VS Code 终端执行：

cd D:\work\AI-Agent
.\.venv\Scripts\python.exe -m pip freeze > requirements.txt

然后检查：

Get-Content requirements.txt

应该能看到类似：

chromadb==...
openai==...
pypdf==...
python-dotenv==...
sentence-transformers==...
torch==...
transformers==...
接下来

做完后我们继续：

V10 → README 项目说明

V11 → 整理项目目录

V12 → 完善启动方式

V13 → 最终项目打包

V14 → 简历项目描述 + 面试介绍

最终你会得到一个比较完整的：

基于 RAG + DeepSeek + 自适应学习策略的智能学习 Agent

现在先执行上面的两条命令。

执行完成后告诉我：

“requirements好了”

我们马上继续 README。

今天 13:10
下一步我们做最后的项目目录整理 + 一键启动优化，然后我会给你整理一份**“这个项目怎么写进简历、面试时怎么讲”**的版本。 继续

可以。现在我们不再加功能，直接把项目整理成能一键启动、结构清晰、适合放简历的版本。

第一步：先整理目录

你现在的项目：

D:\work\AI-Agent

建议最终整理成：

AI-Agent/
│
├─ agent.py                  # 主程序
├─ start.bat                 # Windows 一键启动
├─ requirements.txt          # Python依赖
├─ .env                      # API Key（不要上传）
├─ .gitignore                # Git忽略文件
├─ README.md                 # 项目说明
│
├─ knowledge/
│   └─ 软件设计师笔记.pdf
│
├─ chroma_db/                # RAG向量数据库
│
├─ data/
│   ├─ wrong_questions.json
│   ├─ learning_records.json
│   └─ daily_tasks.json
│
└─ docs/
    └─ 项目说明.md

不过不要现在手动移动文件，因为你的 agent.py 目前很可能还是按照根目录读取：

WRONG_QUESTIONS_FILE
LEARNING_RECORDS_FILE
DAILY_TASKS_FILE

贸然移动 JSON 会导致程序找不到数据。

所以我们分两步做

第一步：我先给 agent.py 做路径兼容升级。

让它自动使用：

data/

保存学习数据，同时兼容你现有的 JSON 数据，不会把之前的学习记录和错题弄丢。

然后再整理目录。

第二步：一键启动

目录整理好以后，你以后不需要再输入：

.\.venv\Scripts\python.exe agent.py

只需要双击：

start.bat

就可以启动：

🤖 软件设计师 AI 自适应学习 Agent
第三步：安全配置

.env：

DEEPSEEK_API_KEY=你的Key

.gitignore：

.env
.venv/
__pycache__/
chroma_db/
*.pyc

这样以后如果上传 GitHub，API Key 不会被一起上传。

第四步：README

最后给项目写成：

软件设计师 AI 自适应学习 Agent

技术栈：
Python
DeepSeek API
RAG
BGE Embedding
ChromaDB
Sentence Transformers

核心功能：
1. RAG知识问答
2. AI自动出题
3. 自动批改
4. 错题管理
5. 间隔复习
6. 自适应学习
7. 动态学习计划
8. 学习数据分析
9. 学习报告
🚀 我们现在先做最重要的一步

不要自己移动任何文件。

我下一步直接给你生成：

agent_final.py
start.bat
.gitignore
README.md

并把路径问题一次处理好。

然后你只需要：

替换 agent.py
↓
运行 start.bat
↓
测试
↓
完成

之后我们就进入你说的最后部分：

简历怎么写 + 面试怎么讲 + 面试官可能问什么 + 你怎么回答。

这样整个项目就真正收尾了。

好

好，直接把最终整理版给你。V7 的功能保留，并把数据目录、一键启动、Git 安全配置、README 都整理好了。

① 下载最终主程序

下载 agent_final.py

把它改名为：

agent.py

放到：

D:\work\AI-Agent

覆盖旧版。

这个版本会自动把你以前的：

wrong_questions.json
learning_records.json
daily_tasks.json

迁移到：

data\

不会让你重新开始。

② 下载一键启动

下载 start.bat

把它放到：

D:\work\AI-Agent

以后你只需要双击 start.bat，不用再输入 Python 命令。

③ 下载 README

下载 README.md

放到项目根目录。

④ 下载安全配置

下载 .gitignore

放到：

D:\work\AI-Agent

它会防止 .env、虚拟环境、个人学习数据等被误上传。

另外：

下载 .env.example

这个只是模板，你实际使用的 .env 不要上传 GitHub。

最终目录

整理完后应该是：

D:\work\AI-Agent
│
├── agent.py
├── start.bat
├── requirements.txt
├── README.md
├── .gitignore
├── .env
│
├── knowledge
│   └── 软件设计师笔记.pdf
│
├── chroma_db
│
└── data
    ├── wrong_questions.json
    ├── learning_records.json
    └── daily_tasks.json
注意

你的 chroma_db 暂时不要移动，否则可能导致现有知识库找不到。

🚀 最后测试

全部放好以后，直接双击：

start.bat

然后输入：

帮助

再输入：

学习进度

如果正常，项目整理就完成了。


一个基于 DeepSeek + RAG + BGE Embedding + ChromaDB 的软件设计师智能学习 Agent。

核心功能
RAG 知识库问答
AI 自动出题
自动批改
自动保存与分析错题
自适应专项训练
学习记录
动态学习计划
每日任务管理
错题间隔复习
学习报告
自适应分析
根据学习数据调整后续计划
项目结构
AI-Agent/
├─ agent.py
├─ start.bat
├─ requirements.txt
├─ .env
├─ .env.example
├─ .gitignore
├─ README.md
├─ knowledge/
│  └─ 软件设计师笔记.pdf
├─ chroma_db/
└─ data/
   ├─ wrong_questions.json
   ├─ learning_records.json
   └─ daily_tasks.json

chroma_db/ 和 data/*.json 属于本地运行数据，不建议上传 GitHub。

Windows 一键启动

双击 start.bat 即可。

如果虚拟环境或依赖还没有安装，在 VS Code 终端执行：

.\.venv\Scripts\python.exe -m pip install -r requirements.txt
API Key

在项目根目录创建 .env：

DEEPSEEK_API_KEY=你的DeepSeek_API_Key

不要把 .env 上传到 GitHub。

常用命令
开始今天学习
每日任务
完成任务1
开始专项训练
开始错题复习
查看复习安排
学习进度
分析我的错题
自适应分析
重新制定今天计划
学习报告
总结今天学习
帮助
exit
技术流程
PDF知识库
   ↓
文本切分
   ↓
BGE中文向量模型
   ↓
ChromaDB
   ↓
RAG检索
   ↓
DeepSeek
   ↓
出题 / 批改 / 解释
   ↓
学习记录 + 错题库
   ↓
间隔复习
   ↓
自适应分析
   ↓
动态学习计划
数据安全

学习记录、错题和 API Key 都属于本地数据。提交代码仓库时，请确认 .env 和个人学习数据没有被上传。
