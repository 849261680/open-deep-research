# Deep Research Smoke Eval Baseline

## Run Configuration

- Tasks: 10
- Evaluated: 10
- Retriever: `tavily`
- Max sub queries: 5
- Max concurrency: 2
- Max read pages per section: 2
- Deep research breadth/depth: 0/1

## Aggregate Metrics

| Metric | Value |
|---|---:|
| coverage_score | 0.54 |
| citation_support_rate | 0.3563 |
| unsupported_claim_count | 48.7 |
| effective_citations | 10.5 |
| elapsed_seconds | 93.749 |
| search_count | 7.0 |
| read_count | 11.9 |

## Task Scores

| Task | Status | Coverage | Citation support | Unsupported claims | Search | Read | Elapsed(s) |
|---|---|---:|---:|---:|---:|---:|---:|
| `quantum-computing-applications-2026` | evaluated | 0.8 | 0.3714 | 44 | 7 | 12 | 80.28 |
| `ai-regulation-us-eu-china` | evaluated | 0.6 | 0.2692 | 57 | 7 | 12 | 93.28 |
| `ev-battery-recycling-economics` | evaluated | 1.0 | 0.4375 | 45 | 7 | 11 | 91.39 |
| `open-source-llm-enterprise-adoption` | evaluated | 0.6 | 0.4658 | 39 | 7 | 12 | 84.91 |
| `global-semiconductor-supply-chain-risk` | evaluated | 0.2 | 0.375 | 50 | 7 | 12 | 110.16 |
| `carbon-removal-market-quality` | evaluated | 0.6 | 0.1867 | 61 | 7 | 12 | 98.66 |
| `ai-agents-software-engineering` | evaluated | 0.4 | 0.3289 | 51 | 7 | 12 | 88.73 |
| `healthcare-ai-diagnostics-risk` | evaluated | 0.4 | 0.4366 | 40 | 7 | 12 | 90.32 |
| `robotaxi-commercialization-challenges` | evaluated | 0.2 | 0.3158 | 52 | 7 | 12 | 110.39 |
| `space-launch-market-competition` | evaluated | 0.6 | 0.3766 | 48 | 7 | 12 | 89.37 |

## Task Details

### quantum-computing-applications-2026

- Query: 量子计算的最新发展和应用场景
- Coverage: 0.8
- Citation support rate: 0.3714
- Unsupported claim count: 44
- Effective citations: 11
- Search/read/elapsed: 7 / 12 / 80.28s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: 容错量子计算, 量子纠错, NISQ, 优化问题
- Forbidden claim hits: none

### ai-regulation-us-eu-china

- Query: 美国、欧盟和中国人工智能监管政策对比
- Coverage: 0.6
- Citation support rate: 0.2692
- Unsupported claim count: 57
- Effective citations: 10
- Search/read/elapsed: 7 / 12 / 93.28s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: 风险分级, 生成式人工智能服务管理暂行办法, 合规义务
- Forbidden claim hits: none

### ev-battery-recycling-economics

- Query: 电动汽车动力电池回收的商业模式和经济性
- Coverage: 1.0
- Citation support rate: 0.4375
- Unsupported claim count: 45
- Effective citations: 8
- Search/read/elapsed: 7 / 11 / 91.39s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: 锂, 镍, 钴, 梯次利用, 回收成本
- Forbidden claim hits: none

### open-source-llm-enterprise-adoption

- Query: 开源大语言模型在企业中的落地场景和风险
- Coverage: 0.6
- Citation support rate: 0.4658
- Unsupported claim count: 39
- Effective citations: 12
- Search/read/elapsed: 7 / 12 / 84.91s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: 私有化部署, 数据安全, 许可证
- Forbidden claim hits: none

### global-semiconductor-supply-chain-risk

- Query: 全球半导体供应链的关键风险和缓解策略
- Coverage: 0.2
- Citation support rate: 0.375
- Unsupported claim count: 50
- Effective citations: 10
- Search/read/elapsed: 7 / 12 / 110.16s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: 出口管制
- Forbidden claim hits: none

### carbon-removal-market-quality

- Query: 碳移除市场的质量标准、MRV 和商业化挑战
- Coverage: 0.6
- Citation support rate: 0.1867
- Unsupported claim count: 61
- Effective citations: 12
- Search/read/elapsed: 7 / 12 / 98.66s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: MRV, 永久性, 碳信用
- Forbidden claim hits: none

### ai-agents-software-engineering

- Query: AI 编程智能体在软件工程中的能力边界和评价指标
- Coverage: 0.4
- Citation support rate: 0.3289
- Unsupported claim count: 51
- Effective citations: 11
- Search/read/elapsed: 7 / 12 / 88.73s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: SWE-bench, 工具调用
- Forbidden claim hits: none

### healthcare-ai-diagnostics-risk

- Query: 医疗 AI 诊断系统的临床价值、风险和监管要求
- Coverage: 0.4
- Citation support rate: 0.4366
- Unsupported claim count: 40
- Effective citations: 12
- Search/read/elapsed: 7 / 12 / 90.32s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: FDA, 偏差
- Forbidden claim hits: none

### robotaxi-commercialization-challenges

- Query: Robotaxi 商业化的技术、监管和单位经济挑战
- Coverage: 0.2
- Citation support rate: 0.3158
- Unsupported claim count: 52
- Effective citations: 10
- Search/read/elapsed: 7 / 12 / 110.39s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: 单位经济
- Forbidden claim hits: none

### space-launch-market-competition

- Query: 商业航天发射市场竞争格局和成本下降趋势
- Coverage: 0.6
- Citation support rate: 0.3766
- Unsupported claim count: 48
- Effective citations: 9
- Search/read/elapsed: 7 / 12 / 89.37s
- Budget: elapsed_seconds=True, search_count=True, read_count=True
- Expected fact hits: 可重复使用火箭, SpaceX, 发射成本
- Forbidden claim hits: none


## Overall Assessment

- The current baseline evaluates 10 of 10 fixed smoke tasks.
- Average coverage is 0.54, average citation support is 0.3563, and average unsupported claims per task is 48.7.
- Main improvement area: reports need to cover more of the fixed expected facts explicitly.
- Main reliability area: increase valid inline citations on factual claims.
- Main risk area: reduce uncited factual sentences or unsupported claim extraction noise.
