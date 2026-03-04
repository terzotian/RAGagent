# AgenticRAG

## 项目描述

AgenticRAG 是一个基于 Retrieval-Augmented Generation (RAG) 框架的大学政策/课程/作业智能问答系统。旨在通过检索真实文档内容生成准确、易懂的答案，减少生成式模型的幻觉问题。

政策文档往往复杂冗长，难以快速提取所需信息。本系统结合检索和生成技术，为用户提供基于事实的可靠回答。

## 系统架构

系统采用前后端分离架构：

- **前端**：React + TypeScript + Vite，提供用户界面、文件管理和问答聊天。
- **后端**：FastAPI，提供RESTful API，包括用户管理、文件上传和流式问答。
- **数据库**：PostgreSQL + pgvector 扩展，存储用户、文件元数据和向量嵌入。
- **检索**：混合检索（pgvector 语义向量 + TF-IDF 关键词），RRF 融合。
- **生成**：优先 Google Vertex AI (Gemini)，回退本地 Ollama。
- **存储**：文件存储在 `.local_data/` 目录，支持本地和云端配置。

### 架构图

```mermaid
graph TB
    Client[Web Frontend<br/>React + Vite] -->|HTTP| API[FastAPI<br/>code/backend/main.py]

    subgraph Control[Control Plane<br/>Agent Orchestrator]
        Planner[Master Planner<br/>intent + scope] --> Rewrite[Query Rewrite<br/>standalone query]
    end

    subgraph Retrieval[Data Plane<br/>Hybrid Retrieval]
        Vec[pgvector search<br/>items table] --> Fusion[RRF Fusion<br/>Top 5 refs]
        Tfidf[TF-IDF search<br/>pieces/*.txt] --> Fusion
    end

    API -->|SSE /questions/stream| Planner
    Rewrite --> Vec
    Rewrite --> Tfidf
    Fusion --> Prompt[Prompt Builder<br/>rag_stream.build_prompt]

    subgraph LLM[LLM/Embedding]
        Vertex[Vertex AI<br/>Gemini + text-embedding-004]
        Ollama[Ollama Fallback]
    end

    Prompt --> Vertex
    Vertex -->|fallback| Ollama
    Ollama -->|stream tokens| API
    Vertex -->|stream tokens| API

    subgraph Store[Persistence]
        PG[(PostgreSQL<br/>users/files/sessions/questions/items)]
        FS[(.local_data<br/>knowledge_base/uploads/avatars)]
    end

    API --> PG
    API --> FS
    Vec --> PG
    Tfidf --> FS
```

## 功能特性

- **用户管理**：注册/登录，多角色权限（学生/老师/管理员）。
- **文件管理**：上传政策、课程资料和作业，自动索引和一致性删除。
- **智能问答**：基于检索的流式生成，支持对话上下文和临时文件。
- **会话历史**：保存问答记录和用户反馈。

## 安装与运行

### 前置要求

- Python 3.8+
- Node.js 16+
- Docker 和 Docker Compose
- PostgreSQL（可选，自带Docker）

### 1. 克隆仓库

```bash
git clone <repository-url>
cd AgenticRAG
```

### 2. 后端设置

```bash
# 激活虚拟环境（推荐）
conda create -n rag-agentic python=3.10
conda activate rag-agentic

# 安装依赖
pip install -r requirements.txt

# 设置环境变量（创建 .env 文件）
# DATABASE_URL=postgresql://postgres:password@localhost:5433/lurag
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json  # Vertex AI（可选）
# VERTEX_PROJECT_ID=your-project-id
# VERTEX_LOCATION=us-central1
# OLLAMA_BASE_URL=http://localhost:11434  # Ollama回退（可选）
# OLLAMA_GEN_MODEL=llama3.2
# LOCAL_DATA_DIR=./.local_data  # 数据目录（可选）
```

### 3. 数据库

使用Docker Compose启动PostgreSQL：

```bash
docker-compose up -d
```

或使用现有PostgreSQL，确保启用pgvector扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. 前端设置

```bash
cd web
npm install
npm run dev  # 开发模式，访问 http://localhost:5173
```

### 5. 运行后端

```bash
cd code
python -m backend.main
```

API文档：http://localhost:8536/docs

## 环境变量

- `DATABASE_URL`：PostgreSQL连接串（必需）
- `LOCAL_DATA_DIR`：数据目录路径（默认 `.local_data`）
- `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_PROJECT_ID` / `VERTEX_LOCATION`：Vertex AI配置（可选）
- `OLLAMA_BASE_URL` / `OLLAMA_GEN_MODEL`：Ollama配置（可选）
- `AUTO_CREATE_TABLES`：启动时自动创建表（默认1）

## 部署

### Docker部署

```bash
# 构建并运行
docker build -t agenticrag .
docker run -p 8536:8536 --env-file .env agenticrag
```

### 生产环境

- 使用反向代理（如Nginx）处理前端静态文件。
- 配置HTTPS和防火墙。
- 监控日志和性能。

## API文档

后端自动生成Swagger UI：http://localhost:8536/docs

主要端点：
- `/api/v1/auth/login`：用户登录
- `/api/v1/questions/stream`：问答流式接口
- `/api/v1/files/list`：文件列表
- `/api/v1/admin/policies`：上传政策（管理员）

## 贡献

欢迎提交Issue和Pull Request。请确保代码符合项目规范。

## 引用

1. Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive nlp tasks. *Advances in Neural Information Processing Systems*, 33, 9459-9474.
2. Gao, Y., et al. (2023). Retrieval-augmented generation for large language models: A survey. arXiv preprint arXiv:2312.10997.
3. Wu, J., et al. (2024). Medical Graph RAG: Towards safe medical large language model via graph retrieval-augmented generation. arXiv preprint arXiv:2408.04187.
