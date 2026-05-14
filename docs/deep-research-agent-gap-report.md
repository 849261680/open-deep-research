# 顶尖深度研究智能体对标与差距报告

调研日期：2026-05-15  
对应 Beads：`open-deepresearch-s48`

## 结论

本项目已经具备“可用的 GPT Researcher 风格深度研究应用”雏形：能够做初始搜索、生成结构化研究计划、并行处理子查询、压缩证据、做章节校验、递归深挖、流式展示进度并生成带引用的报告。它不是一个浅层搜索包装。

但和 2026 年公开资料里的顶尖深度研究智能体相比，核心差距不在“有没有 plan/search/report”，而在六个产品化能力：可控研究计划、海量且可信的数据源、可审计的证据链、专业评测闭环、多工具执行能力、多形态交付。顶尖系统把深度研究当作“可被用户监督的长期代理工作流”，本项目当前更像“固定流程的单次研究流水线”。

最有价值的下一步不是继续堆 UI，而是先做一个小型 Deep Research Bench 风格评测集和证据链质量门槛，用 10-20 个真实任务量化当前输出的引用准确率、有效引用数、召回缺口和耗时。没有这个闭环，后续多智能体、MCP、浏览器、文件连接器都会缺少判断标准。

## 调研范围

本报告参考了三类公开资料：

- 商业产品：OpenAI Deep Research、Gemini Deep Research、Claude Research、Perplexity Sonar Deep Research、You.com ARI、Genspark Deep Research。
- 开源实现：LangChain `open_deep_research`、GPT Researcher。
- 评测基准：Deep Research Bench、BrowseComp。

同时检查了本仓库当前实现，重点文件包括：

- `backend/app/research/agent.py`
- `backend/app/research/conductor.py`
- `backend/app/research/query_planner.py`
- `backend/app/research/retriever.py`
- `backend/app/research/source_curator.py`
- `backend/app/services/evidence_store.py`
- `backend/app/services/verifier_service.py`
- `backend/app/research/writer.py`
- `frontend/src/services/api.js`
- `frontend/src/components/StreamingResults.js`

## 顶尖系统怎么做

### 1. OpenAI Deep Research：可控代理流程 + 工具强化

OpenAI 官方说明把 Deep Research 定义为计划、研究、综合复杂问题并产出文档化报告的能力。关键模式是：用户选择来源范围，系统先给出研究计划，用户可审阅和修改；运行中能看进度，也能中断并调整焦点或来源；最后产出结构化报告和引用链接。

更重要的是，OpenAI 把它设计成能访问公共网页、上传文件、连接应用和 MCP 的研究代理；2026 年更新还强调可限制到可信网站、实时进度和中断修正。原始发布也说明它会在数十分钟内分析数百个来源，并使用浏览、Python、图表和图片等工具。OpenAI 的 BrowseComp 也体现了一个方向：顶尖研究代理不是“搜到结果”，而是能在难找信息上持续改写搜索策略、跨多个网页拼接线索。

对本项目的启示：我们已有结构化计划和递归深挖，但计划不是用户可编辑的契约；工具层也基本局限在搜索、网页抓取和 LLM，总体还没有 Python/文件/表格/浏览器/MCP 这样的执行能力。

### 2. Gemini Deep Research：研究计划 + Google 生态数据源 + 多形态输出

Gemini 的公开帮助文档显示，它默认使用 Google Search，同时可以选择 Gmail、Drive、上传文件和 NotebookLM notebooks 等来源；提交后 Gemini 会生成研究计划，用户可以先编辑计划再开始研究。报告通常需要 5-10 分钟，更复杂的任务更久。Google AI Ultra 版本还可以在报告中加入图表、图解、交互模拟器，并支持导出到 Google Docs。

对本项目的启示：Gemini 的优势是数据源和交付形态。我们的 `ResearchConfig` 已有 `query_domains` 和 `source_urls`，但还不是完整的“来源选择体验”；最终报告也主要是 Markdown 文本，没有图表、表格制品、Docs/PDF/Word 等一等交付物。

### 3. Claude Research：短周期研究模式 + 内部上下文

Claude 官方帮助页把 Research 描述为能进行多次相互衔接的搜索，并自动探索问题的不同角度。Research 可跨网页和已连接的内部上下文运行，例如 Gmail、Calendar、Google Docs。另一个官方页面把 Research 定位为适合 5 次以上工具调用、1-3 分钟内完成的综合信息收集，并且默认和 extended thinking 结合。

对本项目的启示：Claude 的差异点是“研究模式”与“普通搜索/深思考”的清晰分层，以及内部知识源连接。我们目前前端默认发送 `report_type: 'deep'`、`deep_research_breadth: 2`、`deep_research_depth: 2`，但用户难以理解不同深度、耗时、成本和质量之间的取舍。

### 4. Perplexity Sonar Deep Research：API 化、成本透明、搜索规模明确

Perplexity 官方 API 文档把 Sonar Deep Research 定义为能跨数百来源做详尽搜索、综合专家级洞察并生成详细报告的模型；文档公开 128K context、详细报告生成、搜索查询成本、reasoning token、citation token、引用列表和搜索查询数等元数据。

对本项目的启示：Perplexity 的 API 产品化能力比我们强很多。我们已有 `CostTracker` 和 `cost_update` 事件，但还没有把搜索次数、引用 token、推理成本、来源计数、读页计数、每阶段耗时做成稳定的开发者可用元数据。

### 5. You.com ARI 与 Genspark：规模化来源 + 商业报告包装

You.com ARI 官方资料称它可分析最多 400 个来源，在 5 分钟内生成专业级研究，并结合公私数据源，为企业输出 PDF 报告。Genspark Deep Research 则公开强调 Mixture-of-Agents，多模型协作制定研究计划，处理 1.6M words、1,338 个来源，20-30 分钟产出报告、思维导图、数据表和视频引用。

对本项目的启示：这类产品押注的是大规模来源、模型协作和“可直接交付”的商业制品。本项目当前更克制：默认 `max_sub_queries=5`、`max_concurrency=3`，每次搜索和每节来源数量都比较小，适合 MVP，但离“咨询级研究制品”还有距离。

### 6. LangChain Open Deep Research 与 GPT Researcher：开源参考架构

LangChain `open_deep_research` 的 README 显示它已用 LangGraph 运行，支持不同模型承担 summarization、research、compression、final report，并支持多种搜索 API、MCP、LangGraph Studio、Open Agent Platform，以及 Deep Research Bench 评测。它的旧实现还保留了 plan-and-execute human-in-the-loop 和 supervisor-researcher 多智能体版本。

GPT Researcher 的核心架构是 planner、execution agents、publisher：planner 生成研究问题，执行代理收集信息，publisher 汇总为报告。它强调来源跟踪、20+ 来源聚合、JavaScript 网页抓取、上下文记忆、PDF/Word 等导出。

对本项目的启示：本项目已经接近 GPT Researcher 的主流程，但还缺模型职责拆分、工作流图状态机、可视化调试、评测适配、JS 渲染抓取和导出能力。

## 本项目当前能力画像

### 已经做得不错的部分

1. 结构化计划已经存在。`QueryPlanner.plan_detailed()` 会输出 `ResearchPlanItem`，包含 `dimension`、`rationale`、`search_queries`、`expected_outcome`、`evidence_targets`。

2. 研究流不是单层搜索。`ResearchConductor._process_query_tree()` 会在章节证据不足时根据 `DeepResearchDecision` 递归生成 follow-up queries，受 `deep_research_depth` 和 `deep_research_breadth` 控制。

3. 并发研究已经存在。`conduct_research()` 用 `asyncio.Semaphore` 控制 `max_concurrency`，并行处理根子查询。

4. 有证据层和校验层。`EvidenceStore` 保存 evidence item，`VerifierService` 先尝试 LLM critic，失败后有规则兜底；`ResearchWriter` 会把校验、证据压缩、深挖记录放进最终写作 prompt。

5. 前端有过程可见性。`StreamingResults.js` 已展示 planning、search_result、analysis_progress、deep_research_decision、cost_update、report_complete 等事件。

6. 有本地可观测性入口。`docs/OBSERVABILITY.md`、Prometheus/Loki/Tempo、`/api/observability/promql` 和 `/api/observability/logql` 对调试长流程有价值。

### 主要差距

| 维度 | 顶尖系统 | 本项目现状 | 差距判断 |
| --- | --- | --- | --- |
| 研究计划控制 | 用户可审阅、编辑、中断、调整来源 | 后端直接生成并执行计划；前端展示但不可编辑 | 高 |
| 来源范围 | 公共网、文件、私有知识库、应用、MCP、行业数据库 | Web 搜索、配置 URL、域名过滤 | 高 |
| 来源规模 | 数百到上千来源，长耗时任务可接受 | 每查询默认较少来源，EvidenceStore 只提取前 2 个无内容链接 | 高 |
| 工具能力 | 浏览器、Python、文件、表格、图表、图片、交互制品 | 搜索、抓取、LLM、压缩、校验 | 高 |
| 证据审计 | 句级引用、来源 used/activity history、可下载报告 | 引用列表和章节校验，但非句级 claim verification | 中高 |
| 评测闭环 | DRB、BrowseComp、产品内部 evals | 单元/接口测试为主，未见真实研究质量 benchmark | 高 |
| 模型分工 | 研究/压缩/总结/写作可用不同模型 | `DeepSeekLLM` 贯穿 planner、verifier、writer | 中高 |
| 可观测性 | 进度、活动历史、成本/搜索/引用元数据 | 有日志和 cost，但阶段指标还不完整 | 中 |
| 输出形态 | Markdown、Word、PDF、Docs、图表、思维导图、音频/可视化 | 主要是 Markdown 报告和前端展示 | 中 |

## 优先级建议

### P0：先补评测，不要先大改架构

建立一个小型 `evals/deep_research_smoke/`，先收 10-20 个任务，覆盖中文、英文、需要多来源对比、需要数值、需要官方来源、需要反方观点的场景。每个任务至少定义：

- 期望覆盖的事实点
- 必须或优先使用的来源类型
- 不应出现的错误结论
- 引用是否支持对应事实
- 最长耗时和搜索预算

最低可行指标：

- `citation_support_rate`：引用是否真的支持附近论断
- `effective_citations`：有效引用数量
- `coverage_score`：关键事实点覆盖率
- `unsupported_claim_count`：无来源断言数量
- `elapsed_seconds`、`search_count`、`read_count`、`llm_cost`

这一步能直接回答“我们到底比顶尖差在哪里”，也是后面接 MCP、浏览器、多模型之前的质量基线。

### P1：把研究计划变成用户可控契约

当前后端已经能发 `plan_items`，可以做最小切片：

1. 先请求 `/api/research/plan` 只生成计划，不执行研究。
2. 前端展示计划项、搜索语句、证据目标，允许用户删除/编辑/补充。
3. 用户确认后再调用现有 `/api/research`，把确认后的计划传入。

这样能接近 OpenAI/Gemini 的“先审计划再跑研究”，也能减少错误方向上的长耗时。

### P1：增强来源与证据管线

当前 `EvidenceStore.add_many()` 只对前两个缺少 `extracted_content` 的链接做正文提取，这会限制深度研究质量。建议先做小改动：

- 记录每个候选来源的状态：searched、selected、read、failed、cited、discarded。
- 把正文提取数量从固定 2 改为受预算控制的 `max_read_pages_per_section`。
- 增加 PDF/HTML/JS rendered page 的清晰失败原因。
- 对 `query_domains` 和 `source_urls` 做前端来源选择入口，而不是隐藏配置。

### P1：做 claim-level 引用校验

现在 `VerifierService` 是章节级 critic，无法保证每个关键事实都被来源支撑。建议新增最小 slice：

1. 从最终报告抽取带引用的句子。
2. 对每个句子取引用来源正文片段。
3. 用 LLM 或规则判断 `supported / partially_supported / unsupported`。
4. 在报告末尾给出“引用质量摘要”，并把 unsupported claim 数写入 cost/quality summary。

这会直接对齐 Deep Research Bench、MiroEval 这类评测关注的 groundedness 和 citation quality。

### P2：模型职责拆分

LangChain `open_deep_research` 把 summarization、research、compression、final report 分开配置。我们可以先不换 LangGraph，只在 `ResearchConfig` 加：

- `planner_model`
- `research_model`
- `verifier_model`
- `writer_model`

然后让 `DeepSeekLLM` 支持按用途读取模型配置。这样可以用便宜模型做规划/压缩，用强模型做最终报告或校验。

### P2：补专业交付形态

先做低风险输出：

- Markdown 下载
- PDF 导出
- Word 导出
- 来源清单 CSV
- 研究活动 JSON

图表、思维导图、交互模拟器可以等评测闭环稳定后再做。

### P3：再考虑多智能体/工作流图

多智能体不是第一优先级。当前代码里的 `ResearchConductor` 已经是清晰的顺序/并发控制器，盲目迁移 LangGraph 会增加复杂度。只有当评测显示瓶颈来自任务拆分、回溯、状态恢复或多分支协调时，再考虑：

- supervisor-researcher 并行架构
- durable graph state
- human-in-the-loop approval node
- research branch retry/reflection node

## 建议的近期路线图

### 1 周内

- 新建 10-20 条固定 deep research eval 任务。
- 为研究过程记录 `search_count`、`read_count`、`selected_source_count`、`cited_source_count`、`elapsed_seconds`。
- 生成一份本项目当前基线报告：质量分、耗时、失败样例。

### 2-3 周

- 增加计划预览/确认流程。
- 增加来源选择入口：指定域名、指定 URL、是否允许全网搜索。
- 把正文读取数量改成预算控制。
- 加 claim-level 引用校验。

### 1-2 个月

- 多模型职责拆分。
- Markdown/PDF/Word/JSON 导出。
- 接入文件上传/PDF 研究。
- 评估是否需要 LangGraph 或其他 durable workflow。

## 参考资料

- OpenAI Help Center, “Deep research in ChatGPT”: https://help.openai.com/en/articles/10500283-deep-research-faq
- OpenAI Academy, “Research with ChatGPT”: https://openai.com/academy/search-and-deep-research/
- OpenAI, “Introducing deep research”: https://openai.com/index/introducing-deep-research/
- OpenAI, “BrowseComp: a benchmark for browsing agents”: https://openai.com/index/browsecomp/
- Google Gemini Help, “Use Deep Research in Gemini Apps”: https://support.google.com/gemini/answer/15719111?hl=en
- Anthropic Help Center, “Using Research on Claude”: https://support.claude.com/en/articles/11088861-using-research-on-claude
- Anthropic Help Center, “When should I use web search, extended thinking, and Research?”: https://support.claude.com/en/articles/11095361-when-should-i-use-web-search-extended-thinking-and-research
- Perplexity Docs, “Sonar Deep Research”: https://docs.perplexity.ai/docs/sonar/models/sonar-deep-research
- You.com, “Introducing ARI”: https://you.com/resources/introducing-ari-the-first-professional-grade-research-agent-for-business
- Genspark, “Introducing Genspark Deep Research”: https://www.genspark.ai/blog/genspark-autopilot-agent-deep-research
- LangChain `open_deep_research`: https://github.com/langchain-ai/open_deep_research
- GPT Researcher: https://github.com/assafelovic/gpt-researcher
- FutureSearch, “Deep Research Bench Leaderboard”: https://futuresearch.ai/deep-research-bench/
- arXiv, “Deep Research Bench: Evaluating AI Web Research Agents”: https://arxiv.org/abs/2506.06287
