# MuseaAgent 技术设计文档

> 基于 VisionFlow 原始 spec 修改
> 项目名从 VisionFlow 改为 MuseaAgent
> 核心改动：Chat 交互模式 + 混合检索 + Agent-first MVP + 分阶段交付

---

## 1. 项目定位

MuseaAgent 是一个基于 Unsplash 数据的 AI 视觉参考 Agent。用户用自然语言表达模糊的视觉需求，系统通过多模态理解、混合检索、RAG、Agent workflow，帮助用户找到适合的壁纸、摄影参考图片和摄影师作品集。

项目集成到已有 Flutter Unsplash App 中。

这一版的目标不是“先做一个能搜图的 API”，而是做一个 **最小但完整的视觉检索 Agent**。MVP 从第一版开始就覆盖生产环境里常见的一段 Agent 链路：

- 理解用户意图
- 提取结构化约束
- 改写 query
- 组织多路检索
- 判断结果质量
- 必要时重试
- 生成可解释结果

因此，MuseaAgent 被定义为 **Agent-first MVP**：优先练习 Agent 能力覆盖，而不是先做纯搜索接口、后面再套 Agent。

---

## 2. 核心交互模式

### 2.1 最终形态：Chat + SSE 流式

```
POST /api/chat
Content-Type: application/json
Accept: text/event-stream

{
  "conversation_id": "uuid_or_null",
  "message": "我想找深色安静的 OLED 壁纸，不要人物"
}
```

SSE 事件流（按阶段逐步推进）：

| type | 触发时机 | Flutter 表现 |
|------|----------|-------------|
| `thinking` | 意图分析中 | 加载动画 + 文字提示 |
| `intent` | 意图识别完成 | 展示"系统已理解"气泡 |
| `searching` | 检索执行中 | 搜索进度提示 |
| `result` | 结果产出（可多次） | 逐批渲染图片卡片 |
| `complete` | 全部完成 | 关闭流 |

支持多轮对话、模式自由切换（壁纸 / 摄影参考 / 摄影师）。

### 2.2 前期过渡形态：同步 Agent API

在 Chat 实现之前，先通过 `POST /api/search/photos` 走同一套 Agent pipeline，但同步返回 JSON，不走 SSE。这样它既是 Flutter 早期接入入口，也是调试、benchmark、回归测试入口。

---

## 3. 整体架构

```
Flutter App
    ↓
FastAPI Server
    ↓
LangGraph Agent Workflow (Phase 3+)
    ↓
Hybrid Retrieval / Rerank / Tools
    ↓
Supabase Postgres + pgvector + FTS
    ↑
Ingestion Pipeline （分析成功才写库）
    ↑
Unsplash Dataset / Unsplash API
```

### 架构分层

MuseaAgent 拆成三层：

1. `Core Retrieval Layer`
   - 负责 query normalization、embedding、FTS、metadata filter、fusion、rerank
   - 这一层必须可独立调用，作为所有 Agent 行为的基础能力层
2. `Agent Orchestration Layer`
   - 负责 intent、constraint extraction、query planning、critic、retry、response generation
   - 这一层把 retrieval 组织成完整的 Agent workflow
3. `Conversation Layer`
   - 负责多轮上下文、约束继承、topic reset、SSE 流式输出
   - 不承载底层检索细节，只做对话状态管理和交互编排

这样设计的目标是：既能练习完整 Agent 链路，又保留每一层独立调试和替换的空间。

### 数据库策略

Postgres + pgvector，不引入 MongoDB。

- 内部 PK 用 `BIGSERIAL`（顺序写，避免 UUID 索引膨胀）
- `uuid` 列唯一暴露给 API（不可猜测）

---

## 4. 数据库设计

### 4.1 photo_index

说明：下面这份表结构更接近长期目标 schema 候选。实际分阶段落地时，Phase 2/3 会先收敛成“最小检索索引表”，只保留写索引和读索引马上需要的字段，再按后续验证结果扩展语义列。

```sql
CREATE TABLE photo_index (
    id BIGSERIAL PRIMARY KEY,

    source TEXT NOT NULL DEFAULT 'unsplash',
    unsplash_photo_id TEXT NOT NULL UNIQUE,
    unsplash_user_id TEXT,

    raw_title TEXT,
    raw_description TEXT,
    raw_alt_description TEXT,

    thumb_url TEXT,
    small_url TEXT,
    regular_url TEXT,

    width INT,
    height INT,
    orientation TEXT,

    raw_metadata JSONB,

    search_text TEXT,                        -- 供 FTS 使用的拼接文本

    ai_caption TEXT,
    ai_short_caption TEXT,

    scene_tags JSONB DEFAULT '[]'::jsonb,
    mood_tags JSONB DEFAULT '[]'::jsonb,
    style_tags JSONB DEFAULT '[]'::jsonb,
    composition_tags JSONB DEFAULT '[]'::jsonb,
    lighting_tags JSONB DEFAULT '[]'::jsonb,
    color_tags JSONB DEFAULT '[]'::jsonb,
    subject_tags JSONB DEFAULT '[]'::jsonb,
    use_case_tags JSONB DEFAULT '[]'::jsonb,

    has_human BOOLEAN,
    has_face BOOLEAN,
    is_abstract BOOLEAN,
    is_minimal BOOLEAN,
    is_dark BOOLEAN,
    wallpaper_score FLOAT,
    photography_reference_score FLOAT,

    dominant_colors JSONB DEFAULT '[]'::jsonb,

    embedding VECTOR(1536),                  -- 语义向量

    status TEXT NOT NULL DEFAULT 'pending',
    last_error TEXT,

    indexed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

索引：

```sql
CREATE INDEX idx_photo_index_unsplash_user_id ON photo_index(unsplash_user_id);
CREATE INDEX idx_photo_index_orientation ON photo_index(orientation);
CREATE INDEX idx_photo_index_has_human ON photo_index(has_human);
CREATE INDEX idx_photo_index_wallpaper_score ON photo_index(wallpaper_score DESC);
CREATE INDEX idx_photo_index_photography_score ON photo_index(photography_reference_score DESC);
CREATE INDEX idx_photo_index_embedding_hnsw ON photo_index USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_photo_index_fts ON photo_index USING GIN(to_tsvector('english', search_text));
```

### 4.2 photographer_profile

```sql
CREATE TABLE photographer_profile (
    id BIGSERIAL PRIMARY KEY,

    source TEXT NOT NULL DEFAULT 'unsplash',
    unsplash_user_id TEXT NOT NULL UNIQUE,

    username TEXT,
    name TEXT,
    profile_image_url TEXT,

    photo_count INT DEFAULT 0,

    style_summary TEXT,
    common_scene_tags JSONB DEFAULT '[]'::jsonb,
    common_mood_tags JSONB DEFAULT '[]'::jsonb,
    common_style_tags JSONB DEFAULT '[]'::jsonb,
    common_composition_tags JSONB DEFAULT '[]'::jsonb,
    common_lighting_tags JSONB DEFAULT '[]'::jsonb,
    common_color_tags JSONB DEFAULT '[]'::jsonb,

    sample_photo_ids JSONB DEFAULT '[]'::jsonb,

    embedding VECTOR(1536),

    generated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 4.3 conversations

```sql
CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID UNIQUE DEFAULT gen_random_uuid(),
    user_id TEXT,
    title TEXT,
    message_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 4.4 messages

```sql
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conv_id BIGINT NOT NULL REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    structured_data JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_messages_conv_id ON messages(conv_id);
```

### 4.5 search_logs

用于 evaluation 和调试。

```sql
CREATE TABLE search_logs (
    id BIGSERIAL PRIMARY KEY,

    request_id TEXT UNIQUE,
    user_id TEXT,

    query TEXT NOT NULL,
    intent JSONB,
    rewritten_queries JSONB,
    filters JSONB,

    retrieved_photo_ids JSONB,
    reranked_photo_ids JSONB,

    latency_ms INT,
    model_usage JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.6 user_feedback

```sql
CREATE TABLE user_feedback (
    id BIGSERIAL PRIMARY KEY,

    user_id TEXT,
    conversation_id TEXT,
    message_id TEXT,
    unsplash_photo_id TEXT,

    feedback_type TEXT,
    -- like / dislike / save / click / hide / not_relevant

    feedback_reason TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);
```

### 4.7 ingestion_runs

```sql
CREATE TABLE ingestion_runs (
    id BIGSERIAL PRIMARY KEY,

    trigger_source TEXT,
    query TEXT,
    limit_count INT,

    processed_count INT DEFAULT 0,
    skipped_count INT DEFAULT 0,
    failed_count INT DEFAULT 0,

    status TEXT DEFAULT 'running',
    last_error TEXT,

    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP
);
```

---

## 5. Ingestion 设计

### 5.1 核心原则：分析成功才写库

```
读数据 → VLM 分析 → 构建 search_text → 生成 embedding → 写完整记录
                                                         ↑
                                                     失败就跳过，不留半成品
```

- 不从 Unsplash 存原始图片文件
- 每个 `unsplash_photo_id` 只处理一次（幂等）
- 失败记录 `last_error`，跳过，不中断整批

### 5.2 冷启动

- 使用 Unsplash Dataset Lite
- 解析 `photos.tsv`
- 对每张图执行：VLM 分析 → 构造 search_text → 生成 embedding → upsert 到 photo_index
- 第一批 5,000 - 10,000 张
- 在本地执行

### 5.3 增量 trigger

```
POST /internal/ingest/trigger?limit=30
Authorization: Bearer <INTERNAL_SECRET>
```

流程：
1. 校验 INTERNAL_SECRET
2. 从 query pool 选择 query，调 Unsplash API 拉取
3. 根据 unsplash_photo_id 去重
4. 对新图片执行分析流程
5. upsert 到 photo_index
6. 返回 processed / skipped / failed

约束：
- 每次 20-50 张
- 单次最多 2-5 分钟
- 幂等，不中断整批
- 不允许并发 trigger

### 5.4 Query Pool

维持原始 spec 的 query pool（壁纸类 / 摄影参考类 / 摄影师风格类）。

---

## 6. 混合检索设计

### 6.1 检索管线

检索读路径建立在先完成的写路径之上。系统先通过 ingestion pipeline 生成英文 `search_text`、`embedding` 和最小结构化字段，再由 retrieval 读取这些索引记录做召回与排序。

```
query
  │
  ├→ Embedding → Vector Search（语义相似性）
  ├→ Full-Text Search（关键词匹配，tsvector）
  └→ Metadata Filter（结构化过滤：首版仅保留 orientation 等稳定字段）
      │
      └→ Hybrid Fusion（加权合并/RRF）
           │
           └→ Rerank → final result
```

### 6.1a Query Normalization

用户原始 query 往往是中文自然语言、口语化、带模糊审美词，因此在进入 retrieval 之前，先做一次轻量标准化：

```text
原始 query
  → 意图识别（wallpaper / reference / photographer / auto）
  → 结构化约束提取（首版尽量收敛，只保留少量稳定硬过滤，如 orientation）
  → 英文检索短语改写（供 FTS 和 query embedding 使用）
```

例如：

```text
我想找深色安静的 OLED 壁纸，不要人物
→ mode: wallpaper
→ filters: { orientation: portrait }
→ rewritten query: dark calm oled wallpaper minimal no people
```

这样做的目的不是让 Query Normalization 取代 Agent，而是让第一版在中文输入场景下也能稳定练到英文 query rewrite、FTS 和最小结构化过滤这些真实问题。

### 6.2 Vector Search

基于 query embedding 查 `photo_index.embedding`：

```sql
SELECT
    id, unsplash_photo_id, orientation,
    1 - (embedding <=> :query_embedding) AS vector_score
FROM photo_index
WHERE status = 'indexed'
  AND (:orientation IS NULL OR orientation = :orientation)
ORDER BY embedding <=> :query_embedding
LIMIT 100;
```

### 6.3 Full-Text Search

基于英文 `search_text`（写路径生成的检索专用文本）：

```sql
SELECT *, ts_rank(to_tsvector('english', search_text), plainto_tsquery('english', :query)) AS fts_score
FROM photo_index
WHERE to_tsvector('english', search_text) @@ plainto_tsquery('english', :query)
  AND status = 'indexed'
  [metadata filters]
ORDER BY fts_score DESC
LIMIT 50;
```

### 6.4 Hybrid Fusion

第一版：**RRF（Reciprocal Rank Fusion）**

```python
def rrf_fusion(vector_results, fts_results, k=60):
    scores = {}
    for rank, item in enumerate(vector_results):
        scores[item["unsplash_photo_id"]] = 1.0 / (k + rank)
    for rank, item in enumerate(fts_results):
        scores[item["unsplash_photo_id"]] = scores.get(item["unsplash_photo_id"], 0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])
```

第二版可升级为加权线性融合。

### 6.5 Rerank

第一版：**规则 rerank**

```python
final_score =
    0.55 * hybrid_score +
    0.20 * retrieval_quality_score +
    0.10 * metadata_match_score +
    0.10 * orientation_score +
    0.05 * freshness_score
```

第二版可升级为 LLM rerank。

### 6.6 评分分层

为了让后面的 Critic、重试和调参更清晰，检索链路里的分数建议拆成几层：

- `vector_score`：语义相似性
- `fts_score`：关键词命中
- `metadata_match_score`：结构化约束满足程度
- `use_case_score`：是否更适合 wallpaper / reference / photographer
- `final_score`：最终排序分数

即便第一版不把所有分数暴露给前端，也建议在服务层和日志层保留这些中间结果，方便后续练习 rerank、critic 和评估。

---

## 7. LangGraph Agent 设计

### 7.1 Agent State

```python
class VisualSearchState(TypedDict):
    request_id: str
    conversation_id: str
    user_id: str | None

    original_query: str
    conversation_history: list[dict]

    mode: Literal["wallpaper", "reference", "photographer", "auto"]
    intent: dict | None
    rewritten_queries: list[str]
    filters: dict

    stream_events: list[dict]

    retrieved_items: list[dict]
    reranked_items: list[dict]
    critique: dict | None
    final_items: list[dict]

    retry_count: int
    errors: list[str]
```

### 7.2 Graph Nodes

| Node | 职责 | 输入 | 输出 |
|------|------|------|------|
| Intent | 判断当前模式、识别新话题还是延续 | 用户 query + 历史 | mode + topic decision |
| Constraint Extractor | 提取 mood/color/style/composition/constraints | 用户 query + mode | 结构化 filters |
| Query Planner | 生成 2-5 个改写 query，区分 strict / exploratory | intent + filters | rewritten_queries |
| Retrieval Orchestrator | 调 hybrid retrieval tool，并合并多 query 结果 | query + filter | candidates |
| Rerank | 排序 | candidates | reranked_items |
| Critic | 检查结果质量 | reranked_items | pass/fail + 重试建议 |
| Response | 生成最终回复 | reranked_items | items + 理由 |

其中第一版要刻意覆盖这些 Agent 问题：

- 中文自然语言到检索 query 的转换
- 硬约束保留，例如“不要人物”“竖屏”“深色”
- 多 query planning，而不是只查一个 query
- Critic 发现“结果太少 / 风格跑偏 / 违反约束”后触发一次 retry
- 生成面向用户的简短 `reason`

### 7.3 Conditional Routing

```
Intent → Constraint Extractor → Query Planner → Retrieval Orchestrator → Rerank → Critic
  ├─ pass=true  → Response
  └─ pass=false && retry_count < 1 → Query Planner / Retrieval Orchestrator（最多重试一次）
```

### 7.4 多轮上下文（Chat 阶段）

Conversation Layer 额外判断新话题还是延续：

- "再安静一点的" → 继承上一轮 intent，增量修改
- "换个风格，找雨夜人像" → 重置 intent
- 历史 messages 传给 LLM 作为上下文

约束继承原则：

- `hard constraints` 默认继承，除非用户显式取消
- `soft preferences` 可以在新一轮被弱化或替换
- Query Planner 在重写 query 时必须保留 hard constraints

---

## 8. 图片理解设计

复用原始 spec 的 VLM prompt 设计，强调摄影语言（构图、光线、色调、景别）而非通用 object detection。

注意：下面的输出 schema 是“分析层可生成的丰富结构”示例，不代表这些字段都必须在早期阶段直接固化成数据库列。

### 输出 Schema

```json
{
  "ai_caption": "A quiet rainy night street with neon reflections and a cinematic mood.",
  "ai_short_caption": "Rainy neon night street",
  "scene_tags": ["rainy city", "night street", "urban"],
  "mood_tags": ["lonely", "calm", "cinematic"],
  "style_tags": ["neo-noir", "low saturation", "moody"],
  "composition_tags": ["leading lines", "foreground framing"],
  "lighting_tags": ["neon reflection", "low exposure"],
  "color_tags": ["blue", "purple", "dark"],
  "subject_tags": ["street", "building", "reflection"],
  "use_case_tags": ["wallpaper", "photography reference"],
  "has_human": false,
  "has_face": false,
  "is_abstract": false,
  "is_minimal": false,
  "is_dark": true,
  "wallpaper_score": 0.84,
  "photography_reference_score": 0.91,
  "dominant_colors": ["#111827", "#374151", "#60A5FA"]
}
```

---

## 9. Photo Embedding 策略

将 AI metadata 拼成 embedding text 文本：

```text
Caption: Rainy neon night street.
Scene: rainy city, night street, urban.
Mood: lonely, calm, cinematic.
Style: neo-noir, low saturation, moody.
Composition: leading lines, foreground framing.
Lighting: neon reflection, low exposure.
Color: blue, purple, dark.
Use cases: wallpaper, photography reference.
```

`search_text` 基于同样内容构建，用于 FTS。

---

## 10. API 路由规划

### 10.1 最终路由

```
GET  /health

POST /api/chat           (Phase 5+)
POST /api/conversations  (Phase 5+)
GET  /api/conversations   (Phase 5+)
GET  /api/conversations/{id} (Phase 5+)

POST /api/search/photos    (同步 Agent 调试入口，长期保留)

POST /api/feedback

POST /internal/ingest/trigger
POST /internal/photographers/rebuild
POST /internal/eval/run
```

### 10.2 路由演进

| Phase | 可用路由 |
|-------|---------|
| 0 | `/health` |
| 1 | `/health` + `/internal/ingest/trigger` |
| 2 | + `/api/search/photos`（最小检索/同步 JSON） |
| 3 | + `/api/search/photos`（完整 Agent pipeline + critic/retry） |
| 4+ | + `/api/chat`（SSE chat 入口），`/api/search/photos` 继续作为调试/评估入口 |

---

## 11. 项目目录结构

```
musea-server/
  app/
    main.py
    config.py
    dependencies.py

    api/
      chat.py
      conversations.py
      feedback.py
      internal.py
      health.py

    agents/
      visual_search_graph.py
      states.py
      nodes/
        intent_node.py
        constraint_extractor_node.py
        query_planner_node.py
        retrieval_node.py
        rerank_node.py
        critic_node.py
        response_node.py

    tools/
      photo_search_tool.py
      photographer_search_tool.py
      rerank_tool.py
      unsplash_tool.py

    services/
      llm_service.py
      vision_service.py
      embedding_service.py
      query_normalization_service.py
      unsplash_service.py
      retrieval_service.py
      ingestion_service.py
      photographer_profile_service.py
      evaluation_service.py

    repositories/
      photo_repository.py
      photographer_repository.py
      conversation_repository.py
      message_repository.py
      search_log_repository.py
      feedback_repository.py

    schemas/
      chat.py
      conversation.py
      search.py
      photo.py
      photographer.py
      ingestion.py

    prompts/
      intent.md
      query_rewrite.md
      vision_analysis.md
      critic.md
      response_reason.md
      photographer_profile.md

  scripts/
    cold_start_unsplash_dataset.py
    rebuild_embeddings.py
    rebuild_photographer_profiles.py
    run_eval.py

  migrations/
    001_init.sql

  tests/
    test_intent_node.py
    test_constraint_extractor.py
    test_query_normalization.py
    test_retrieval_service.py
    test_rerank.py
    test_graph_flow.py

  pyproject.toml
  README.md
  .env.example
```

---

## 12. 阶段规划 & 验收标准

共 **12 个 session**，每个独立可验收。

| Phase | Session | 内容 | 交付物 | 验收标准 |
|-------|---------|------|--------|---------|
| **0** | 1 | 项目骨架 | pyproject.toml、FastAPI 启动、Supabase 连接、建表、/health | `curl /health` 返回 OK |
| **1a** | 1 | 冷启动 Ingestion | translation/search-text pipeline + embedding_service + ingestion_service + photo_repository | 5k+ 张索引记录，每条有 source_text/search_text/embedding |
| **1b** | 1 | 增量 trigger | POST /internal/ingest/trigger + query pool + Unsplash API | trigger 一次新增几张图并入库成功 |
| **2a** | 1 | 检索读核心 | query_normalization + retrieval_service：vector + FTS + orientation filter + RRF fusion + 规则 rerank | 单元测试覆盖中文 query 到英文检索 query 的转换，以及各检索组合 |
| **2b** | 1 | 同步 Agent API | POST /api/search/photos（走最小检索/Agent pipeline，同步 JSON） | curl 搜"深色壁纸"返回图片列表和 reason |
| **3a** | 1 | Agent 骨架增强 | llm_service、states、intent_node、constraint_extractor_node、query_planner_node + prompts | Agent 能输出结构化 intent、filters、改写 query |
| **3b** | 1 | 完整 Agent Graph | retrieval_node → rerank_node → critic_node → response_node + graph 组装 | 完整 Agent 流程跑通，支持一次 retry |
| **4** | 1 | 对话管理与 Streaming | conversations/messages 表 + repository + CRUD API + SSE chat | Flutter chat 可交互，并支持约束继承 |
| **5** | 1 | Evaluation | 固定 query set + baseline 对比 + 评分 | 能比较最小检索与完整 Agent 的效果差异 |
| **6** | 1 | 摄影师发现 | 聚合逻辑 + photographer_profile + 搜索 API | 能搜到摄影师 |

### 阶段间依赖

```
Phase 0 → Phase 1a → Phase 1b
                     ↓
                   Phase 2a → Phase 2b → Phase 3a → Phase 3b
                                                         ↓
                                                       Phase 4
                                                         ↓
                                                       Phase 5
                                                         ↓
                                                       Phase 6
```

每个 session 开始前，前一个阶段必须完成验收。

---

## 13. 技术栈

- Python 3.11+
- FastAPI + Uvicorn
- Pydantic v2
- Supabase Postgres + pgvector
- LangGraph
- LangChain Core（仅 message/tool abstraction）
- httpx（外部 API 调用）
- VLM API（Qwen-VL / Gemini Flash Vision / OpenAI）
- LLM API（Qwen / DeepSeek / Gemini Flash / OpenAI mini）
- Embedding API（OpenAI / Jina / Voyage / Qwen）
- Rerank：第一版规则，后续 LLM rerank

---

## 14. 部署方案

- FastAPI 部署到 Render / Railway
- Supabase 作为 DB
- GitHub Actions 每天触发 `/internal/ingest/trigger`
- 冷启动在本地执行

---

## 15. 安全设计

- Internal API：`Authorization: Bearer <INTERNAL_SECRET>`
- API Key 放环境变量，Flutter 不持有 service key
- IP 级别限流 + 用户级别限流

---

## 16. 成本控制

- 冷启动本地批量跑，每张图只分析一次
- 在线 side：用小模型做 intent、constraint extraction、query rewrite，规则 rerank，critic 只在必要时调 LLM
- 每次最多 retry 一次

---

## 17. 这个项目要刻意练到的 Agent 问题

MuseaAgent 作为练手项目，不只追求“结果可用”，还要尽可能覆盖生产中常见的 Agent 开发问题。第一版建议明确把这些问题当作设计目标：

- 用户 query 模糊、口语化、中文表达，如何转成可检索的结构
- 如何把 `hard constraints` 和 `soft preferences` 分开处理
- Query Planner 如何同时生成保守 query 和探索型 query
- 检索失败时，如何根据 Critic 结果做一次有方向的 retry，而不是盲重试
- 多轮对话里，如何继承约束、如何识别 topic reset
- 如何为结果生成简短但可信的解释
- 如何保留同步调试入口与 Chat 入口共用一条 Agent pipeline

这部分是 MuseaAgent 区别于“普通搜图接口”的关键，也是该项目作为 Agent 学习项目最有价值的地方。
