# AgentRAG

## Project Description
Developing a Policy QA System Using Retrieval-Augmented Generation (RAG) Framework.

Policies are often complex, lengthy, and filled with technical language, making it challenging for individuals to extract the specific information they need efficiently. This project aims to bridge this gap by providing concise, accurate, and user-friendly answers to policy-related queries.

This project addresses the hallucination problem commonly found in generation-based systems by developing a QA system based on the Retrieval-Augmented Generation (RAG) framework. RAG combines the best of retrieval-based and generation-based approaches, aiming to significantly reduce hallucinations in language model outputs by grounding answers in factual, retrieved data.

## System Architecture

The RAG framework operates through two main components:
1. **Retrieval**: Retrieves relevant policy documents or sections from policy documents based on user queries.
2. **Generation**: Synthesizes an easy-to-understand response based on the retrieved content.

Unlike standalone generative models that may invent fake details when faced with incomplete information, the RAG approach ensures that all answers are firmly rooted in the retrieved policy data. This enhances the credibility and reliability of the system.

## Setup & Running

### 1. Database
This project uses MySQL to store historical data. Ensure you have a MySQL instance running and configured.

### 2. Environment Variables
Ensure you have `unzip` installed.
```bash
sudo apt update
sudo apt install unzip
```

Unzip the environment file:
```bash
cd code/backend/model
unzip env.zip
```

### 3. Backend Setup
Use `python3` to start the FastAPI backend service. It is recommended to run in a virtual environment.

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install dependencies
cd code
pip install --upgrade -r requirements.txt

# Run the backend
python -m backend.main
```

You can then verify the API is running by visiting `http://localhost:8536/docs` (if Swagger UI is enabled) or testing an endpoint like `http://localhost:8536/api/v1/files/list`.

## References

1. Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., ... & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive nlp tasks. Advances in Neural Information Processing Systems, 33, 9459-9474.
2. Gao, Y., Xiong, Y., Gao, X., Jia, K., Pan, J., Bi, Y., ... & Wang, H. (2023). Retrieval-augmented generation for large language models: A survey. arXiv preprint arXiv:2312.10997.
3. Wu, J., Zhu, J., Qi, Y., Chen, J., Xu, M., Menolascina, F., & Grau, V. (2024). Medical Graph RAG: Towards safe medical large language model via graph retrieval-augmented generation. arXiv preprint arXiv:2408.04187.
