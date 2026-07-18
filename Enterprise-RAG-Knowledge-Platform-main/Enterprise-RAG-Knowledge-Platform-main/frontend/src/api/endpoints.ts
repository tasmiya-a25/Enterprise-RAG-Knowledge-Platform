import { api } from "./client";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: "admin" | "editor" | "user";
  is_active: boolean;
  is_verified: boolean;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "indexed" | "failed";
  error_message: string | null;
  created_at: string;
  indexed_at: string | null;
}

export interface Citation {
  document_id: string;
  document_name: string;
  chunk_id: string;
  page_number: number | null;
  score: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface ChatSummary {
  id: string;
  title: string;
  updated_at: string;
}

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    api.post<User>("/auth/register", { email, password, full_name }),
  login: (email: string, password: string) =>
    api.post<{ access_token: string; refresh_token: string }>("/auth/login", { email, password }),
  me: () => api.get<User>("/me"),
};

export const documentsApi = {
  list: () => api.get<{ documents: DocumentItem[]; total: number }>("/documents"),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<DocumentItem>("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  get: (id: string) => api.get<DocumentItem>(`/documents/${id}`),
  remove: (id: string) => api.delete(`/documents/${id}`),
};

export const chatApi = {
  ask: (message: string, chat_id?: string) =>
    api.post<{ chat_id: string; message: ChatMessage }>("/chat", { message, chat_id }),
  history: () => api.get<ChatSummary[]>("/chat/history"),
  getChat: (chatId: string) =>
    api.get<{ chat_id: string; title: string; messages: ChatMessage[] }>(`/chat/${chatId}`),
  remove: (chatId: string) => api.delete(`/chat/${chatId}`),
};
