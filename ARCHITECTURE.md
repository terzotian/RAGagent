# Agentic RAG System Architecture

This document provides a comprehensive architectural overview of the Agentic RAG system, featuring both a text-based representation and a detailed academic-style diagram.

## 1. High-Level Text Architecture

The system is designed as a **Micro-Kernel Architecture** with clear separation between the Control Plane (Agent Router) and the Data Plane (Retrieval Engine).

```text
+-----------------------------------------------------------------------------+
|                        PRESENTATION LAYER (Frontend)                        |
|                                                                             |
|    [ Web Client ] ................................. (React SPA / Firebase)  |
|          |                                                                  |
+----------|------------------------------------------------------------------+
           | HTTPS / WSS
           v
+-----------------------------------------------------------------------------+
|                        APPLICATION KERNEL (Backend)                         |
|                                                                             |
|    [ API Gateway ] ............................... (FastAPI / Cloud Run)    |
|          |                                                                  |
|          v                                                                  |
|    +---------------------------+         +-----------------------------+    |
|    |  CONTROL PLANE            |         |  DATA PLANE                 |    |
|    |  (Agent Orchestrator)     |         |  (Retrieval Engine)         |    |
|    |                           |         |                             |    |
|    |  [1] Intent Classifier    |-------->|  [1] Query Processor        |    |
|    |      (Router)             |         |      (Hybrid Search)        |    |
|    |                           |         |                             |    |
|    |  [2] Domain Router        |         |  [2] Rank Fusion            |    |
|    |      (Course/Policy)      |         |      (Reranking)            |    |
|    |                           |         |                             |    |
|    |  [3] Prompt Engineer      |<--------|                             |    |
|    |      (Persona Injection)  |         |                             |    |
|    +---------------------------+         +-----------------------------+    |
|                                                                             |
+-----------------------------------------------------------------------------+
           |
           v
+-----------------------------------------------------------------------------+
|                        INFRASTRUCTURE LAYER (Data)                          |
|                                                                             |
|   [ Model Service ]    [ Vector Store ]    [ Metadata DB ]    [ Doc Store ] |
|   (Ollama / vLLM)      (ChromaDB)          (PostgreSQL)       (FileSystem)  |
+-----------------------------------------------------------------------------+
```

---

## 2. Detailed System Diagram (Academic Style)

This diagram utilizes a **nested block layout** with a **Top-Down (TB)** flow to maximize space efficiency and readability. By stacking layers vertically, we reduce horizontal whitespace and allow text to be larger and clearer.

```mermaid
graph TB
    %% ==========================================
    %% Styling Configuration
    %% ==========================================
    classDef clientNode fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1,font-weight:bold;
    classDef apiNode fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20,font-weight:bold;
    classDef logicNode fill:#FFF3E0,stroke:#EF6C00,stroke-width:2px,color:#E65100;
    classDef storageNode fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#4A148C;
    classDef aiNode fill:#FFEBEE,stroke:#C62828,stroke-width:2px,color:#B71C1C;

    %% ==========================================
    %% 1. User Interface (Top)
    %% ==========================================
    subgraph Frontend ["Presentation Layer"]
        Client["Web Client (React SPA)"]:::clientNode
    end

    %% ==========================================
    %% 2. Backend Core (Middle)
    %% ==========================================
    subgraph Backend ["Application Core (Cloud Run)"]
        direction TB

        API["API Gateway (FastAPI)"]:::apiNode

        %% Logic Block - Side by Side
        subgraph LogicBlock ["Agent & Retrieval Logic"]
            direction LR

            subgraph Orchestrator ["Agent Orchestrator"]
                direction TB
                Intent{"Intent\nClassifier"}:::logicNode
                Router{"Domain\nRouter"}:::logicNode
                Prompt["Prompt\nEngineer"]:::logicNode
            end

            subgraph Retrieval ["Hybrid Engine"]
                direction TB
                QueryProc["Query\nProcessor"]:::logicNode
                Fusion["Fusion &\nRe-ranker"]:::logicNode
            end
        end
    end

    %% ==========================================
    %% 3. Infrastructure & Data (Bottom)
    %% ==========================================
    subgraph Infra ["Infrastructure & Data Layer"]
        direction LR

        subgraph Models ["Model Serving"]
            LLM["LLM Service\n(Ollama)"]:::aiNode
        end

        subgraph Data ["Persistence"]
            VecDB[("Vector DB\n(Chroma)")]:::storageNode
            RelDB[("Metadata\n(Postgres)")]:::storageNode
            FileDB[("Doc Store\n(Files)")]:::storageNode
        end
    end

    %% ==========================================
    %% Interactions (Compact Flow)
    %% ==========================================

    Client <==>|"HTTPS"| API
    API --> Intent

    Intent -- "Chitchat" --> LLM
    Intent -- "Retrieval" --> Router

    Router -- "Context" --> QueryProc
    Router -.->|"Persona"| Prompt

    QueryProc --> VecDB
    QueryProc --> FileDB

    VecDB & FileDB --> Fusion

    Fusion -->|"Top-K"| Prompt
    Prompt -->|"Full Prompt"| LLM

    LLM -->|"Stream"| API
    API -.->|"Auth"| RelDB

    %% Link Styling
    linkStyle default stroke:#616161,stroke-width:1.5px;
```

## Architectural Design Principles

### 1. Separation of Concerns
The system strictly separates the **Orchestration Logic** (deciding *what* to do) from the **Execution Logic** (performing the search). The `Agent Router` acts as the control plane, while the `Hybrid Retrieval Engine` acts as the data plane.

### 2. Adaptive Retrieval
Unlike traditional RAG systems that treat all queries equally, this architecture implements **Domain-Aware Routing**.
- **Course Queries**: Heavily weight the vector similarity from course-specific namespaces.
- **Policy Queries**: Prioritize exact keyword matches from the official handbook to ensure compliance.

### 3. Hybrid Intelligence
The system combines:
- **Symbolic AI**: Rule-based routing and TF-IDF keyword matching for precision.
- **Neural AI**: Vector embeddings and LLM generation for semantic understanding and fluidity.
