import os
import asyncio
from pathlib import Path
from backend.model.doc_analysis import read_file, split_sentences
from backend.root_path import piece_dir

async def ingest_file(base: str, file_path: str):
    """
    传统 RAG 索引流程：
    1. 读取文件内容 (Text Extraction)
    2. 文本切片 (Chunking)
    3. 保存为片段文件 (Saving segments)
    """
    print(f"DEBUG: Starting traditional ingestion for {file_path} into base {base}")

    # 1. 读取内容
    try:
        content = read_file(file_path)
        if not content or content.startswith("unsupported"):
            print(f"Warning: Could not read content from {file_path}")
            return
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return

    # 2. 文本切片
    # 简单策略：按句子切分，每 N 句合并为一个 Chunk
    sentences = split_sentences(content)

    chunks = []
    chunk_size = 10 # 每个片段包含的句子数
    overlap = 2     # 重叠句子数

    # 如果 split_sentences 失败（比如没有正确识别到句号），把整个 content 当作一个 sentence
    if not sentences and len(content) > 0:
        sentences = [content]

    for i in range(0, len(sentences), chunk_size - overlap):
        chunk_sentences = sentences[i : i + chunk_size]
        chunk_text = " ".join(chunk_sentences)
        # 只要不是空的，或者长度大于20，就保留。放宽限制。
        if len(chunk_text.strip()) > 5:
            chunks.append(chunk_text)

    if not chunks:
        # 兜底：按长度强行切分
        if len(content) > 0:
            chunks = [content[i:i+500] for i in range(0, len(content), 400)]

    # 3. 保存片段
    # 目标目录：backend/knowledge_base/{base}/pieces/
    # doc_search.py 会读取这个目录下的所有文件

    # 获取 pieces 目录路径
    # piece_dir 是一个函数，返回 Path 对象
    save_dir = piece_dir(base=base)
    os.makedirs(save_dir, exist_ok=True)

    file_name = os.path.basename(file_path)
    # 构造保存的文件名，例如: {original_filename}.txt
    # 内容格式需符合 load_segments_from_file 的要求: "--- Segment X ---"

    output_filename = f"{file_name}.txt"
    output_path = os.path.join(save_dir, output_filename)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, chunk in enumerate(chunks):
            f.write(f"--- Segment {i+1} ---\n")
            f.write(chunk + "\n\n")

    print(f"DEBUG: Successfully indexed {len(chunks)} segments to {output_path}")
