import { apiFetch } from "./client";
import { API_BASE } from "./config";
import type { ApiResponse, FileItem, Folder, TaskProgress } from "./types";

type FolderTreeNode = {
  id: string;
  name: string;
  parent_id?: string | null;
  path?: string;
  children?: FolderTreeNode[];
  file_count?: number;
};

function flattenFolderTree(nodes: FolderTreeNode[], parentId: string | null = null, parentPath = ""): Folder[] {
  return nodes.flatMap((node) => {
    if (node.id === "root") {
      return flattenFolderTree(node.children || [], null, "");
    }

    const path = node.path || `${parentPath}/${node.name}`;
    const folder: Folder = {
      id: node.id,
      name: node.name,
      parent_id: node.parent_id ?? parentId,
      path,
      children: node.children as Folder[] | undefined,
      file_count: node.file_count,
    };

    return [folder, ...flattenFolderTree(node.children || [], node.id, path)];
  });
}

export async function getFiles(params?: {
  folder_id?: string | null;
  root_only?: boolean;
  page?: number;
  page_size?: number;
  status?: string;
  tag?: string;
}): Promise<{ total: number; items: FileItem[] }> {
  const search = new URLSearchParams();
  if (params?.root_only) search.set("folder_id", "root");
  else if (params?.folder_id) search.set("folder_id", params.folder_id);
  if (params?.page) search.set("page", String(params.page));
  if (params?.page_size) search.set("page_size", String(params.page_size));
  if (params?.status) search.set("status", params.status);
  if (params?.tag) search.set("tag", params.tag);
  const res = await apiFetch<ApiResponse<{ total: number; items: FileItem[] }>>(
    `/files?${search.toString()}`
  );
  return res.data;
}

export async function uploadFile(file: File, folderId?: string): Promise<{
  file_id: string;
  task_id: string;
  status: string;
  folder_id?: string | null;
}> {
  const formData = new FormData();
  formData.append("file", file);
  if (folderId) formData.append("folder_id", folderId);

  const token = typeof window !== "undefined" ? localStorage.getItem("aisb_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/files/upload`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `Upload failed: ${res.status}`);
  }
  const data: ApiResponse<{ file_id: string; task_id: string; status: string }> = await res.json();
  return data.data;
}

export async function initChunkUpload(payload: {
  file_name: string;
  file_size: number;
  mime_type: string;
  folder_id?: string;
}): Promise<{ upload_id: string; chunk_size: number; total_chunks: number }> {
  const res = await apiFetch<ApiResponse<{ upload_id: string; chunk_size: number; total_chunks: number }>>("/files/upload/init", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return res.data;
}

export async function uploadChunk(
  uploadId: string,
  chunkIndex: number,
  chunk: Blob
): Promise<{ chunk_index: number; uploaded: boolean }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("aisb_token") : null;
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/files/upload/${uploadId}/chunks/${chunkIndex}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/octet-stream",
      ...headers,
    },
    body: chunk,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message || `Chunk upload failed: ${res.status}`);
  }
  const data: ApiResponse<{ chunk_index: number; uploaded: boolean }> = await res.json();
  return data.data;
}

export async function completeChunkUpload(uploadId: string): Promise<{
  file_id: string;
  task_id: string;
  status: string;
  folder_id?: string | null;
}> {
  const res = await apiFetch<ApiResponse<{
    file_id: string;
    task_id: string;
    status: string;
    folder_id?: string | null;
  }>>(
    `/files/upload/${uploadId}/complete`,
    { method: "POST" }
  );
  return res.data;
}

export async function deleteFile(fileId: string): Promise<{ deleted: boolean; file_id: string }> {
  const res = await apiFetch<ApiResponse<{ deleted: boolean; file_id: string }>>(`/files/${fileId}`, {
    method: "DELETE",
  });
  return res.data;
}

export async function getFileChunks(fileId: string, params?: { page?: number; page_size?: number }): Promise<{
  file_id: string;
  total: number;
  items: Array<{
    id: string;
    chunk_index: number;
    content: string;
    page_number: number;
    start_pos: number;
    end_pos: number;
    locator?: unknown;
    token_count?: number | null;
    vector_id?: string | null;
    created_at: string;
  }>;
}> {
  const search = new URLSearchParams();
  if (params?.page) search.set("page", String(params.page));
  if (params?.page_size) search.set("page_size", String(params.page_size));
  const res = await apiFetch<ApiResponse<{
    file_id: string;
    total: number;
    items: Array<{
      id: string;
      chunk_index: number;
      content: string;
      page_number: number;
      start_pos: number;
      end_pos: number;
      locator?: unknown;
      token_count?: number | null;
      vector_id?: string | null;
      created_at: string;
    }>;
  }>>(`/files/${fileId}/chunks?${search.toString()}`);
  return res.data;
}

export async function getTaskProgress(taskId: string): Promise<TaskProgress> {
  const res = await apiFetch<ApiResponse<TaskProgress>>(`/tasks/${taskId}/progress`);
  return res.data;
}

export async function getFolderTree(): Promise<Folder[]> {
  const res = await apiFetch<ApiResponse<FolderTreeNode[]>>("/folders/tree");
  return flattenFolderTree(res.data);
}

export async function createFolder(payload: { name: string; parent_id?: string }): Promise<Folder> {
  const res = await apiFetch<ApiResponse<Folder>>("/folders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return res.data;
}

export async function deleteFolder(folderId: string): Promise<{ deleted: boolean; folder_id: string }> {
  const res = await apiFetch<ApiResponse<{ deleted: boolean; folder_id: string }>>(`/folders/${folderId}`, {
    method: "DELETE",
  });
  return res.data;
}
