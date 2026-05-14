# 本地可观测性栈
- 当你需要程序的报错信息和性能信息时，请阅读docs/OBSERVABILITY.md。

# 开发规则

- 测试驱动开发，在构建功能时，先打造一个微小的、端到端的功能切片，寻求反馈，然后在此基础上逐步扩展。 曳光弹的概念源自《程序员修炼之道》。在构建系统时，你希望编写能尽快获得反馈的代码。曳光弹是贯穿系统所有层的小功能切片，让你能尽早测试和验证方法。这有助于识别潜在问题，并确保在投入大量开发时间之前，整体架构是稳健的。

- 回归是最严重的错误。新改动引入的问题必须立即修复，不得拖延。

- 重要！做最小化改动，每次改动只做一件事，快速获取反馈。

- 代码嵌套不能超过3层

- 每一个模块和函数都要写一个简短的注释来注明其功能

- 没有临时代码。进入系统的代码就是永久代码，不存在"以后再清理"。

- 写简单易读的代码，复杂代码是错误的代码。如果需要大段注释才能解释一段逻辑，说明这段逻辑需要重写。

- 死代码和不必要的代码需要删除

- uv管理虚拟环境

- 不要用RUFF,BLACK,LINT

- 后端使用basedpyright 进行类型检查

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
