# AgenticRAG

## Project Description

AgenticRAG is an intelligent Q&A system for university policies, courses, and assignments based on the Retrieval-Augmented Generation (RAG) framework. It aims to provide accurate, easy-to-understand answers by retrieving real document content, reducing hallucinations in generative models.

Policy documents are often complex and lengthy, making it difficult to quickly extract needed information. This system combines retrieval and generation technologies to provide reliable answers grounded in facts.

## System Architecture

The system uses a front-end and back-end separated architecture:

- **Front-end**: React + TypeScript + Vite, providing user interface, file management, and Q&A chat.
- **Back-end**: FastAPI, providing RESTful APIs including user management, file upload, and streaming Q&A.
- **Database**: PostgreSQL + pgvector extension, storing users, file metadata, and vector embeddings.
- **Retrieval**: Hybrid retrieval (pgvector semantic vectors + TF-IDF keywords), RRF fusion.
- **Generation**: Prioritizes Google Vertex AI (Gemini), falls back to local Ollama.
- **Storage**: Files stored in `.local_data/` directory, supporting local and cloud configurations.

### Architecture Diagram

![AgenticRAG: dual-agent iterative RAG architecture](docs/AgenticRAG_Architecture_v2.png)

## Features

- **Home Page**: Dynamic images and a homepage designed in line with Lingnan University.
![Home Page](docs/home.png)
- **User Profile**: View and update personal information, including password.
![User Profile](docs/person page.png)
- **File Management**: Upload policies, course materials, and assignments, with automatic indexing and consistent deletion.
![File Management](docs/file.png)
- **Intelligent Q&A**: Streaming generation based on retrieval, supporting conversation context and temporary file uploads.
- **Session History**: Save Q&A records and user feedback.
![Session History](docs/chat.png)

## Installation and Running

### Prerequisites

- Python 3.8+
- Node.js 16+
- Docker and Docker Compose
- PostgreSQL (optional, Docker included)

### 1. Clone Repository

```bash
git clone <repository-url>
cd AgenticRAG
```

### 2. Backend Setup

```bash
# Activate virtual environment (recommended)
conda create -n rag-agentic python=3.10
conda activate rag-agentic

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
# DATABASE_URL=postgresql://postgres:password@localhost:5433/lurag
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json  # Vertex AI (optional)
# VERTEX_PROJECT_ID=your-project-id
# VERTEX_LOCATION=us-central1
# OLLAMA_BASE_URL=http://localhost:11434  # Ollama fallback (optional)
# OLLAMA_GEN_MODEL=llama3.2
# LOCAL_DATA_DIR=./.local_data  # Data directory (optional)
```

### 3. Database

Start PostgreSQL using Docker Compose:

```bash
docker-compose up -d
```

Or use existing PostgreSQL, ensure pgvector extension is enabled:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Frontend Setup

```bash
cd web
npm install
npm run dev  # Development mode, visit http://localhost:5173
```

### 5. Run Backend

```bash
cd code
python -m backend.main
```

API Documentation: http://localhost:8536/docs

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (required)
- `LOCAL_DATA_DIR`: Data directory path (default `.local_data`)
- `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_PROJECT_ID` / `VERTEX_LOCATION`: Vertex AI configuration (optional)
- `OLLAMA_BASE_URL` / `OLLAMA_GEN_MODEL`: Ollama configuration (optional)
- `AUTO_CREATE_TABLES`: Auto-create tables on startup (default 1)

## Deployment

### Docker Deployment

```bash
# Build and run
docker build -t agenticrag .
docker run -p 8536:8536 --env-file .env agenticrag
```

### Production Environment

- Use reverse proxy (e.g., Nginx) for front-end static files.
- Configure HTTPS and firewall.
- Monitor logs and performance.

## API Documentation

Backend auto-generates Swagger UI: http://localhost:8536/docs

Main endpoints:
- `/api/v1/auth/login`: User login
- `/api/v1/questions/stream`: Streaming Q&A interface
- `/api/v1/files/list`: File list
- `/api/v1/admin/policies`: Upload policies (admin)

## Contributing

Issues and Pull Requests are welcome. Ensure code follows project standards.

## References

1. Lewis, P., et al. (2020). Retrieval-augmented generation for knowledge-intensive nlp tasks. *Advances in Neural Information Processing Systems*, 33, 9459-9474.
2. Gao, Y., et al. (2023). Retrieval-augmented generation for large language models: A survey. arXiv preprint arXiv:2312.10997.
3. Wu, J., et al. (2024). Medical Graph RAG: Towards safe medical large language model via graph retrieval-augmented generation. arXiv preprint arXiv:2408.04187.
