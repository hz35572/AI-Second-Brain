# AI Second Brain 前端技术文档

> 位置：`/docs/fronted/FRONTEND_TECHNICAL_DOCUMENT.md`  
> 目标读者：参与本项目的 AI 智能体与人类工程师  
> 适用范围：Web 前端（Next.js），桌面端/移动端未来扩展不在本文件的 MVP 范围内

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术栈选型与版本](#2-技术栈选型与版本)
- [3. 目录结构说明](#3-目录结构说明)
- [4. 编码规范与最佳实践](#4-编码规范与最佳实践)
- [5. 组件设计规范](#5-组件设计规范)
- [6. 状态管理方案](#6-状态管理方案)
- [7. 路由配置说明](#7-路由配置说明)
- [8. API 接口文档（前端视角）](#8-api-接口文档前端视角)
- [9. 开发环境搭建步骤](#9-开发环境搭建步骤)
- [10. 构建与部署流程](#10-构建与部署流程)
- [11. 常见问题（FAQ）](#11-常见问题faq)
- [12. 扩展开发指南](#12-扩展开发指南)

---

## 1. 项目概述

AI Second Brain 是一个基于 RAG 的个人知识库问答系统。前端的核心体验来自 PRD：

- Chat-first 的对话式交互
- 三栏布局（左导航/中对话/右侧抽屉预览）
- SSE 流式输出（TTFB < 2s）
- 严格引用溯源：点击引用角标可跳转到原文对应位置并高亮
- 支持文件/文件夹范围问答（scope）
- 上传支持大文件分片与进度反馈

前端在 MVP 的职责边界：

1. 文件/文件夹的基础管理界面（列表、树、拖拽上传、状态展示）
2. 对话 UI（SSE 流式渲染、引用角标渲染、对话历史）
3. 溯源预览（右侧抽屉，PDF/Markdown 优先；Excel 预留）
4. 任务进度展示（轮询 tasks 或 WebSocket 推送）

---

## 2. 技术栈选型与版本

> 本仓库目前尚未初始化前端代码与 `package.json`；以下为 **MVP 约定的目标技术栈**，用于统一后续实现与协作口径。

运行时与框架：

- Node.js：`>= 20`（建议 LTS）
- React：`^18`
- Next.js：`^14`（App Router）
- TypeScript：`^5`

UI 与样式：

- Tailwind CSS：`^3`
- shadcn/ui（基于 Radix UI）：用于表单、弹窗、Popover、Tabs 等基础组件
- lucide-react：图标库

数据获取与状态：

- TanStack Query（React Query）：服务端数据缓存、重试、失效、乐观更新
- Zustand：轻量全局 UI 状态（侧边栏折叠、当前 scope、抽屉状态等）

渲染与体验组件：

- SSE：浏览器 `EventSource`（或 fetch + ReadableStream，按兼容性选型）
- PDF 预览：`react-pdf`（配合自定义高亮层）
- Markdown：`react-markdown` + `remark-gfm`
- 长列表：`react-virtuoso`（对话历史/文件列表）

测试与质量：

- ESLint + TypeScript ESLint
- Prettier
- Vitest（单元测试）+ Testing Library
- Playwright（E2E：引用点击打开抽屉并高亮、SSE 流式渲染）

---

## 3. 目录结构说明

目标目录（建议）：

```text
frontend/
  src/
    app/                      # Next.js App Router
      (shell)/                # 三栏布局 shell
        layout.tsx
        page.tsx              # 默认进入 chat
      chat/
        page.tsx
      files/
        page.tsx
      settings/
        page.tsx
    components/
      layout/                 # 三栏、抽屉、导航、工具条
      chat/                   # 消息气泡、输入框、引用角标、SSE 渲染
      files/                  # 文件列表、上传、状态、标签
      preview/                # PDF/MD/Excel 预览与高亮
      ui/                     # shadcn/ui 组件（生成或封装）
    lib/
      api/                    # API client（REST + SSE）
      auth/                   # token 管理、拦截器、鉴权守卫
      sse/                    # SSE 解析与缓冲策略
      utils/                  # 工具函数
    store/                    # Zustand stores
    styles/
      globals.css
  public/
  package.json
  next.config.js
  tsconfig.json
```

与后端/文档的对应关系：

- 后端 API 概览：`docs/API.md`
- 技术设计文档（TDD）：`docs/TECH_DESIGN.md`

---

## 4. 编码规范与最佳实践

### 4.1 语言与类型

- 强制 TypeScript：公共组件、API 请求、store、hooks 统一写 TS
- 禁止 `any`（必要时用 `unknown` + 运行时校验）
- API 响应必须建类型（`zod` 可选，用于运行时校验）

### 4.2 格式化与 lint

- Prettier 统一格式
- ESLint 作为提交前门禁

### 4.3 性能与渲染

- 长列表必须虚拟化（对话/文件列表）
- SSE 渲染需要节流/缓冲，避免每个 token 触发一次 React render

示例：用 RAF 将 token buffer 批量刷新到 UI：

```ts
// lib/sse/useStreamingText.ts
import { useEffect, useRef, useState } from "react";

export function useStreamingText() {
  const [text, setText] = useState("");
  const bufferRef = useRef("");

  useEffect(() => {
    let raf = 0;
    const loop = () => {
      setText(bufferRef.current);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);

  return {
    text,
    append: (chunk: string) => {
      bufferRef.current += chunk;
    },
    reset: () => {
      bufferRef.current = "";
      setText("");
    },
  };
}
```

---

## 5. 组件设计规范

### 5.1 三栏布局（Shell）

布局约定（PRD）：

- 左：新建对话/知识库/对话列表入口
- 中：主对话区（消息流 + 输入框）
- 右：预览抽屉（点击 citation 打开，并定位高亮）

建议组件：

```text
components/layout/
  AppShell.tsx
  LeftNav.tsx
  RightDrawer.tsx
  TopBar.tsx
```

### 5.2 Chat 组件

组件边界建议：

- `ChatComposer`：输入框（支持 Enter 发送、Shift+Enter 换行、禁用态）
- `MessageList`：虚拟列表
- `AssistantMessage`：流式渲染 + 引用角标渲染
- `CitationBadge`：可点击，触发右侧抽屉定位

### 5.3 预览器与高亮

统一预览接口（建议）：

```ts
export type PreviewTarget =
  | { kind: "pdf"; fileId: string; page: number; start: number; end: number }
  | { kind: "markdown"; fileId: string; anchorText?: string }
  | { kind: "excel"; fileId: string; sheet: string; rowStart: number; rowEnd: number; colStart: number; colEnd: number };

export interface DocumentPreviewer {
  open(target: PreviewTarget): void;
}
```

---

## 6. 状态管理方案

### 6.1 React Query（服务端状态）

使用场景：

- 文件列表、文件夹树、对话列表、对话历史
- 任务进度（轮询）

约定：

- QueryKey 结构化：`["files", { folderId, status, tag, page }]`
- 任何改变 scope 的行为都要 `invalidateQueries` 对应的 key

### 6.2 Zustand（客户端 UI 状态）

使用场景：

- 当前选中的 scope（global/folder/file + ids）
- 右侧抽屉开关与当前预览目标
- 左侧导航折叠、主题等

示例：

```ts
import { create } from "zustand";

type Scope =
  | { type: "global" }
  | { type: "folder"; ids: string[] }
  | { type: "file"; ids: string[] };

type UIState = {
  scope: Scope;
  setScope: (scope: Scope) => void;
  drawerOpen: boolean;
  openDrawer: () => void;
  closeDrawer: () => void;
};

export const useUIStore = create<UIState>((set) => ({
  scope: { type: "global" },
  setScope: (scope) => set({ scope }),
  drawerOpen: false,
  openDrawer: () => set({ drawerOpen: true }),
  closeDrawer: () => set({ drawerOpen: false }),
}));
```

---

## 7. 路由配置说明

使用 Next.js App Router：

- `/chat`：对话主页面（默认入口）
- `/files`：文件管理
- `/settings`：模型/密钥/本地部署配置（按产品规划逐步开放）

建议在 `(shell)` layout 中实现三栏布局，子页面仅负责中栏主内容。

---

## 8. API 接口文档（前端视角）

后端 API 总览见：`docs/API.md`。本节强调前端调用方式与关键协议（尤其 SSE）。

### 8.1 API Client 约定

- REST：`fetch` 或 `axios` 均可，需统一封装 baseURL、错误处理、鉴权 header
- SSE：优先 `EventSource`（简单可靠），本地/云端注意代理缓冲（需要 `X-Accel-Buffering: no`）

建议封装：

```ts
// lib/api/client.ts
export function getAuthToken(): string | null {
  return localStorage.getItem("aisb_token");
}
```

### 8.2 SSE（流式问答）协议

接口：`POST /api/v1/chat/conversations/{conversation_id}/messages`

事件类型：

- `chunk`：增量文本片段 `{ type: "chunk", content: string }`
- `citation`：引用数组 `{ type: "citation", citations: Citation[] }`
- `done`：完成 `{ type: "done", metadata: { token_usage?: number; latency_ms?: number } }`

前端处理建议：

1. `chunk`：追加到 buffer（不要每 token 立即 setState）
2. `citation`：解析并缓存，用于渲染角标与点击跳转
3. `done`：落盘（写入对话历史 cache），停止 loading

### 8.3 引用角标点击行为

点击 citation 后：

1. 打开右侧抽屉
2. 请求文件内容/可预览资源（PDF/MD）
3. 定位到 `page + start/end`（PDF）或 `locator`（Excel）
4. 高亮对应范围

---

## 9. 开发环境搭建步骤

### 9.1 启动后端依赖（数据库/缓存/向量库/对象存储）

在项目根目录：

```powershell
docker compose up -d
```

### 9.2 启动后端 API（占位骨架）

后端在 `backend/`（目前为 skeleton）：

```powershell
cd backend
python -m pip install -e .
python -m uvicorn app.main:app --reload --port 8000
```

### 9.3 初始化并启动前端（待实现）

前端尚未生成 `package.json`，建议后续初始化：

```powershell
cd frontend
npx create-next-app@latest ...
npm run dev
```

---

## 10. 构建与部署流程

### 10.1 本地构建

```bash
npm run build
npm run start
```

### 10.2 部署（建议）

- SaaS：Next.js 部署到 Vercel 或容器化部署（nginx 反代到后端）
- 本地版：与后端一起打包（Tauri/Electron 属于后续阶段）

关键注意点：

- SSE 需要禁用代理缓冲（nginx `X-Accel-Buffering: no`）
- 跨域：本地 dev 通过 Next.js rewrites 或后端 CORS

---

## 11. 常见问题（FAQ）

### 11.1 SSE 没有流式效果、变成“一次性返回”

常见原因：

- 反向代理/网关启用了缓冲（nginx 默认缓冲）
- 服务端没有设置 `text/event-stream` 或缺少 `\n\n` 分隔

排查建议：

- 确认响应头包含：`Content-Type: text/event-stream`、`Cache-Control: no-cache`、`X-Accel-Buffering: no`

### 11.2 引用点击无法定位/高亮不准

常见原因：

- start/end 是按解析后的文本位置，而 PDF 渲染层坐标不同步
- 文本抽取策略变化导致定位偏移

建议：

- MVP 先保证“页码准确 + 该页内高亮近似可见”
- 对 Word/Excel 采用 `locator` 或“片段文本匹配”作为降级定位策略

---

## 12. 扩展开发指南

### 12.1 Excel 预览器接入

后端 citation 中会提供：

- `locator.type = "excel"`
- sheet/行列范围

前端扩展路径：

1. 新增 `components/preview/ExcelPreview.tsx`
2. 实现 `open(target)`：定位 sheet + 选区高亮
3. 与 `RightDrawer` 统一接口联动

### 12.2 范围问答（scope）UI

scope 选择器建议放在 chat 顶部工具条：

- global（默认）
- folder（多选文件夹）
- file（多选文件）

scope 的变更必须同步到：

1. 创建对话接口 `/chat/conversations`
2. 发送消息时（后端若需要也可再次携带 scope）

### 12.3 本地化版本（Local）

本地化版本的前端重点：

- baseURL 指向本地后端
- 禁用任何外部网络请求（包括字体、CDN）
- 明确标识“离线模式”
