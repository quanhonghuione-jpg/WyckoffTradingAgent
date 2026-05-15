# 策略能力边界

本文档是公开仓库中的策略边界说明。真实量化规则、阈值、因子权重、排序逻辑、回测实现和持仓风控细节不在公开仓库维护，统一收敛到私有 `WyckoffStrategyAPI` 服务。

## 公开仓库保留什么

- Agent、CLI、MCP、Streamlit 维护入口和 React Web 展示层。
- 用户配置、登录、持仓、历史记录、导出、LLM 编排和通用数据查询。
- `Strategy API Client`：通过脱敏 API 调用私有策略服务。
- 公开安全的结果展示：评分、评级、阶段、触发名称、风险提示和摘要。

## 私有服务承载什么

- 漏斗筛选。
- 单股 Wyckoff 结构诊断。
- 策略回测。
- 真实规则树、阈值、权重、排序、风控和调参逻辑。

## API 开关

默认本地开发仍使用公开仓库里的兼容实现，便于过渡：

```bash
WYCKOFF_STRATEGY_API_MODE=local
```

闭源部署时使用远程私有策略服务：

```bash
WYCKOFF_STRATEGY_API_MODE=remote
WYCKOFF_STRATEGY_API_URL=https://your-strategy-api.example.com
WYCKOFF_STRATEGY_API_KEY=your-api-key
WYCKOFF_STRATEGY_VERSION=private-v1
```

`remote` 模式下，诊断、筛选、回测如果 API 不可用会直接报错，不会回退到本地策略实现。灰度期可以使用：

```bash
WYCKOFF_STRATEGY_API_MODE=auto
```

`auto` 模式只在 URL 和 Key 都配置时走私有 API；API 调用失败时回退本地兼容实现。

## 当前接入点

- `agents.chat_tools.analyze_stock(mode="diagnose")`
- `agents.chat_tools.portfolio(mode="diagnose")`
- `agents.chat_tools.screen_stocks`
- `agents.chat_tools.run_backtest`
- `scripts.web_background_job` 的漏斗后台任务
- `wyckoff screen` / `wyckoff backtest` CLI 子命令

## 公开发布前清理清单

1. 确认生产、Web、CLI、MCP 环境均配置 `WYCKOFF_STRATEGY_API_MODE=remote`。
2. 确认 `WyckoffStrategyAPI` 私有服务部署了真实策略包和数据源凭据。
3. 从公开仓库移除历史兼容策略实现和相关测试数据。
4. 保留 API Client、接口契约测试和公开结果展示逻辑。
5. 发布前检查文档、截图、测试快照，确保没有规则阈值、权重或内部调参说明。
