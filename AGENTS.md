# AGENTS.md

## 1. 项目使命

构建一个 Windows 本地运行的 CS2 收藏品研究与价格看板。它必须稳定、可审计、可恢复、不会伪造历史数据，并允许非程序员通过桌面图标启动。

## 2. 开始任何任务前

必须按顺序阅读：

1. `docs/PRODUCT_SPEC.md`
2. `docs/DECISIONS.md`
3. `docs/DATA_SOURCE_POLICY.md`
4. `docs/ARCHITECTURE.md`
5. 当前里程碑对应的 `codex-prompts/*.md`

若代码与文档冲突，以 `docs/DECISIONS.md` 和 `docs/PRODUCT_SPEC.md` 为准。若仍有冲突，停止扩大实现范围，在 `docs/OPEN_QUESTIONS.md` 记录问题。

## 3. 绝对约束

- 禁止使用、导入、推导或展示 Steam 市场价格。
- 禁止把 BUFF、C5、IGXE、5E 或旧平台价格拼接成悠悠主K线。
- 禁止用估算值填补缺失K线。
- 禁止把单个采样点伪装成具有真实高低价的完整OHLC。
- 禁止绕过验证码、登录限制、频率限制或平台访问控制。
- 禁止在运行时调用 OpenAI 或其他 AI API。
- 禁止把 Token、密码、Cookie、Webhook 或邮箱凭据提交到 Git。
- 禁止让本地HTTP服务监听公网地址；默认只能绑定 `127.0.0.1`。
- 禁止自动购买付费云服务或依赖必须付费的基础设施。
- 禁止把人工修正覆盖到原始导入记录；必须使用覆盖层。
- 禁止在没有备份和迁移测试的情况下执行破坏性数据库变更。

## 4. 数据真实性规则

每个价格点、K线、事件和分类关系都必须记录来源或计算依据。

所有展示数据至少应能回答：

- 来自哪个平台？
- 原始币种是什么？
- 价格口径是什么？
- 时间粒度是什么？
- 是原始数据、聚合数据还是人工修正？
- 数据是否完整？
- 是否存在缺口？
- 最后更新时间是什么？

缺失数据必须显示为空白和原因，不得线性插值。

## 5. 默认技术原则

- 后端：Python 3.12、FastAPI、SQLAlchemy 2、Alembic、Pydantic Settings。
- 数据库：SQLite，WAL 模式。
- 采集：`httpx`，适配器模式，APScheduler 或等价本地调度器。
- 前端：React、TypeScript、Vite。
- 表格：TanStack Table 或同等成熟组件。
- K线：Apache ECharts 或同等支持蜡烛图、缩放与事件标线的开源组件。
- 桌面托盘和启动器：PySide6。
- 打包：PyInstaller；若遇到稳定性问题，可评估 Nuitka。
- 测试：pytest、前端单元测试、Playwright 端到端测试。
- 代码格式：Ruff、Black、mypy；前端 ESLint、Prettier、TypeScript strict。
- 所有界面默认中文，内部标识和代码使用英文。

可以调整技术方案，但必须先在 `docs/ARCHITECTURE.md` 写出原因、迁移成本和验证方法。

## 6. 工作方式

- 一次只实施一个里程碑。
- 先写测试或验收脚本，再完成实现。
- 每次任务结束必须运行相关测试。
- 更新受影响的文档。
- 报告完成内容、未完成内容、已知风险和下一步。
- 不要一次生成一个“看起来完整但无法运行”的大型代码堆。
- 所有网络接口先做能力探测和固定样例测试。
- 对外部响应保存经过脱敏的样例到 `research/samples/`。
- 所有数据源实现必须放在独立适配器中。
- 数据源不可用时，界面仍应能浏览已有本地数据。

## 7. UI规则

- 首页按收藏品来源体系分组。
- 来源标签必须醒目，不能作为小号灰字隐藏。
- 同一收藏品允许在多个来源分类重复展示。
- 重复展示只创建关系引用，不复制价格对象或价格记录。
- 页面记住上次展开和收起状态。
- 电脑端优先。
- 价格来源和缺失原因必须视觉可见。
- 悠悠无价格、改用外部补充时，必须醒目标注外部平台。
- 点击饰品、武器箱名称进入详情页。
- 事件竖线同日多事件合并为一根，顶部右侧显示摘要，点击后展示全部事件。

## 8. 安全与隐私

- Token 使用 Windows Credential Manager 或仅当前用户可解密的存储。
- 前端永远不直接获得上游API Token。
- 日志必须过滤 Authorization、Cookie、Token 和密码。
- 数据导出默认不包含密钥。
- 本地管理页面只能从 localhost 访问。
- 应提供一键导出诊断包，但必须自动脱敏。

## 9. Git与提交要求

建议每个里程碑使用独立分支和小提交。提交信息示例：

- `docs: define taxonomy research workflow`
- `feat: add price source adapter contract`
- `test: cover gap-aware OHLC aggregation`
- `feat: add local tray launcher`

禁止提交：

- `.env`
- 实际 Token
- 实际邮箱密码
- 浏览器 Cookie
- 包含个人身份信息的日志
- 大型原始数据库
