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
  ChevronRight,
  Loader2,
  AlertCircle,
  X,
  FileSpreadsheet,
  Image as ImageIcon,
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
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
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

  const [viewMode, setViewMode] = useState<"grid" | "list">("list");
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

  // If current folder disappears (deleted elsewhere), fall back to root.
  useEffect(() => {
    if (selectedFolderId && !currentFolder) setSelectedFolderId(null);
  }, [selectedFolderId, currentFolder, setSelectedFolderId]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#E5E7EB] bg-white">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-[#111827]">知识库</h2>
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink
                  onClick={() => setSelectedFolderId(null)}
                  className="cursor-pointer"
                >
                  全部文件
                </BreadcrumbLink>
              </BreadcrumbItem>
              {currentFolder && (
                <>
                  <BreadcrumbSeparator>
                    <ChevronRight className="h-3 w-3" />
                  </BreadcrumbSeparator>
                  <BreadcrumbItem>
                    <span className="text-[#111827]">{currentFolder.name}</span>
                  </BreadcrumbItem>
                </>
              )}
            </BreadcrumbList>
          </Breadcrumb>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              "h-8 w-8",
              viewMode === "grid" && "bg-[#EEF2FF] text-[#4F46E5]"
            )}
            onClick={() => setViewMode("grid")}
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              "h-8 w-8",
              viewMode === "list" && "bg-[#EEF2FF] text-[#4F46E5]"
            )}
            onClick={() => setViewMode("list")}
          >
            <List className="h-4 w-4" />
          </Button>

          <Dialog open={newFolderOpen} onOpenChange={setNewFolderOpen}>
            <DialogTrigger
              render={<Button variant="outline" size="sm" className="gap-1" />}
            >
              <Plus className="h-3.5 w-3.5" />
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
                  size="sm"
                  className="bg-[#4F46E5] hover:bg-[#4338CA] text-white gap-1"
                />
              }
            >
              <Upload className="h-3.5 w-3.5" />
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
        <div className="px-4 pt-3 space-y-2">
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

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full p-4">
            {viewMode === "grid" ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {childFolders.map((folder) => (
                  <div
                    key={folder.id}
                    className="group relative p-3 rounded-lg border border-[#E5E7EB] hover:border-[#4F46E5] hover:shadow-sm transition-all bg-white cursor-pointer"
                    onClick={() => setSelectedFolderId(folder.id)}
                  >
                    <div className="flex flex-col items-center text-center">
                      <div className="h-12 w-12 rounded-lg bg-[#EEF2FF] flex items-center justify-center mb-2">
                        <FolderOpen className="h-5 w-5 text-[#4F46E5]" />
                      </div>
                      <span className="text-xs text-[#111827] truncate w-full">
                        {folder.name}
                      </span>
                      <span className="text-[10px] text-[#6B7280] mt-0.5">
                        文件夹
                      </span>
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
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-[#FEF2F2] transition-opacity"
                    >
                      <Trash2 className="h-3.5 w-3.5 text-[#EF4444]" />
                    </button>
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
                {childFolders.length === 0 && filteredFiles.length === 0 && (
                  <div className="col-span-full text-center py-12 text-[#6B7280]">
                    <FolderOpen className="h-12 w-12 mx-auto mb-3 text-[#E5E7EB]" />
                    <p className="text-sm">暂无内容</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-1">
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
                  <div className="text-center py-12 text-[#6B7280]">
                    <FolderOpen className="h-12 w-12 mx-auto mb-3 text-[#E5E7EB]" />
                    <p className="text-sm">暂无内容</p>
                  </div>
                )}
              </div>
            )}
          </ScrollArea>
        </div>
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
