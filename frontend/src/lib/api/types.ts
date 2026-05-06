export interface ApiResponse<T> {
  code: number;
  data: T;
  message?: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface AuthData {
  token: string;
  expires_in: number;
  user: User;
}

export interface FileItem {
  id: string;
  name: string;
  file_size: number;
  mime_type: string;
  page_count?: number;
  summary?: string;
  tags?: string[];
  status: "pending" | "parsing" | "ready" | "failed";
  created_at: string;
}

export interface Folder {
  id: string;
  name: string;
  parent_id: string | null;
  path: string;
  children?: Folder[];
  file_count?: number;
}

export interface Citation {
  index: number;
  chunk_id: string;
  file_id: string;
  file_name: string;
  page: number;
  locator?: {
    type: "excel";
    sheet: string;
    row_start: number;
    row_end: number;
    col_start: number;
    col_end: number;
  };
  text: string;
  highlight_positions?: {
    start: number;
    end: number;
  };
}

export interface Conversation {
  id: string;
  title: string;
  scope_type: "global" | "folder" | "file";
  created_at: string;
  message_count?: number;
  updated_at?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at: string;
}

export interface TaskProgress {
  task_id: string;
  task_type: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  message: string;
}
