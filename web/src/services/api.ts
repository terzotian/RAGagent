import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1'; // Use direct backend URL to bypass Vite proxy

const client = axios.create({
  baseURL: API_BASE_URL,
});

export interface Reference {
  file_name: string;
  similarity: number;
}

export interface User {
  user_id: number;
  account: string;
  nickname: string;
  gender: string;
  identity: string;
  avatar_path?: string;
}

export const getAvatarUrl = (filename?: string) => {
  if (!filename) return '';
  return `${API_BASE_URL}/avatars/${filename}`;
};

export interface FileItem {
  file_name: string;
  file_description: string;
  file_path: string;
  file_size: string;
  uploaded_at: string;
  base: string;
}

export const fileApi = {
  list: async (base: string) => {
    const res = await client.get('/files/list', { params: { base } });
    return res.data.files;
  },

  upload: async (base: string, file: File) => {
    const formData = new FormData();
    formData.append('base', base);
    formData.append('file', file);
    const res = await client.post('/files', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  delete: async (base: string, fileName: string) => {
    const res = await client.delete('/files', {
      params: { base, file_name: fileName }
    });
    return res.data;
  },

  preview: async (base: string, file_name: string) => {
    const res = await client.get('/files/preview', {
      params: { base, file_name },
      responseType: 'blob'
    });
    return res.data;
  }
};

export const api = {
  // Auth methods
  register: async (data: any) => {
    const res = await client.post('/auth/register', data);
    return res.data;
  },

  login: async (data: any) => {
    const res = await client.post('/auth/login', data);
    return res.data;
  },

  updateProfile: async (userId: number, data: any) => {
    const res = await client.put(`/users/${userId}`, data);
    return res.data;
  },

  updatePassword: async (userId: number, data: any) => {
    const res = await client.put(`/users/${userId}/password`, data);
    return res.data;
  },

  uploadAvatar: async (userId: number, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post(`/users/${userId}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getUserSessions: async (userId: number) => {
    const res = await client.get(`/users/${userId}/sessions`);
    return res.data;
  },

  getSessionMessages: async (sessionId: string) => {
    const res = await client.get(`/sessions/${sessionId}/messages`);
    return res.data;
  }
};

export const streamAnswer = async (params: {
    session_id: string;
    question_id: string;
    previous_questions: string[];
    current_question: string;
    language: string;
    base: string;
    user_id?: number;
    onToken: (token: string) => void;
    onReferences: (refs: Reference[]) => void;
    onDone: () => void;
    onError: () => void;
}) => {
    let url = `${API_BASE_URL}/questions/stream?session_id=${params.session_id}&question_id=${params.question_id}&previous_questions=${encodeURIComponent(JSON.stringify(params.previous_questions))}&current_question=${encodeURIComponent(params.current_question)}&language=${params.language}&base=${params.base}`;
    
    if (params.user_id) {
        url += `&user_id=${params.user_id}`;
    }

    const controller = new AbortController();
    const signal = controller.signal;

    try {
        const response = await fetch(url, {
            signal,
            headers: {
                'Accept': 'text/event-stream',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        if (!response.body) {
            throw new Error('Response body is null');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }

            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ''; // Keep the incomplete part

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6);
                    
                    if (dataStr === '[DONE]') {
                        params.onDone();
                        return controller; // Return controller but we are done
                    }

                    try {
                        const data = JSON.parse(dataStr);
                        if (data.token) {
                            params.onToken(data.token);
                        } else if (data.references) {
                            params.onReferences(data.references);
                        } else if (data.error) {
                            console.error('Stream error from server:', data.error);
                            params.onError();
                        }
                    } catch (e) {
                        console.error('Error parsing event data:', e);
                    }
                }
            }
        }
    } catch (error: any) {
        if (error.name === 'AbortError') {
            console.log('Stream aborted by user');
        } else {
            console.error('Stream failed:', error);
            params.onError();
        }
    }

    return controller;
};
