# 前端维护记录

## 测试警告

`@testing-library/react` 已从 13.x 升级到 14.x，React 18 测试不再通过 `react-dom/test-utils` 调用 `act`。`CI=true npm test -- --watchAll=false` 的输出不再刷 `ReactDOMTestUtils.act` 弃用警告。

## punycode 来源

`punycode` 仍由 `react-scripts@5.0.1` 的传递依赖引入：

- `react-scripts -> jest -> jest-environment-jsdom -> jsdom -> tough-cookie / whatwg-url / tr46`
- `react-scripts -> eslint -> ajv -> uri-js`
- `react-scripts -> workbox-webpack-plugin -> workbox-build -> source-map -> whatwg-url / tr46`

当前测试和构建没有失败，这属于 CRA 工具链维护债，不是运行时功能缺陷。

## 构建栈路径

短期继续保留 CRA，理由是当前 `react-scripts build` 和测试套件稳定，迁移会触碰 dev server、Jest、环境变量和部署产物。维护动作限制在测试库、小范围覆盖依赖和现有 `scripts/patch-cra-webpack-dev-server.js`。

中期迁移 Vite 的最小路径是先新增并验证独立 Vite 构建入口，再迁移测试到 Vitest 或保留 Jest 的兼容配置，最后替换 `start`、`build`、`test` 脚本。迁移验收应覆盖当前首页、登录、历史切换、流式研究和报告渲染，不应和功能改动混在同一次提交里。
