import { create } from "zustand";
import type { FileItem, Folder } from "@/lib/api/types";

interface FilesState {
  files: FileItem[];
  folders: Folder[];
  selectedFolderId: string | null;
  isUploading: boolean;
  uploadProgress: Record<string, number>;
  setFiles: (files: FileItem[]) => void;
  setFolders: (folders: Folder[]) => void;
  addFile: (file: FileItem) => void;
  removeFile: (fileId: string) => void;
  updateFileStatus: (fileId: string, status: FileItem["status"]) => void;
  addFolder: (folder: Folder) => void;
  removeFolder: (folderId: string) => void;
  setSelectedFolderId: (id: string | null) => void;
  setIsUploading: (uploading: boolean) => void;
  setUploadProgress: (fileId: string, progress: number) => void;
}

export const useFilesStore = create<FilesState>((set) => ({
  files: [],
  folders: [],
  selectedFolderId: null,
  isUploading: false,
  uploadProgress: {},
  setFiles: (files) => set({ files }),
  setFolders: (folders) => set({ folders }),
  addFile: (file) => set((state) => ({ files: [file, ...state.files] })),
  removeFile: (fileId) =>
    set((state) => ({ files: state.files.filter((f) => f.id !== fileId) })),
  updateFileStatus: (fileId, status) =>
    set((state) => ({
      files: state.files.map((f) => (f.id === fileId ? { ...f, status } : f)),
    })),
  addFolder: (folder) =>
    set((state) => ({ folders: [...state.folders, folder] })),
  removeFolder: (folderId) =>
    set((state) => ({
      folders: state.folders.filter((f) => f.id !== folderId),
    })),
  setSelectedFolderId: (id) => set({ selectedFolderId: id }),
  setIsUploading: (isUploading) => set({ isUploading }),
  setUploadProgress: (fileId, progress) =>
    set((state) => ({
      uploadProgress: { ...state.uploadProgress, [fileId]: progress },
    })),
}));
