# 软件设计师 AI 自适应学习 Agent

> 基于 DeepSeek + RAG + BGE Embedding + ChromaDB + Supabase + Streamlit 构建的智能学习系统。

## 项目简介
面向软件设计师学习场景，将大语言模型、RAG 知识库、学习行为分析、错题管理和自适应学习计划结合起来。系统支持知识库问答、AI专项训练、错题复习、学习报告、每日任务和自适应分析。

## 核心功能
- 📅 今日学习任务
- 📝 AI专项训练：动态出题、提交后判题与解析、重复题控制
- ❌ 错题复习与间隔复习
- 🧠 自适应学习分析
- 📊 学习报告
- 💬 RAG 知识库问答
- 📚 知识库管理
- ☁️ Supabase 云端数据
- 🚀 Streamlit Web 使用

## 系统架构
```text
用户/浏览器
    ↓
Streamlit Web
    ├── AI专项训练 ──→ DeepSeek
    ├── 知识库问答 ──→ RAG ──→ BGE Embedding ──→ 向量库
    └── 学习管理 ──→ 学习记录/错题
                         ↓
                    自适应分析
                         ↓
                 个性化任务/复习
                         ↓
                  Supabase / 本地数据
```

## 技术栈
| 技术 | 用途 |
|---|---|
| Python | Agent 核心逻辑 |
| Streamlit | Web UI |
| DeepSeek API | LLM、出题、问答 |
| RAG | 知识库增强问答 |
| BAAI/bge-small-zh-v1.5 | 中文向量化 |
| ChromaDB | 本地向量检索 |
| Supabase | 云端数据库、向量与存储 |
| PyMuPDF / OCR | PDF 知识库解析 |
| Git / GitHub | 版本管理 |

## RAG 流程
```text
PDF → 文本/OCR → 清洗分块 → BGE Embedding → 向量数据库
                                              ↓
用户问题 → 相似度检索 → Top-K知识片段 → DeepSeek → 回答
```

## 自适应学习闭环
```text
答题 → 学习记录 → 错题分析 → 薄弱知识点 → 每日任务/专项训练
                                              ↓
                                           间隔复习
                                              ↓
                                           再次评估
```

## 项目亮点
1. **RAG 专业知识库**：先检索软件设计师资料，再结合大模型回答。
2. **自适应学习**：根据真实答题行为识别薄弱知识点。
3. **错题闭环**：答错 → 保存 → 分析 → 复习 → 再评估。
4. **AI专项训练**：提交前隐藏答案，提交后才展示结果；保存历史题目指纹避免重复。
5. **云端化**：知识和学习数据可通过 Supabase 持久化。

## 本地运行
```powershell
cd D:\work\AI-Agent
.\.venv\Scripts\python.exe -m streamlit run app.py
```
也可以双击 `start.bat`。

## 环境变量
复制 `.env.example` 为 `.env`，配置：
```text
DEEPSEEK_API_KEY=你的API Key
SUPABASE_URL=你的Supabase地址
SUPABASE_KEY=你的Supabase Key
```
不要将真实 `.env` 提交到 GitHub。

## 面试一句话
> 我做了一个基于 DeepSeek 和 RAG 的软件设计师 AI 自适应学习 Agent，能够读取专业知识库，根据用户答题和错题数据识别薄弱知识点，并自动生成专项训练、错题复习和个性化学习任务。

## 后续扩展
多用户隔离、更多题库、RAG 重排序、学习曲线可视化、流式回答和更完善的学习策略。
