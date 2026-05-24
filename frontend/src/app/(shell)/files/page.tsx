"use client";

import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useFilesStore } from "@/store/files";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";
import {
  getFiles,
  getFolderTree,
  uploadFile,
  initChunkUpload,
  uploadChunk,
  completeChunkUpload,
  deleteFile,
  createFolder,
  deleteFolder,
  getTaskProgress,
} from "@/lib/api/files";
import {
  FolderOpen,
  FileText,
  Upload,
  Trash2,
  Plus,
  Grid,
  List,
  Loader2,
  AlertCircle,
  X,
  FileSpreadsheet,
  Image as ImageIcon,
  MoreHorizontal,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { FileItem, Folder } from "@/lib/api/types";

const CHUNK_SIZE = 5 * 1024 * 1024;

function getFileIcon(mimeType: string) {
  if (mimeType.includes("spreadsheet") || mimeType.includes("excel") || mimeType.endsWith(".xlsx") || mimeType.endsWith(".csv")) {
    return <FileSpreadsheet className="h-5 w-5 text-[#10B981]" />;
  }
  if (mimeType.includes("image")) {
    return <ImageIcon className="h-5 w-5 text-[#F59E0B]" />;
  }
  return <FileText className="h-5 w-5 text-[#6B7280]" />;
}

function formatFileSize(bytes: number) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function EmptyFolderIllustration() {
  return (
    <div className="relative mx-auto h-36 w-44">
      <div className="absolute left-5 top-10 h-20 w-32 rotate-[8deg] rounded-[22px] bg-[#EEF1FF] shadow-[0_22px_48px_rgba(79,70,229,0.16)]" />
      <div className="absolute left-11 top-6 h-16 w-22 rotate-[19deg] rounded-2xl bg-[#DDE2FF]" />
      <div className="absolute left-2 top-18 h-16 w-36 -rotate-[7deg] rounded-[20px] bg-gradient-to-br from-white to-[#DDE3FF] shadow-[0_18px_44px_rgba(79,70,229,0.14)]" />
      <div className="absolute left-3 top-15 h-7 w-18 rounded-t-2xl bg-[#F5F6FF]" />
      <div className="absolute right-7 top-7 h-2 w-2 rounded-full bg-[#5B50F1]" />
      <div className="absolute left-7 top-6 h-1.5 w-1.5 rounded-full bg-[#A6AAFF]" />
      <div className="absolute right-4 bottom-8 h-2 w-2 rounded-full bg-[#5B50F1]" />
    </div>
  );
}

export default function FilesPage() {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const {
    files,
    folders,
    selectedFolderId,
    isUploading,
    uploadProgress,
    setFiles,
    setFolders,
    addFile,
    removeFile,
    updateFileStatus,
    addFolder,
    removeFolder,
    setSelectedFolderId,
    setIsUploading,
    setUploadProgress,
  } = useFilesStore();

  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [newFolderOpen, setNewFolderOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: "file" | "folder"; id: string; name: string } | null>(null);

  const { data: filesData } = useQuery({
    queryKey: ["files", selectedFolderId],
    queryFn: async () => {
      const data = await getFiles({
        folder_id: selectedFolderId,
        root_only: selectedFolderId === null,
        page: 1,
        page_size: 100,
      });
      setFiles(data.items);
      return data;
    },
    enabled: isAuthenticated,
    staleTime: 30 * 1000,
  });

  const { data: foldersData } = useQuery({
    queryKey: ["folders"],
    queryFn: async () => {
      const data = await getFolderTree();
      setFolders(data);
      return data;
    },
    enabled: isAuthenticated,
    staleTime: 30 * 1000,
  });

  useEffect(() => {
    if (!foldersData) return;
    queueMicrotask(() => setFolders(foldersData));
  }, [foldersData, setFolders]);

  const pollTaskProgress = useCallback(
    (taskId: string, fileId: string) => {
      const interval = setInterval(async () => {
        try {
          const progress = await getTaskProgress(taskId);
          setUploadProgress(fileId, progress.progress || 50 + (progress.progress || 0) / 2);
          if (progress.status === "completed") {
            updateFileStatus(fileId, "ready");
            clearInterval(interval);
            queryClient.invalidateQueries({ queryKey: ["files", selectedFolderId] });
          } else if (progress.status === "failed") {
            updateFileStatus(fileId, "failed");
            clearInterval(interval);
          }
        } catch {
          clearInterval(interval);
        }
      }, 2000);
    },
    [selectedFolderId, setUploadProgress, updateFileStatus, queryClient]
  );

  const uploadSingleFile = useCallback(
    async (file: File) => {
      if (file.size > CHUNK_SIZE) {
        const initRes = await initChunkUpload({
          file_name: file.name,
          file_size: file.size,
          mime_type: file.type || "application/octet-stream",
          folder_id: selectedFolderId || undefined,
        });

        const totalChunks = Math.ceil(file.size / initRes.chunk_size);
        for (let i = 0; i < totalChunks; i++) {
          const start = i * initRes.chunk_size;
          const end = Math.min(start + initRes.chunk_size, file.size);
          const chunk = file.slice(start, end);
          await uploadChunk(initRes.upload_id, i, chunk);
          setUploadProgress(
            `upload-${file.name}`,
            Math.round(((i + 1) / totalChunks) * 50)
          );
        }

        const completeRes = await completeChunkUpload(initRes.upload_id);
        const tempFile: FileItem = {
          id: completeRes.file_id,
          name: file.name,
          file_size: file.size,
          mime_type: file.type || "application/octet-stream",
          folder_id: completeRes.folder_id ?? selectedFolderId ?? null,
          status: "parsing",
          created_at: new Date().toISOString(),
        };
        addFile(tempFile);
        pollTaskProgress(completeRes.task_id, completeRes.file_id);
      } else {
        const res = await uploadFile(file, selectedFolderId || undefined);
        const tempFile: FileItem = {
          id: res.file_id,
          name: file.name,
          file_size: file.size,
          mime_type: file.type || "application/octet-stream",
          folder_id: res.folder_id ?? selectedFolderId ?? null,
          status: "parsing",
          created_at: new Date().toISOString(),
        };
        addFile(tempFile);
        pollTaskProgress(res.task_id, res.file_id);
      }
    },
    [selectedFolderId, addFile, pollTaskProgress, setUploadProgress]
  );

  const handleUploadFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const filesToUpload = Array.from(fileList).filter((file) => file.size > 0);
      if (filesToUpload.length === 0) return;

      setUploadErrors([]);
      setIsUploading(true);
      let hasError = false;

      for (const file of filesToUpload) {
        try {
          await uploadSingleFile(file);
        } catch (err) {
          hasError = true;
          setUploadErrors((prev) => [
            ...prev,
            `${file.name}: ${err instanceof Error ? err.message : "上传失败"}`,
          ]);
        }
      }

      queryClient.invalidateQueries({ queryKey: ["files", selectedFolderId] });
      queryClient.invalidateQueries({ queryKey: ["folders"] });
      setIsUploading(false);
      if (!hasError) setUploadOpen(false);
    },
    [selectedFolderId, queryClient, setIsUploading, uploadSingleFile]
  );

  const handleCreateFolder = useCallback(async () => {
    if (!newFolderName.trim()) return;
    try {
      const folder = await createFolder({
        name: newFolderName.trim(),
        parent_id: selectedFolderId || undefined,
      });
      addFolder(folder);
      setNewFolderName("");
      setNewFolderOpen(false);
      queryClient.invalidateQueries({ queryKey: ["folders"] });
    } catch (err) {
      setUploadErrors((prev) => [
        ...prev,
        `创建文件夹失败: ${err instanceof Error ? err.message : "未知错误"}`,
      ]);
    }
  }, [newFolderName, selectedFolderId, addFolder, queryClient]);

  const handleDeleteFile = useCallback(
    async (fileId: string) => {
      try {
        await deleteFile(fileId);
        removeFile(fileId);
        queryClient.invalidateQueries({ queryKey: ["files", selectedFolderId] });
      } catch (err) {
        setUploadErrors((prev) => [
          ...prev,
          `删除失败: ${err instanceof Error ? err.message : "未知错误"}`,
        ]);
      }
    },
    [removeFile, selectedFolderId, queryClient]
  );

  const handleDeleteFolder = useCallback(
    async (folderId: string) => {
      try {
        await deleteFolder(folderId);
        removeFolder(folderId);
        if (selectedFolderId === folderId) setSelectedFolderId(null);
        queryClient.invalidateQueries({ queryKey: ["folders"] });
        queryClient.invalidateQueries({ queryKey: ["files", selectedFolderId] });
      } catch (err) {
        setUploadErrors((prev) => [
          ...prev,
          `删除文件夹失败: ${err instanceof Error ? err.message : "未知错误"}`,
        ]);
      }
    },
    [removeFolder, selectedFolderId, setSelectedFolderId, queryClient]
  );

  const visibleFiles = filesData?.items ?? files;
  const filteredFiles = selectedFolderId
    ? visibleFiles.filter((f) => f.folder_id === selectedFolderId)
    : visibleFiles.filter((f) => !f.folder_id);

  const visibleFolders = foldersData ?? folders;
  const currentFolder = visibleFolders.find((f) => f.id === selectedFolderId);
  const childFolders: Folder[] = visibleFolders
    .filter((f) => (selectedFolderId ? f.parent_id === selectedFolderId : f.parent_id === null))
    .sort((a, b) => a.name.localeCompare(b.name));
  const isKnowledgeBaseEmpty = childFolders.length === 0 && filteredFiles.length === 0;

  // If current folder disappears (deleted elsewhere), fall back to root.
  useEffect(() => {
    if (selectedFolderId && !currentFolder) setSelectedFolderId(null);
  }, [selectedFolderId, currentFolder, setSelectedFolderId]);

  return (
    <div className="flex h-full flex-col bg-[#FBFCFF] px-9 py-8">
      <div className="mb-8 flex items-start justify-between gap-6">
        <div>
          <h1 className="text-[28px] font-bold leading-tight text-[#07143B]">知识库</h1>
          <p className="mt-2 text-base text-[#6B7280]">
            管理和维护您的知识库文件，支持多种格式文档
          </p>
        </div>

        <div className="flex items-center gap-7">
          <div className="flex items-center rounded-xl border border-[#DDE3F0] bg-white p-1 shadow-[0_10px_28px_rgba(30,41,59,0.05)]">
          <Button
            variant="ghost"
            size="icon"
            className={cn(
                "h-11 w-12 rounded-lg text-[#25324D]",
                viewMode === "grid" && "bg-[#F0EEFF] text-[#4F46E5] shadow-[0_8px_18px_rgba(79,70,229,0.10)]"
            )}
            onClick={() => setViewMode("grid")}
              aria-label="网格视图"
          >
              <Grid className="h-5 w-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={cn(
                "h-11 w-12 rounded-lg text-[#25324D]",
                viewMode === "list" && "bg-[#F0EEFF] text-[#4F46E5] shadow-[0_8px_18px_rgba(79,70,229,0.10)]"
            )}
            onClick={() => setViewMode("list")}
              aria-label="列表视图"
          >
              <List className="h-5 w-5" />
          </Button>
          </div>

          <Dialog open={newFolderOpen} onOpenChange={setNewFolderOpen}>
            <DialogTrigger
              render={<Button variant="outline" className="h-12 rounded-xl border-[#DDE3F0] bg-white px-7 text-base text-[#111827] shadow-[0_10px_28px_rgba(30,41,59,0.04)] hover:bg-[#F8FAFF]" />}
            >
              <Plus className="h-5 w-5" />
              新建文件夹
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>新建文件夹</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-2">
                <input
                  type="text"
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  placeholder="文件夹名称"
                  className="w-full px-3 py-2 border border-[#E5E7EB] rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-[#4F46E5] focus:border-transparent"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCreateFolder();
                  }}
                />
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setNewFolderOpen(false)}
                  >
                    取消
                  </Button>
                  <Button
                    size="sm"
                    className="bg-[#4F46E5] hover:bg-[#4338CA] text-white"
                    onClick={handleCreateFolder}
                    disabled={!newFolderName.trim()}
                  >
                    创建
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>

          <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
            <DialogTrigger
              render={
                <Button
                  className="h-12 rounded-xl bg-[#4F46E5] px-8 text-base text-white shadow-[0_14px_32px_rgba(79,70,229,0.30)] hover:bg-[#4338CA]"
                />
              }
            >
              <Upload className="h-5 w-5" />
              上传文件
            </DialogTrigger>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>上传文件</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 mt-2">
                <label
                  className={cn(
                    "flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors",
                    isDragActive
                      ? "border-[#4F46E5] bg-[#EEF2FF]"
                      : "border-[#E5E7EB] hover:border-[#4F46E5] hover:bg-[#EEF2FF]",
                    isUploading && "cursor-wait opacity-75"
                  )}
                  onDragEnter={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsDragActive(true);
                  }}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    e.dataTransfer.dropEffect = "copy";
                    setIsDragActive(true);
                  }}
                  onDragLeave={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
                      setIsDragActive(false);
                    }
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setIsDragActive(false);
                    if (isUploading) return;
                    handleUploadFiles(e.dataTransfer.files);
                  }}
                >
                  <Upload
                    className={cn(
                      "h-8 w-8 mb-2",
                      isDragActive ? "text-[#4F46E5]" : "text-[#6B7280]"
                    )}
                  />
                  <span className="text-sm text-[#6B7280]">
                    {isDragActive ? "松开即可上传" : "点击或拖拽文件到此处"}
                  </span>
                  <span className="text-xs text-[#9CA3AF] mt-1">
                    支持 TXT, PDF, Word, Excel 等格式
                  </span>
                  <input
                    type="file"
                    multiple
                    className="hidden"
                    disabled={isUploading}
                    onChange={(e) => {
                      const selectedFiles = e.target.files;
                      if (selectedFiles?.length) handleUploadFiles(selectedFiles);
                      e.currentTarget.value = "";
                    }}
                  />
                </label>

                {isUploading && (
                  <div className="flex items-center gap-2 text-sm text-[#6B7280]">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    正在上传...
                  </div>
                )}

                {uploadErrors.length > 0 && (
                  <div className="space-y-2">
                    {uploadErrors.map((err, i) => (
                      <Alert key={i} variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{err}</AlertDescription>
                      </Alert>
                    ))}
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {uploadErrors.length > 0 && (
        <div className="mb-4 space-y-2">
          {uploadErrors.map((err, i) => (
            <Alert key={i} variant="destructive" className="relative">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{err}</AlertDescription>
              <button
                onClick={() =>
                  setUploadErrors((prev) => prev.filter((_, idx) => idx !== i))
                }
                className="absolute top-2 right-2"
              >
                <X className="h-3 w-3" />
              </button>
            </Alert>
          ))}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-[#DDE3F0] bg-white shadow-[0_18px_60px_rgba(30,41,59,0.04)]">
        <ScrollArea className="h-full">
          <div className="min-h-[calc(100vh-220px)] p-10">
            {currentFolder && (
              <button
                onClick={() => setSelectedFolderId(null)}
                className="mb-6 rounded-lg px-3 py-2 text-sm font-medium text-[#4F46E5] hover:bg-[#EEF2FF]"
              >
                全部文件 / {currentFolder.name}
              </button>
            )}
            {viewMode === "grid" ? (
              <div className="relative min-h-[620px]">
                <div className="grid grid-cols-1 gap-7 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {childFolders.map((folder) => (
                  <div
                    key={folder.id}
                      className="group relative h-[230px] cursor-pointer rounded-2xl border border-[#DDE3F0] bg-white p-7 shadow-[0_18px_42px_rgba(30,41,59,0.08)] transition-all hover:-translate-y-0.5 hover:border-[#C9D2EA] hover:shadow-[0_22px_52px_rgba(79,70,229,0.12)]"
                    onClick={() => setSelectedFolderId(folder.id)}
                  >
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeleteConfirm({
                            type: "folder",
                            id: folder.id,
                            name: folder.name,
                          });
                        }}
                        className="absolute right-5 top-5 rounded-lg p-1.5 text-[#7A86A1] opacity-100 hover:bg-[#FEF2F2] hover:text-[#EF4444]"
                        aria-label="文件夹操作"
                      >
                        <MoreHorizontal className="h-5 w-5" />
                      </button>
                      <div className="flex h-full flex-col items-center justify-center text-center">
                        <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#F0EEFF]">
                          <FolderOpen className="h-9 w-9 text-[#4F46E5]" />
                      </div>
                        <span className="w-full truncate text-lg font-semibold text-[#111827]">
                        {folder.name}
                      </span>
                        <span className="mt-2 text-sm text-[#6B7280]">
                        文件夹
                      </span>
                        <div className="mt-auto flex w-full items-center justify-between text-sm text-[#6B7280]">
                          <span className="flex items-center gap-1">
                            <FolderOpen className="h-4 w-4" />
                            {folder.file_count ?? 0} 个文件
                          </span>
                          <span>刚刚</span>
                        </div>
                    </div>
                  </div>
                ))}
                {filteredFiles.map((file) => (
                  <div
                    key={file.id}
                    className="group relative p-3 rounded-lg border border-[#E5E7EB] hover:border-[#4F46E5] hover:shadow-sm transition-all bg-white"
                  >
                    <div className="flex flex-col items-center text-center">
                      <div className="h-12 w-12 rounded-lg bg-[#F9FAFB] flex items-center justify-center mb-2">
                        {getFileIcon(file.mime_type)}
                      </div>
                      <span className="text-xs text-[#111827] truncate w-full">
                        {file.name}
                      </span>
                      <span className="text-[10px] text-[#6B7280] mt-0.5">
                        {formatFileSize(file.file_size)}
                      </span>
                      {file.status === "parsing" && (
                        <div className="mt-2 flex items-center gap-1 text-[10px] text-[#F59E0B]">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          处理中
                        </div>
                      )}
                      {file.status === "failed" && (
                        <span className="mt-2 text-[10px] text-[#EF4444]">
                          处理失败
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() =>
                        setDeleteConfirm({
                          type: "file",
                          id: file.id,
                          name: file.name,
                        })
                      }
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[#FEF2F2] transition-opacity"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-[#EF4444]" />
                    </button>
                  </div>
                ))}
                </div>
                {isKnowledgeBaseEmpty && (
                  <div className="pointer-events-none absolute inset-x-0 top-1/2 mx-auto flex -translate-y-1/2 flex-col items-center text-center text-[#6B7280]">
                    <EmptyFolderIllustration />
                    <h2 className="mt-6 text-2xl font-bold text-[#07143B]">知识库为空</h2>
                    <p className="mt-4 text-base text-[#6B7280]">
                      上传文件或创建文件夹，开始构建您的知识库
                    </p>
                    <div className="pointer-events-auto mt-7 flex items-center gap-5">
                      <Button className="h-12 rounded-xl bg-[#4F46E5] px-8 text-base text-white shadow-[0_14px_32px_rgba(79,70,229,0.30)] hover:bg-[#4338CA]" onClick={() => setUploadOpen(true)}>
                        <Upload className="h-5 w-5" />
                        上传文件
                      </Button>
                      <Button
                        variant="outline"
                        className="h-12 rounded-xl border-[#DDE3F0] bg-white px-8 text-base text-[#111827] shadow-[0_10px_28px_rgba(30,41,59,0.04)] hover:bg-[#F8FAFF]"
                        onClick={() => setNewFolderOpen(true)}
                      >
                        <FolderOpen className="h-5 w-5" />
                        新建文件夹
                      </Button>
                    </div>
                    <div className="mt-18 flex items-center gap-2 text-sm text-[#7A86A1]">
                      <Lock className="h-4 w-4" />
                      支持多种格式：PDF、DOCX、TXT、MD 等
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {childFolders.map((folder) => (
                  <div
                    key={folder.id}
                    onClick={() => setSelectedFolderId(folder.id)}
                    className="group flex items-center gap-3 px-3 py-2.5 rounded-md hover:bg-[#F9FAFB] transition-colors cursor-pointer"
                  >
                    <FolderOpen className="h-5 w-5 text-[#4F46E5]" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[#111827] truncate">
                        {folder.name}
                      </p>
                      <p className="text-xs text-[#6B7280]">文件夹</p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm({
                          type: "folder",
                          id: folder.id,
                          name: folder.name,
                        });
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-[#FEF2F2] transition-opacity"
                    >
                      <Trash2 className="h-4 w-4 text-[#EF4444]" />
                    </button>
                  </div>
                ))}
                {filteredFiles.map((file) => (
                  <div
                    key={file.id}
                    className="group flex items-center gap-3 px-3 py-2.5 rounded-md hover:bg-[#F9FAFB] transition-colors"
                  >
                    {getFileIcon(file.mime_type)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-[#111827] truncate">{file.name}</p>
                      <p className="text-xs text-[#6B7280]">
                        {formatFileSize(file.file_size)}
                        {file.status === "parsing" && (
                          <span className="ml-2 text-[#F59E0B]">处理中</span>
                        )}
                        {file.status === "failed" && (
                          <span className="ml-2 text-[#EF4444]">处理失败</span>
                        )}
                      </p>
                    </div>
                    {uploadProgress[file.id] !== undefined && (
                      <div className="w-20 h-1.5 bg-[#E5E7EB] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#4F46E5] rounded-full transition-all"
                          style={{ width: `${uploadProgress[file.id]}%` }}
                        />
                      </div>
                    )}
                    <button
                      onClick={() =>
                        setDeleteConfirm({
                          type: "file",
                          id: file.id,
                          name: file.name,
                        })
                      }
                      className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-[#FEF2F2] transition-opacity"
                    >
                      <Trash2 className="h-4 w-4 text-[#EF4444]" />
                    </button>
                  </div>
                ))}
                {childFolders.length === 0 && filteredFiles.length === 0 && (
                  <div className="py-24 text-center text-[#6B7280]">
                    <EmptyFolderIllustration />
                    <p className="mt-4 text-sm">暂无内容</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      <Dialog
        open={!!deleteConfirm}
        onOpenChange={() => setDeleteConfirm(null)}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              确认删除{deleteConfirm?.type === "folder" ? "文件夹" : "文件"}?
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-[#6B7280] mt-2">
            确定要删除 &quot;{deleteConfirm?.name}&quot; 吗？此操作不可撤销。
          </p>
          <div className="flex justify-end gap-2 mt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDeleteConfirm(null)}
            >
              取消
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => {
                if (deleteConfirm?.type === "file") {
                  handleDeleteFile(deleteConfirm.id);
                } else if (deleteConfirm?.type === "folder") {
                  handleDeleteFolder(deleteConfirm.id);
                }
                setDeleteConfirm(null);
              }}
            >
              删除
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
