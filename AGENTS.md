# 开发规则

- 测试驱动开发，在构建功能时，先打造一个微小的、端到端的功能切片，寻求反馈，然后在此基础上逐步扩展。 曳光弹的概念源自《程序员修炼之道》。在构建系统时，你希望编写能尽快获得反馈的代码。曳光弹是贯穿系统所有层的小功能切片，让你能尽早测试和验证方法。这有助于识别潜在问题，并确保在投入大量开发时间之前，整体架构是稳健的。

- 永远不要破坏已有接口。新版本必须向后兼容，已有行为不得改变。

- 回归是最严重的错误。新改动引入的问题必须立即修复，不得拖延。

- 每次改动只做一件事。一个提交解决一个问题，不混入无关修改。

- 提交说明必须解释为什么，而不只是做了什么。"修复 bug"不是合格的说明，"防止 X 条件下 Y 崩溃"才是。

- 代码嵌套不能超过3层

- 每一个模块和函数都要写一个简短的注释来注明其功能

- 没有临时代码。进入系统的代码就是永久代码，不存在"以后再清理"。

- 写简单易读的代码，复杂代码是错误的代码。如果需要大段注释才能解释一段逻辑，说明这段逻辑需要重写。

- 先做正确，再做优化。不要在未确认瓶颈前优化性能，但一旦确认必须认真对待。

- uv管理虚拟环境

- 不要用RUFF,BLACK,LINT

# 本地可观测性栈

- 本项目提供本地可观测性栈，用于让开发者和智能体查询日志、指标和追踪。Docker 只负责运行这些基础设施容器，不负责记录业务日志。

- 日志链路是：后端写入 `logs/backend.log`，Promtail 读取日志文件，Loki 存储日志，智能体用 LogQL 查询。

- 指标链路是：后端暴露 `/metrics`，Prometheus 抓取指标，智能体用 PromQL 查询。

- 追踪链路是：后端通过 OpenTelemetry 导出 trace，OTel Collector 转发到 Tempo，Grafana 或 Tempo API 用 trace id 查询。

- 启动带可观测性的本地开发环境：

```bash
./scripts/dev-observability.sh
```

- 如果 `docker` 不在 PATH，脚本会尝试使用 Docker.app 自带的 CLI：`/Applications/Docker.app/Contents/Resources/bin/docker`。

- 常用本地端口：
  - 前端：`http://localhost:3003`
  - 后端：`http://localhost:8003`
  - Grafana：`http://localhost:3004`
  - Prometheus：`http://localhost:9091`
  - Loki：`http://localhost:3100`
  - Tempo：`http://localhost:3200`
  - OTel Collector HTTP：`http://localhost:4319/v1/traces`

- 智能体查询入口：

```bash
uv run python scripts/query_observability.py promql 'up{job="open-deepresearch-backend"}'
uv run python scripts/query_observability.py logql '{service="open-deepresearch-backend"} |= "ERROR"'
```

- 后端也提供 HTTP 查询接口：

```bash
POST /api/observability/promql
POST /api/observability/logql
```

- 排查“服务是否在线”时，优先查询：

```promql
up{job="open-deepresearch-backend"}
```

- 排查“接口是否被调用、状态码是否异常”时，优先查询：

```promql
open_deepresearch_http_requests_total
```

- 排查“后端错误日志”时，优先查询：

```logql
{service="open-deepresearch-backend"} |= "ERROR"
```

- 排查“深度研究规划是否生成”时，优先查询：

```logql
{service="open-deepresearch-backend"} |= "research_plan_created" | json
```

- 排查“某个 trace id 对应的日志”时，优先查询：

```logql
{service="open-deepresearch-backend", trace_id="<trace_id>"}
```

- 停止本地可观测性栈：

```bash
PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH" docker compose -f docker-compose.observability.yml down
```

- 普通 `./backend.sh` 不默认启用 JSON 日志和 trace 导出；只有 `./scripts/dev-observability.sh` 会设置 `OBSERVABILITY_JSON_LOGS=true` 和 `OBSERVABILITY_TRACING_ENABLED=true`。
