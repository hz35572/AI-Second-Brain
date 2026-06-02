# 文档解析与分块处理方案

本文档定义 AI Second Brain 后端文档解析、结构分析、智能分块、分块优化与质量评估方案。方案必须与 `docs/PRD.md`、`docs/TECH_DESIGN.md`、`docs/API.md`、`docs/database.md` 保持一致，服务 MVP 的核心链路：TXT/PDF/Word/Markdown 上传解析、RAG 检索建库、严格引用溯源和右侧原文定位高亮。

## 1. 目标与硬约束

### 1.1 目标

- 稳定识别常见文档类型，并准确提取正文、标题、列表、表格、代码块、页码、段落、字符偏移等信息。
- 将不同格式文档统一转换为可分块、可向量化、可引用回溯的中间结构。
- 基于语义相关性、内容长度、主题边界和原文定位生成高质量 chunk。
- 保证 chunk 适合后续 embedding、检索、rerank、prompt 组装和 Citation 高亮。
- 建立可重复的分块质量评估指标，让分块策略可以持续优化，而不是依赖主观感觉。

### 1.2 硬约束

- MVP 稳定支持 TXT、Markdown、PDF、DOCX；Excel、PPT、图片 OCR 先保留接口和 locator 规范，按迭代计划接入。
- 每个可用于问答的 chunk 必须保留 `file_id`、`chunk_index`、`content`、`page_number`、`start_pos`、`end_pos`、`locator`、`token_count` 等元数据。
- 引用溯源不可丢失：PDF 至少保证页码正确；TXT/Markdown 使用字符偏移；DOCX 使用段落范围；Excel 使用 sheet/row/col。
- 不允许为了凑 chunk 大小打断代码块、表格、列表项、标题下的短段落集合或一个完整语义步骤。
- 10MB 文本/PDF 从上传到 ready 的全链路目标 < 15s；100MB 文件允许异步更久，但必须可报告进度并保证进程稳定。
- 日志不得记录用户原文内容；质量诊断只记录长度、数量、耗时、hash、错误类型和脱敏统计。

## 2. 总体流程

```text
上传完成
  -> 文件类型识别
  -> 解析器选择
  -> 内容提取
  -> 结构块归一化
  -> 清洗与格式保留
  -> 结构分析
  -> 智能分块
  -> 分块优化
  -> 质量评估
  -> chunks 入 PostgreSQL
  -> embedding 入 Qdrant
  -> 文件状态 ready
```

后端入口保持单一：

- `app.deepdoc.service.parse()`：文档解析唯一入口。
- `app.deepdoc.registry.ParserRegistry`：根据 MIME type、扩展名和文件签名选择 parser。
- `app.deepdoc.parsers`：具体格式解析器。
- `app.deepdoc.chunking`：结构感知分块与质量评估。
- `app.services.ingestion`：上传、解析、分块、入库、向量化的业务编排。

## 3. 文档类型识别

### 3.1 识别信号

文档类型识别必须同时使用多路信号，按可靠性排序：

1. 文件魔数或文件头签名。
2. 上传时提供的 MIME type。
3. 文件扩展名。
4. 内容探测，例如 Markdown 标题、front matter、PDF header、ZIP 内部结构。

不得只依赖扩展名，因为用户可能上传错误后缀文件。

### 3.2 类型识别规则

| 类型 | 扩展名 | MIME type | 强识别信号 | MVP 行为 |
| --- | --- | --- | --- | --- |
| TXT | `.txt`, `.text`, `.log` | `text/plain` | 可按文本编码成功解码 | 稳定支持 |
| Markdown | `.md`, `.markdown`, `.mdx` | `text/markdown`, `text/plain` | 标题、列表、代码围栏、front matter | 稳定支持 |
| PDF | `.pdf` | `application/pdf` | 文件头 `%PDF-` | 稳定支持 |
| Word | `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | ZIP 中存在 `word/document.xml` | 稳定支持 DOCX |
| Word legacy | `.doc` | `application/msword` | OLE 复合文档头 | MVP 可拒绝或异步转换后解析 |
| Excel | `.xlsx`, `.xls` | Excel MIME | ZIP 中存在 `xl/workbook.xml` | 保留接口 |
| PPT | `.pptx`, `.ppt` | PowerPoint MIME | ZIP 中存在 `ppt/presentation.xml` | 保留接口 |
| Image | `.png`, `.jpg`, `.jpeg`, `.webp` | image MIME | 图片文件头 | OCR 开关控制 |

### 3.3 冲突处理

- 魔数与扩展名冲突时，以魔数为准，并在任务结果中记录 `detected_type` 与 `declared_type`。
- 无法识别但可安全解码为文本时，按 TXT parser 尝试解析。
- 无法识别且不可解码时，返回解析失败，不创建可检索 chunk。
- 对压缩炸弹、超大嵌套 ZIP、异常 PDF 对象流等风险文件，必须提前限制解压大小、页数和解析时间。

## 4. 统一中间结构

解析器输出统一的 `ParsedDocument`，分块器只消费该结构，避免每种格式各自实现分块逻辑。

```text
ParsedDocument
  file_id
  document_type
  title
  language
  page_count
  word_count
  blocks[]
  raw_text
  metadata
```

结构块 `DocumentBlock`：

```text
DocumentBlock
  id
  type              # heading / paragraph / list / table / code / quote / image_text / page_break
  text
  level             # heading level or nesting level
  page_number
  start_pos
  end_pos
  locator
  style             # bold / italic / font / alignment 等可选格式信息
  parent_id
  order_index
```

`locator` 按文档类型表达：

- TXT/Markdown：`{"type":"text","start":0,"end":120}`
- PDF：`{"type":"pdf","page":3,"blocks":[...],"bbox":[x0,y0,x1,y1]}`
- DOCX：`{"type":"docx","paragraph_start":10,"paragraph_end":12,"run_start":0,"run_end":5}`
- Excel：`{"type":"excel","sheet":"Sheet1","row_start":1,"row_end":20,"col_start":1,"col_end":5}`
- PPT：`{"type":"ppt","slide":2,"shape_ids":["..."]}`
- Image OCR：`{"type":"image","page":1,"bbox":[x0,y0,x1,y1]}`

## 5. 内容提取方案

### 5.1 TXT

- 编码识别优先使用 UTF-8、UTF-8 BOM、GB18030、Big5、Latin-1 兜底。
- 保留段落分隔、列表形态、空行边界和字符偏移。
- 对连续空白做温和归一化：行内多个空格可压缩，段落空行保留为结构边界。
- `.log` 文件保留时间戳、错误码、命令、路径和堆栈格式，不做激进清洗。

### 5.2 Markdown

Markdown 解析必须结构感知，不应按纯文本粗暴切分。

需识别并保留：

- 标题层级：`#` 到 `######`
- 段落
- 有序/无序列表和嵌套层级
- fenced code block 和 inline code
- 表格
- blockquote 和 callout
- front matter
- 链接文本与 URL
- 图片 alt 文本

分块时 chunk 内应前置标题上下文，例如：

```text
标题路径：RAG 设计 > 混合检索 > 候选融合
正文：
...
```

标题上下文可用于 embedding 输入，但数据库 `content` 应尽量保留原始可读文本，避免污染引用预览。

### 5.3 PDF

PDF 解析目标分两层：

- MVP 必达：抽取文本、页码、页内块顺序，保证页码级引用准确。
- 增强目标：保留文本块 bbox、段落近似范围和页内高亮区域。

处理规则：

- 按页解析，页内按阅读顺序排序。
- 合并同一段落被 PDF 布局拆开的多行文本。
- 删除重复页眉、页脚、页码、目录重复项时必须谨慎，保留可引用正文。
- 对双栏 PDF 根据坐标和行距推断阅读顺序。
- 对扫描件 PDF，如 `AISB_RAG_ENABLE_OCR=true`，走 OCR；关闭时返回明确失败或仅提取可用文本。
- 对表格型 PDF，MVP 可线性化为 Markdown table 或多行键值文本，并保留页码。

PDF locator 至少包含：

```json
{
  "type": "pdf",
  "page": 3,
  "text_start": 1200,
  "text_end": 1700,
  "bbox": null
}
```

### 5.4 Word DOCX

DOCX 解析需读取 Office Open XML 结构，避免只抽纯文本导致格式丢失。

需识别并保留：

- 标题样式，例如 Heading 1/2/3。
- 段落和段落顺序。
- 有序/无序列表。
- 表格及单元格文本。
- 页眉页脚可作为 metadata，默认不进入正文分块，除非正文为空。
- 超链接文本和 URL。

DOCX 没有稳定页码时，引用定位优先使用段落范围：

```json
{
  "type": "docx",
  "paragraph_start": 24,
  "paragraph_end": 28
}
```

### 5.5 Word DOC

`.doc` 属于旧格式，MVP 不强制稳定支持。可选策略：

- 若部署环境存在安全转换工具，可转换为 DOCX 后解析。
- 若无法转换，返回 `ERR_UNSUPPORTED_FILE_TYPE` 或任务失败，并提示用户转换为 DOCX。
- 不允许通过不安全的外部命令处理用户文件，除非在 TDD 中明确沙箱策略。

### 5.6 表格、代码和链接

- 表格应尽量保留表头，分块时每个表格 chunk 必须带表头上下文。
- 超长表格按行组切分，每个子 chunk 重复表头。
- 代码块必须整体保留；超过最大 chunk 长度时，按函数、类、段落或注释边界切分。
- 链接应保留可读文本，URL 可作为 metadata；当 URL 本身是答案证据时保留在正文。

## 6. 结构分析

结构分析在内容提取之后、分块之前执行，目标是找出适合分块的自然边界。

### 6.1 结构树

根据标题、页、段落和列表层级构建结构树：

```text
Document
  Section H1
    Section H2
      Paragraph
      List
      Table
  Page
    Blocks
```

Markdown 和 DOCX 优先使用标题树；PDF 优先使用页和版面块，若能识别字号或目录，再推断标题树；TXT 使用段落和规则标题推断弱结构。

### 6.2 主题边界识别

主题边界由多种信号共同决定：

- 标题变化。
- 页或章节切换。
- 段落之间语义相似度明显下降。
- 列表主题结束。
- 表格或代码块开始/结束。
- 关键词或实体集合明显变化。

默认不为了达到固定长度跨越强标题边界。若某个章节太短，可与父级标题上下文合并，但不能与下一个无关章节硬拼。

### 6.3 格式信息保留

格式信息不直接决定检索，但会影响结构判断和引用体验：

- 标题层级进入 `heading_path`。
- 粗体、斜体、字号可作为 `style` 辅助判断标题或重点。
- 表格、代码、列表类型进入 chunk metadata。
- 页码、段落号、字符偏移必须用于 Citation。

## 7. 智能分块策略

### 7.1 默认参数

推荐默认值：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `target_tokens` | 512 | 单个 chunk 目标 token 数 |
| `min_tokens` | 120 | 低于该值优先尝试合并 |
| `max_tokens` | 900 | 超过该值必须继续切分 |
| `overlap_tokens` | 50 | 仅用于跨句或跨段保上下文 |
| `max_overlap_ratio` | 0.15 | 避免重复 chunk 过多 |
| `max_heading_depth` | 6 | Markdown/DOCX 标题层级 |

中文可以用字符数近似估算 token；正式实现优先使用 embedding 模型对应 tokenizer 或统一估算器。

### 7.2 分块优先级

分块边界优先级从高到低：

1. 强结构边界：文档、章节、页、标题。
2. 中结构边界：段落、列表、表格、代码块。
3. 语义边界：句子、步骤、问答项、主题转折。
4. 长度边界：token 上限兜底。

只在前三级无法满足 `max_tokens` 时使用长度兜底。

### 7.3 核心算法

```text
输入：ParsedDocument.blocks
输出：Chunk[]

1. 构建结构树并生成 heading_path。
2. 将 block 按强结构边界分组为 section units。
3. 对每个 section unit：
   3.1 若 unit token_count <= max_tokens，进入候选 chunk。
   3.2 若 unit 超长，按段落、列表、表格、代码块递归切分。
   3.3 若单个 block 超长，按句子或格式内部边界切分。
4. 合并相邻短 chunk：
   4.1 heading_path 相同或父子相邻。
   4.2 合并后不超过 target_tokens 或 max_tokens。
   4.3 语义相似度不低于阈值。
5. 为跨边界 chunk 增加少量 overlap。
6. 计算并写入 locator、start_pos、end_pos、page_number、token_count。
7. 执行质量评估，不合格则局部重分块。
```

### 7.4 Markdown 分块

Markdown 使用标题路径聚合：

- 一个标题下内容较短时，整节作为一个 chunk。
- 一个标题下内容较长时，按段落、列表、表格、代码块切分。
- 子标题内容不与兄弟标题混合。
- 每个 chunk 的 embedding 文本包含 `heading_path`，用于增强召回。
- 代码块和表格超过上限时，使用内部边界切分，并重复标题上下文。

### 7.5 PDF 分块

PDF 使用页和段落块双重边界：

- 页内连续段落优先合并到目标长度。
- 一般不跨页合并，除非上一页末尾和下一页开头明显属于同一段且 chunk 过短。
- 跨页 chunk 的 `locator` 应包含多个 page range；`page_number` 使用起始页。
- 复杂 PDF 至少保证页码级引用，bbox 缺失不阻塞入库。

### 7.6 DOCX 分块

DOCX 使用标题样式和段落范围：

- Heading 1/2/3 作为强边界。
- 同一标题下段落、列表和表格按顺序聚合。
- 表格长时按行组切分并重复表头。
- chunk locator 使用段落起止编号，必要时附带表格索引和单元格范围。

### 7.7 TXT 分块

TXT 使用弱结构识别：

- 空行分段。
- 识别常见标题模式，例如 `1. 标题`、`一、标题`、`## 标题`、全大写短行。
- 日志或命令输出按时间戳、错误段、堆栈段保留结构。
- 无明显结构时按句子窗口切分，最后使用 token 上限兜底。

## 8. 分块优化

### 8.1 短 chunk 合并

短 chunk 合并必须同时满足：

- token_count < `min_tokens`。
- 与相邻 chunk 的 `heading_path` 相同，或属于父子标题。
- 合并后不超过 `target_tokens`，特殊情况下不超过 `max_tokens`。
- 语义相似度达到阈值，例如 `cosine_similarity >= 0.72`。

不应合并 FAQ 中互不相关的问题，也不应合并不同错误码的排查步骤。

### 8.2 长 chunk 拆分

长 chunk 拆分顺序：

1. 按二级或三级标题拆。
2. 按段落拆。
3. 按列表项或步骤拆。
4. 按句子拆。
5. 按固定 token 窗口兜底。

拆分后每个子 chunk 必须保留相同标题路径，并重新计算 locator。

### 8.3 Overlap 策略

Overlap 只用于减少边界处信息丢失：

- 段落级分块：可重叠前后 1 句。
- 列表步骤：可重叠前一个步骤的结论句。
- 代码块：默认不 overlap，避免重复代码污染召回。
- 表格：重复表头不计为普通 overlap。

Overlap 不能导致同一事实在大量 chunk 中重复出现，否则会降低检索多样性并增加引用歧义。

### 8.4 去噪与去重

可删除或降权的内容：

- PDF 每页重复页眉页脚。
- 文档目录重复条目。
- 空段落、纯装饰符、过长分隔线。
- OCR 明显乱码段。

不可删除的内容：

- 错误码、命令、配置项、版本号。
- 法律、科研、合同等文档中的页眉脚注，如其可能承载条款编号或来源信息。
- 用户文档中的原始引用、链接和注释。

### 8.5 Embedding 文本增强

入库时建议区分两个文本：

- `content`：原始可读 chunk，写入 PostgreSQL，用于 Citation 预览。
- `embedding_text`：结构增强文本，写入向量化流程，不覆盖原文。

`embedding_text` 推荐格式：

```text
文件：{file_name}
标题路径：{heading_path}
页码/段落：{locator_summary}
正文：
{content}
```

## 9. 数据入库与向量化

### 9.1 PostgreSQL chunk 字段

`file_chunks` 至少写入：

- `id`
- `user_id`
- `file_id`
- `chunk_index`
- `content`
- `page_number`
- `start_pos`
- `end_pos`
- `locator`
- `token_count`
- `vector_id`

如后续需要持久化 `heading_path`、`document_type`、`quality_score` 等字段，必须同步更新 `docs/database.md` 和 Alembic migration；在未加字段前可放入 Qdrant payload 或任务 metadata，但不能破坏现有 API。

### 9.2 Qdrant payload

Qdrant payload 至少包含：

- `user_id`
- `file_id`
- `folder_id`
- `chunk_id`
- `chunk_index`
- `page_number`
- `locator`
- `document_type`
- `heading_path`
- `section_title`
- `token_count`

payload 不应包含大量原文；检索命中后回查 PostgreSQL 获取完整 chunk 内容。

### 9.3 顺序与一致性

- 同一文件内 `chunk_index` 必须稳定，按原文阅读顺序递增。
- 向量化失败时文件不得标记为 `ready`。
- 删除文件或文件夹时必须同步删除 PostgreSQL chunks、Qdrant points、对象存储原文和相关缓存。
- 重复上传同一 sha256 文件时，可以复用解析结果，但必须确保用户、文件夹、权限和引用 locator 正确隔离。

## 10. 分块质量评估

### 10.1 单文档质量指标

| 指标 | 目标 | 说明 |
| --- | --- | --- |
| 文本提取覆盖率 | `>= 0.95` | 提取字符数 / 可解析正文字符数 |
| 有效 chunk 比例 | `>= 0.98` | 非空且 token_count 合法的 chunk 占比 |
| chunk 长度合规率 | `>= 0.95` | token_count 位于 `[min_tokens, max_tokens]` 或有合理例外 |
| locator 完整率 | `100%` | 每个 chunk 有可回溯 locator |
| 页码准确率 | `>= 0.99` | PDF/PPT 引用页码准确 |
| 结构保留率 | `>= 0.90` | 标题、列表、表格、代码块被正确识别 |
| 重复率 | `<= 0.15` | chunk 间重复文本比例 |
| 边界破坏率 | `<= 0.05` | 表格、代码块、句子被不合理切断比例 |

### 10.2 RAG 效果指标

分块最终要服务检索和回答，因此必须接入 RAG 评估：

- Recall@10：固定问题能否召回正确 chunk，目标 `>= 0.90`。
- MRR@5：正确 chunk 排名是否靠前，目标 `>= 0.80`。
- Citation 覆盖率：事实句引用覆盖率 `100%`。
- 无效引用率：`0`。
- 检索延迟 p95：`< 800ms`。
- 10MB 建库全链路耗时：`< 15s`。

### 10.3 人工抽检项

每次改分块策略，应抽检以下类型文件：

- 标题层级复杂的 Markdown。
- 多页 PDF。
- 表格较多的 DOCX。
- 代码块、命令和错误码密集的技术文档。
- 中英文混排文档。

抽检问题：

- 引用点击后是否打开正确文件。
- PDF 是否跳到正确页。
- 高亮是否覆盖相近原文。
- chunk 是否包含完整语义。
- 检索结果是否被重复 chunk 挤占。

## 11. 自动化测试建议

### 11.1 Parser 单元测试

每种 parser 至少覆盖：

- 正常文档解析成功。
- 空文档或接近空文档。
- 错误扩展名但魔数正确。
- 编码异常或非法字符。
- 超大文件或解析超时。
- locator 是否生成。

### 11.2 Chunker 单元测试

必须覆盖：

- Markdown 标题路径分块。
- PDF 页码 locator。
- DOCX 段落范围 locator。
- 表格拆分时重复表头。
- 代码块不被无意义切断。
- 短 chunk 合并和长 chunk 拆分。
- overlap 比例不超过阈值。

### 11.3 集成测试

关键链路：

```text
上传测试文件
  -> 创建任务
  -> parse
  -> chunk
  -> chunks 入库
  -> embedding mock
  -> 文件 ready
  -> GET /files/{file_id}/chunks
  -> 校验 chunk 顺序、locator、page_number、token_count
```

### 11.4 性能测试

- 10MB TXT/PDF：统计上传完成到文件 ready 的全链路耗时。
- 100MB PDF：验证异步任务进度稳定、内存不持续增长、失败可恢复。
- 解析耗时分段记录：类型识别、内容提取、结构分析、分块、入库、向量化。

## 12. 错误处理与降级

| 场景 | 处理方式 |
| --- | --- |
| 不支持文件类型 | 任务失败，返回明确错误码和用户可理解提示 |
| PDF 无可提取文本 | OCR 开启则 OCR；关闭则失败并提示扫描件需 OCR |
| DOCX 结构损坏 | 尝试纯文本兜底；仍失败则任务失败 |
| 编码识别失败 | 尝试常见编码；仍失败则任务失败 |
| 分块后无有效 chunk | 文件标记 failed，不进入向量库 |
| locator 缺失 | 不允许 ready；必须重新解析或降级到页/段落级 locator |
| 向量化失败 | 保留 chunks，但文件状态不可 ready，任务记录错误 |

错误日志只记录文件 ID、任务 ID、类型、耗时、错误分类和堆栈摘要，不记录原文内容。

## 13. 进度与任务状态

解析建库任务建议进度：

| 阶段 | 进度 |
| --- | --- |
| 文件校验与类型识别 | 0-10 |
| 内容提取 | 10-35 |
| 结构分析 | 35-50 |
| 智能分块 | 50-65 |
| chunk 入库 | 65-75 |
| embedding 生成 | 75-90 |
| Qdrant 写入与 ready | 90-100 |

前端展示可使用 `tasks.progress` 和 `message`，例如“正在解析 PDF 第 12/80 页”“正在向量化：85%”。

## 14. 配置项建议

```env
AISB_RAG_CHUNK_SIZE=512
AISB_RAG_CHUNK_OVERLAP=50
AISB_RAG_CHUNK_MIN_TOKENS=120
AISB_RAG_CHUNK_MAX_TOKENS=900
AISB_RAG_MAX_OVERLAP_RATIO=0.15
AISB_RAG_ENABLE_OCR=false
AISB_RAG_PARSE_TIMEOUT_SECONDS=120
AISB_RAG_MAX_PAGES=500
AISB_RAG_MAX_EXTRACTED_CHARS=2000000
```

配置语义：

- `AISB_RAG_CHUNK_SIZE`：目标 chunk token 数。
- `AISB_RAG_CHUNK_OVERLAP`：默认 overlap token 数。
- `AISB_RAG_CHUNK_MIN_TOKENS`：短 chunk 合并阈值。
- `AISB_RAG_CHUNK_MAX_TOKENS`：强制拆分阈值。
- `AISB_RAG_ENABLE_OCR`：是否启用扫描件/图片 OCR。
- `AISB_RAG_PARSE_TIMEOUT_SECONDS`：单文件解析超时。
- `AISB_RAG_MAX_PAGES`：单文件最大页数保护。
- `AISB_RAG_MAX_EXTRACTED_CHARS`：提取文本保护上限。

如新增配置落地到 `app/core/config.py`，需同步更新 `docs/TECH_DESIGN.md` 的配置章节。

## 15. 分阶段落地计划

### Phase 1：统一解析接口与基础 parser

- 实现 `ParsedDocument` 和 `DocumentBlock`。
- 完成 TXT、Markdown、PDF、DOCX parser。
- 完成类型识别和 parser registry。
- 为每种 parser 建立基础单元测试。

### Phase 2：结构感知分块

- 实现 Markdown 标题树分块。
- 实现 TXT 段落/句子分块。
- 实现 PDF 页/段落分块。
- 实现 DOCX 标题/段落范围分块。
- chunk 入库时写入 `page_number/start_pos/end_pos/locator/token_count`。

### Phase 3：质量评估与局部重分块

- 增加 chunk 长度、重复率、locator 完整率、边界破坏率统计。
- 对超长、过短、locator 缺失 chunk 进行局部修复。
- 输出任务 metadata，供测试和排障使用。

### Phase 4：RAG 评测闭环

- 使用固定测试文档和问题评估 Recall@10、MRR@5、Citation 覆盖率。
- 对比不同 chunk size、overlap、标题上下文策略。
- 将评测结果纳入后端测试或离线评测脚本。

### Phase 5：增强格式与 OCR

- 接入 Excel、PPT、图片 OCR。
- 增强 PDF bbox 高亮。
- 支持更细粒度的表格 locator 和跨页 chunk locator。

## 16. 验收标准

完成本方案的 MVP 落地后，必须满足：

- TXT、Markdown、PDF、DOCX 上传后可解析、分块、入库和向量化。
- `GET /files/{file_id}/chunks` 返回的 chunk 顺序稳定，且每个 chunk 具备定位字段。
- Markdown chunk 保留标题上下文，代码块和表格不被不合理切断。
- PDF chunk 至少可定位到正确页。
- DOCX chunk 至少可定位到段落范围。
- chunk 质量评估指标可输出，异常分块可被测试发现。
- 10MB 文本/PDF 建库全链路目标 < 15s。
- 引用点击预览所需的 `file_id/chunk_id/page/locator/highlight_positions` 不丢失。

默认取舍：准确引用优先于分块数量压缩；证据可回溯优先于抽取覆盖率；结构完整性优先于固定 chunk 大小。
