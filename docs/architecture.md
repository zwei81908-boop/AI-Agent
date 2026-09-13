# 系统架构说明

## 分层
- **表现层**：Streamlit 页面。
- **Agent 层**：`agent.py` 负责出题、判题、学习状态、错题、自适应任务。
- **RAG 层**：`cloud_rag.py` 负责云端知识检索。
- **模型层**：DeepSeek + BGE Embedding。
- **数据层**：Supabase + 本地 JSON/ChromaDB。

## 核心数据流
用户问题 → 向量检索 → Top-K知识片段 → DeepSeek → 最终回答

用户答题 → 学习记录 → 错题分析 → 薄弱知识点 → 自适应任务 → 再训练
