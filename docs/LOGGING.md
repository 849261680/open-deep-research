# 本地日志

后端不再依赖 Prometheus、OpenTelemetry、Loki、Tempo 或 Grafana。排查运行状态时只看应用日志。

## 启动服务

```bash
./backend.sh
```

后端默认运行在 `http://localhost:8003`，启动脚本使用 `uvicorn` 热重载 `backend/app`。

## 查看日志

如果直接运行 `./backend.sh`，日志会输出在当前终端。需要保存日志时使用 shell 重定向：

```bash
./backend.sh 2>&1 | tee logs/backend.log
```

HTTP 请求会写入 `backend.http` 日志，字段包含：

- `method`
- `path`
- `status`
- `duration_seconds`

这些字段会追加在日志正文后面，格式为人类可读的 `key=value`：

```text
INFO [backend.http] http_request method=POST path=/api/research status=200 duration_seconds=0.014
```

业务模块继续使用标准 Python `logging.getLogger(__name__)`。需要更多细节时设置：

```bash
LOG_LEVEL=DEBUG ./backend.sh
```
