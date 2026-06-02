# RAG 最佳方案设计

本文档定义 AI Second Brain 的高精度 RAG 方案。方案必须与 `docs/PRD.md`、`docs/TECH_DESIGN.md`、`docs/API.md` 和 `docs/database.md` 保持一致，优先服务 MVP 的核心目标：检索准确、回答低幻觉、引用可溯源、SSE 首包快。

## 1. 目标与硬约束

### 1.1 目标

- 提升中文知识库问答的检索精度，优先解决“问得自然但召回不到”“召回到相似但非答案段落”“引用不稳定”的问题。
- 支持 `global`、`folder`、`file` 三种 scope，并始终保证用户隔离。
- 在生成阶段严格基于检索上下文回答，不允许编造文件名、页码、定位信息或上下文中不存在的结论。
- 建立可重复的离线评测闭环，用 `backend/tests/test_files` 下的测试文件量化召回、重排、引用质量与性能。

### 1.2 硬约束

- 每个事实句或要点必须包含引用标记，例如 `[1]`。
- 引用编号只能来自最终上下文块编号。
- 点击引用必须能够通过 `file_id`、`chunk_id`、`page`、`locator`、`highlight_positions` 定位或近似高亮原文。
- SSE 协议保持 `chunk* -> citation? -> done`，不改变现有前后端协议。
- Chat 首条 SSE `chunk` TTFB 目标 `< 2s`。
- Retrieval latency 目标 p95 `< 800ms`。
- 找不到足够证据时必须返回：`知识库中未找到相关内容。`

## 2. 端到端 RAG 流程

推荐流程如下：

```text
上传/解析
  -> 结构感知清洗与分块
  -> chunk + metadata 入 PostgreSQL
  -> embedding 入 Qdrant
  -> 用户提问
  -> scope 解析
  -> query normalization
  -> query rewrite
  -> 向量召回 + 关键词召回 + metadata/filter 加权
  -> 候选融合
  -> qwen3-rerank 重排序
  -> 相邻 chunk 上下文扩展
  -> prompt 组装
  -> LLM 生成
  -> CitationValidator 校验/修复/降级
  -> SSE 输出 answer + citations + metadata
```

## 3. 入库与元数据优化

### 3.1 结构感知分块

Markdown、TXT、PDF、Word 等文档都必须尽量保留结构信息。Markdown 优先按标题层级聚合段落、列表、代码块、表格和提示块，避免固定字符切分打断语义。

推荐分块策略：

- Markdown：按标题路径分块，chunk 内容前置标题上下文。
- 普通文本：按段落优先，其次按句子或固定窗口兜底。
- PDF/Word：按页、段落和解析块组织，保证页码和 locator 可回溯。
- chunk 大小默认控制在 500-1000 中文字符或等价 token 范围内。
- overlap 默认 50-120 字符，只用于避免句子跨块丢失，不应制造大量重复候选。

### 3.2 必须保留的 metadata

每个 chunk 在 PostgreSQL 和 Qdrant payload 中都应保留：

- `user_id`
- `file_id`
- `file_name`
- `folder_id`
- `chunk_id`
- `chunk_index`
- `page_number`
- `start_pos`
- `end_pos`
- `locator`
- `document_type`
- `heading_path`
- `section_title`
- `token_count`

其中 `file_name`、`heading_path`、`section_title` 可作为检索增强文本拼接进 embedding 输入，但最终引用文本仍以原始 chunk content 为准。

### 3.3 Embedding 输入格式

为了让向量召回理解文档结构，embedding 输入不只使用正文，推荐格式：

```text
文件：{file_name}
路径：{heading_path}
章节：{section_title}
正文：
{content}
```

注意：该增强文本只用于向量化和检索，不应覆盖数据库中用于引用预览的原文 `content`。

## 4. 查询理解与问题改写

### 4.1 Query Normalization

检索前对用户问题做轻量标准化：

- 去除多余空白、重复标点和无意义口语尾词。
- 保留命令、错误码、API 名、模型名、配置项等大小写敏感 token。
- 中文问题不做激进分词改写，避免破坏产品名和专有名词。
- scope 为 `file` 或 `folder` 时，不再通过文件名猜测范围，直接使用 scope filter。

### 4.2 Query Rewrite

每次检索最多生成 2-3 个查询变体：

1. 原始问题：保持用户表达，适合语义向量召回。
2. 关键词查询：抽取产品名、错误码、命令、API、症状、配置项，适合 BM25/全文召回。
3. 意图补全查询：补齐隐含任务，例如“怎么处理”“最快检查”“修复方法”“注意事项”。

示例：

```text
原始问题：Telegram getMe returned 401 怎么处理？
关键词查询：Telegram getMe returned 401 token BotFather
意图补全查询：Telegram 启动报告 getMe returned 401 的最快检查和修复方法
```

改写必须保持用户原意，不得引入未出现的产品、平台或文件范围。

## 5. 混合检索

### 5.1 召回通道

推荐使用三路信号：

- 向量召回：Qdrant semantic search，适合自然语言问题。
- 关键词召回：PostgreSQL full-text、pg_trgm 或轻量 BM25，适合命令、错误码、API 名和专有名词。
- metadata/filter：`user_id`、`scope_type`、`scope_ids`、`folder_id`、`file_id`、`document_type`、`heading_path`。

MVP 不强制引入 Elasticsearch。关键词召回可先基于 PostgreSQL full-text 或进程内 BM25 实现；如后续新增持久化索引或评测表，必须同步更新 `docs/database.md` 和 Alembic migration。

### 5.2 候选规模

默认候选规模：

- vector top_k：30
- keyword top_k：30
- fusion 后候选：最多 40
- rerank 后候选：最多 8
- 最终进入 prompt 的主引用块：最多 6

若 scope 很窄，例如单文件且 chunk 数少于 30，可降低召回上限以减少延迟。

### 5.3 候选融合

优先使用 RRF（Reciprocal Rank Fusion）融合向量和关键词结果：

```text
rrf_score = sum(1 / (k + rank_i))
```

推荐 `k=60`。同一 `chunk_id` 多路命中时合并为一个候选，并保留以下诊断字段：

- `vector_rank`
- `vector_score`
- `keyword_rank`
- `keyword_score`
- `rrf_score`
- `matched_query_variant`

metadata 加权只做小幅调整，避免把低相关 chunk 强行抬高：

- scope 内命中：必须满足 filter，不作为加分项。
- heading 或 file_name 与查询关键词精确匹配：小幅加分。
- 相邻 chunk 不参与融合加分，只在上下文扩展阶段使用。

## 6. qwen3-rerank 重排序

### 6.1 模型与接口

重排序模型使用阿里云 qwen3-rerank：

```text
base_url = https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank
model = qwen3-rerank
```

调用输入：

- query：标准化后的原始问题，必要时拼接关键词查询。
- documents：fusion 后候选 chunk 文本。

document 文本建议包含少量结构上下文：

```text
文件：{file_name}
章节：{heading_path}
正文：{content}
```

### 6.2 重排策略

- 只对融合后的候选做 rerank，不直接对全库做 rerank。
- rerank 输入候选默认不超过 40 个，避免增加延迟和成本。
- rerank 输出按相关性分数排序，保留 top 8。
- 若最高 rerank 分数低于 `AISB_RAG_MIN_RELEVANCE_SCORE`，视为证据不足，进入降级回答。
- qwen3-rerank 服务超时、无 API key 或异常时，降级为融合排序结果，并在 metadata 中记录 `rerank_degraded=true`。

### 6.3 超时与性能

- rerank 单次请求建议超时 800ms-1200ms。
- Chat TTFB 紧张时，可先完成检索与生成首包，再在 metadata 中记录未启用 rerank；但默认方案仍以 rerank 后结果生成答案。
- 对完全相同的 `user_id + scope + normalized_query` 可做短期缓存，缓存内容只保存 chunk_id 和分数，不保存用户原文上下文。

## 7. 上下文组装与生成约束

### 7.1 最终上下文选择

最终进入 prompt 的主 chunk 最多 6 个。对于 rerank top chunk，可读取相邻 chunk 作为上下文扩展：

- 前一个 chunk：`chunk_index - 1`
- 后一个 chunk：`chunk_index + 1`

相邻 chunk 的作用是补充上下文，不应获得独立引用编号，除非它本身也在 rerank top chunks 中。

### 7.2 引用编号

引用编号只分配给主 chunk：

```text
[1] file={file_name} page={page_number} chunk_id={chunk_id}
{content}
```

如果 prompt 中包含相邻扩展，应标记为“补充上下文”，且生成器不得引用未编号扩展块。

### 7.3 Prompt 约束

System prompt 必须明确：

- 只允许根据上下文回答。
- 每个事实句或要点都必须带 `[n]`。
- 不知道就回答“知识库中未找到相关内容。”
- 禁止引用不存在的编号。
- 禁止编造文件、页码、命令、配置项、错误原因或修复步骤。

推荐输出结构：

- 简短直接回答。
- 多要点问题使用项目符号。
- 每条要点末尾带引用。

## 8. 引用校验与降级

### 8.1 校验规则

服务端必须在输出前校验：

- 回答非空。
- 回答不是无引用事实句集合。
- 引用编号都在 `[1..max_context_index]` 范围内。
- 每个事实句或列表项至少包含一个引用。
- 如果答案为“知识库中未找到相关内容。”，则 citations 必须为空。

### 8.2 修复与降级

校验失败时按顺序处理：

1. 尝试引用修复：为无引用句子绑定最相关的已有 chunk。
2. 再次校验。
3. 仍失败则降级为：`知识库中未找到相关内容。`

不得为了通过校验而新增不存在的引用编号。

### 8.3 Citation 载荷

SSE `citation` 事件继续使用 `docs/API.md` 的 Citation 结构：

```json
{
  "index": 1,
  "chunk_id": "uuid",
  "file_id": "uuid",
  "file_name": "document.pdf",
  "page": 3,
  "locator": {},
  "text": "原文对应段落/块内容预览...",
  "highlight_positions": {
    "start": 0,
    "end": 120
  }
}
```

`highlight_positions` 优先使用 chunk 的 `start_pos/end_pos`。PDF MVP 至少保证页码正确，复杂高亮可近似。

## 9. 配置项

建议新增或明确以下配置：

```env
AISB_RAG_HYBRID_SEARCH=true
AISB_RAG_VECTOR_TOP_K=30
AISB_RAG_KEYWORD_TOP_K=30
AISB_RAG_RERANK_TOP_K=8
AISB_RAG_CONTEXT_MAX_CHUNKS=6
AISB_RAG_MIN_RELEVANCE_SCORE=0.35

AISB_RERANK_PROVIDER=dashscope
AISB_RERANK_MODEL=qwen3-rerank
AISB_RERANK_BASE_URL=https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank
AISB_RERANK_API_KEY=<dashscope-api-key>
```

已有配置继续沿用：

```env
AISB_RAG_TOP_K=10
AISB_RAG_CHUNK_SIZE=512
AISB_RAG_CHUNK_OVERLAP=50
AISB_RAG_DEFAULT_COLLECTION=documents
AISB_EMBEDDING_PROVIDER=siliconflow
AISB_EMBEDDING_MODEL=BAAI/bge-m3
AISB_QDRANT_HOST=localhost
AISB_QDRANT_PORT=6333
```

SSE metadata 可增加：

```json
{
  "retrieval_strategy": "hybrid_rrf_rerank",
  "rerank_model": "qwen3-rerank",
  "retrieved_count": 40,
  "reranked_count": 8,
  "retrieval_ms": 650,
  "validation_status": "valid",
  "rerank_degraded": false
}
```

这些 metadata 不改变现有 SSE 事件顺序，也不改变 `citation` 载荷结构。

## 10. 测试与评测方案

### 10.1 测试语料

使用 `backend/tests/test_files` 下的 Markdown 文件作为离线评测语料：

- `openclaw常见问题.md`
- `openclaw渠道故障.md`
- `custom-video-capture.md`
- `水印和截图.md`

这些文件覆盖故障排查、渠道问题、SDK 操作步骤、注意事项和常见问题，适合验证中文 RAG 的语义召回、专有名词召回和引用定位。

### 10.2 固定评测问题

| 问题 | 期望命中文档 |
| --- | --- |
| OpenClaw 最初故障排查的前 60 秒应该执行哪些命令？ | `openclaw常见问题.md` |
| WhatsApp 二维码登录 408 超时应该检查什么？ | `openclaw渠道故障.md` |
| Telegram getMe returned 401 怎么处理？ | `openclaw渠道故障.md` |
| 自定义视频采集开启后为什么需要保持 enableCamera 为 True？ | `custom-video-capture.md` |
| 水印图片支持哪些格式？ | `水印和截图.md` |
| ZegoWatermark 的 imageURL 应该如何指定？ | `水印和截图.md` |

### 10.3 指标

- Recall@10：目标 `>= 0.90`
- Rerank 后 MRR@5：目标 `>= 0.80`
- Citation 覆盖率：`100%`
- 无效引用率：`0`
- Retrieval latency p95：`< 800ms`
- Chat 首条 SSE `chunk` TTFB：`< 2s`

### 10.4 对比实验

至少比较三组结果：

1. 仅向量召回。
2. 向量召回 + 关键词召回 + RRF。
3. 向量召回 + 关键词召回 + RRF + qwen3-rerank。

预期第三组在命令、错误码、API 名、SDK 注意事项类问题上优于仅向量召回。

### 10.5 命中统计脚本

后端提供命中统计脚本：

```bash
cd backend
python scripts/evaluate_rag_hits.py --qa-file tests/rag_test_qa.md --top-k 6 --log-level INFO
```

如需要保存完整明细：

```bash
python scripts/evaluate_rag_hits.py \
  --qa-file tests/rag_test_qa.md \
  --top-k 6 \
  --json-output .data/rag-eval/latest.json \
  --log-level DEBUG
```

脚本要求测试文档已完成入库和向量化；若库中有多个用户，使用 `--user-id <uuid>` 指定被评测用户。统计字段包括：

- `file_hit_rate`：返回 chunks 中是否命中期望来源文件。
- `section_hit_rate`：是否命中 QA 标注的段落/章节。
- `answer_hit_rate`：返回 chunk 与答案原文的覆盖率是否达到阈值，默认阈值为 `0.35`。
- `file_mrr` / `answer_mrr`：正确文件或答案证据首次出现的倒数排名。
- `ndcg`：按答案命中、章节命中、文件命中的 3/2/1/0 分级相关性计算。
- `best_answer_coverage`：每题 top-k 中最高答案原文覆盖率。

## 11. 分阶段落地计划

### Phase 1：文档与评测基线

- 建立固定评测问题和期望命中文档。
- 记录当前仅向量召回的 Recall@10、MRR@5 和引用校验结果。
- 不改变 API 和数据库结构。

### Phase 2：混合检索

- 增加 query normalization 和 query rewrite。
- 增加 PostgreSQL full-text 或轻量 BM25 关键词召回。
- 使用 RRF 合并向量和关键词候选。
- metadata 中记录检索策略和候选数量。

### Phase 3：qwen3-rerank

- 增加 DashScope qwen3-rerank client。
- 对融合候选进行 rerank。
- 增加超时、异常和无 API key 降级逻辑。
- metadata 中记录 `rerank_model`、`reranked_count`、`rerank_degraded`。

### Phase 4：引用与上下文增强

- 增加相邻 chunk 扩展。
- 保证扩展 chunk 不被错误编号。
- 强化逐句引用校验和降级策略。
- 验证引用点击后右侧抽屉可定位和高亮。

### Phase 5：持续评测

- 将 `backend/tests/test_files` 固定问题接入自动化测试。
- 每次调整 chunk、embedding、retrieval、rerank 或 prompt 时输出指标对比。
- 若新增评测持久化表，例如 `rag_eval_cases`，必须同步更新 `docs/database.md`、Alembic migration 和相关 API 文档。

## 12. 默认取舍

- 不引入 Elasticsearch 作为 MVP 必需依赖。
- qwen3-rerank 是默认首选重排序模型。
- rerank 失败时允许降级，但必须在 metadata 中显式标记。
- 检索准确率优先于回答覆盖面；证据不足时宁可拒答。
- 不为了看起来完整而放宽引用约束。
