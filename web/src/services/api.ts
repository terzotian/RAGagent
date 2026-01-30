import axios from 'axios';

// 配置基础 API 路径，Vite 代理会转发 /api/v1 到后端
const API_BASE = '/api/v1';

// 通用 HTTP 客户端
const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// SSE 流式问答接口
export function streamAnswer(params: {
  session_id: string;
  question_id: string;
  previous_questions: string[];
  current_question: string;
  language: 'en' | 'zh-cn' | 'zh-tw';
  base: string;
  onToken: (token: string) => void;
  onReferences: (refs: any[]) => void;
  onDone: () => void;
  onError?: (err: any) => void;
}) {
  const query = new URLSearchParams({
    session_id: params.session_id,
    question_id: params.question_id,
    previous_questions: JSON.stringify(params.previous_questions),
    current_question: params.current_question,
    language: params.language,
    base: params.base,
  });

  const url = `${API_BASE}/questions/stream?${query.toString()}`;
  console.log('Connecting SSE:', url);

  const es = new EventSource(url);

  es.onmessage = (ev) => {
    try {
      if (ev.data === '[DONE]') {
        es.close();
        params.onDone();
        return;
      }

      const data = JSON.parse(ev.data);
      if (data.token) {
        params.onToken(data.token);
      }
      if (data.references) {
        params.onReferences(data.references);
      }
    } catch (e) {
      console.error('SSE parse error:', e);
    }
  };

  es.onerror = (err) => {
    console.error('SSE Error:', err);
    es.close();
    if (params.onError) params.onError(err);
    else params.onDone(); // 默认当做结束处理，防止 UI 卡死
  };

  return () => {
    es.close();
  };
}

// 文件相关接口
export interface FileItem {
  file_name: string;
  file_description: string;
  file_path: string;
  file_size: string;
  uploaded_at: string;
  base: string;
}

export const fileApi = {
  // 获取文件列表
  list: async (base: string) => {
    const res = await client.get<{ files: FileItem[] }>('/files/list', { params: { base } });
    return res.data.files;
  },

  // 上传文件
  upload: async (base: string, file: File) => {
    const fd = new FormData();
    fd.append('base', base);
    fd.append('file', file);
    // 上传文件时 Content-Type 设为 multipart/form-data
    const res = await client.post('/files', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // 删除文件
  delete: async (base: string, file_name: string) => {
    const res = await client.delete('/files', { params: { base, file_name } });
    return res.data;
  },

  // 获取预览文件内容（返回 Blob）
  preview: async (base: string, file_name: string) => {
    const res = await client.get('/files/preview', {
      params: { base, file_name },
      responseType: 'blob',
    });
    return res.data; // Blob
  },
};
