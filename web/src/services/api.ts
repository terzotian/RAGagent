import axios from 'axios';

const API_BASE_URL = '/api/v1';

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
  }
};

export const streamAnswer = (params: {
  session_id: string;
  question_id: string;
  previous_questions: string[];
  current_question: string;
  language: string;
  base: string;
  onToken: (token: string) => void;
  onReferences: (refs: Reference[]) => void;
  onDone: () => void;
  onError: () => void;
}) => {
  const url = `${API_BASE_URL}/questions/stream?session_id=${params.session_id}&question_id=${params.question_id}&previous_questions=${encodeURIComponent(JSON.stringify(params.previous_questions))}&current_question=${encodeURIComponent(params.current_question)}&language=${params.language}&base=${params.base}`;
  
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    if (event.data === '[DONE]') {
      eventSource.close();
      params.onDone();
      return;
    }

    try {
      const data = JSON.parse(event.data);
      if (data.token) {
        params.onToken(data.token);
      } else if (data.references) {
        params.onReferences(data.references);
      }
    } catch (e) {
      console.error('Error parsing event data:', e);
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    params.onError();
  };

  return () => {
    eventSource.close();
  };
};
