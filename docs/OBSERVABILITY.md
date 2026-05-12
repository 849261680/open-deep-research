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
