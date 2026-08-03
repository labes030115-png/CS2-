# CS2 收藏品价格研究看板：Codex 启动包

这是一套交给 Codex 使用的项目说明、约束、实施顺序和验收标准。目标是在 Windows 本地运行一个只供本机访问的 CS2 收藏品研究与价格看板。

## 使用顺序

1. 新建一个空的 GitHub 仓库，例如 `cs2-collection-tracker`。
2. 把本压缩包中的全部文件原样放到仓库根目录。
3. 在 Codex 中打开该仓库。
4. 把 `CODEX_START_PROMPT.md` 的内容作为第一条任务发送给 Codex。
5. Codex 必须先完成“数据源能力探测”，不得直接跳到完整网页开发。
6. 每完成一个里程碑，先运行测试、更新文档、生成报告，再进入下一阶段。
7. API Token 只在应用首次运行时由用户输入，禁止提交到 Git。

## 项目目标概览

- 首页按完整收藏品来源体系分组，而不是只分四类。
- 同一收藏品可以在多个来源组重复展示，但底层数据只保存一份。
- 以悠悠有品名称和最低在售价为主。
- 每15分钟采集原始价格，首页每小时刷新。
- 只显示普通、非纪念品、非 StatTrak 的目标枪皮。
- 枪皮主范围为隐秘级，磨损只看崭新出厂和略有磨损。
- 刀具和手套也只看崭新、略磨；按刀型或手套型号动态展示最贵的两个标准涂装。
- 不考虑宝石、模板、特殊浮点、贴纸和人工溢价。
- 武器箱本身也有价格、K线、供应状态和事件影响。
- 详情页支持小时、4小时、日、周K线及历史事件竖线。
- 2021年前允许展示 BUFF、C5、IGXE、5E 或经批准旧平台参考线；禁止 Steam。
- 外部参考线不得与悠悠主K线拼接。
- 无法补回的关机数据必须留空。
- 最终交付 Windows 桌面入口、托盘服务、本地网页和 SQLite 数据库。
- 运行时不调用任何 AI API。

## 文档导航

- `AGENTS.md`：Codex 必须遵守的仓库级规则
- `CODEX_START_PROMPT.md`：第一条可直接粘贴给 Codex 的任务
- `docs/PRODUCT_SPEC.md`：完整产品需求
- `docs/DECISIONS.md`：已经确认的产品决策
- `docs/ARCHITECTURE.md`：建议技术架构
- `docs/DATA_MODEL.md`：数据库模型
- `docs/DATA_SOURCE_POLICY.md`：数据源和价格口径
- `docs/TAXONOMY_RESEARCH_PLAN.md`：收藏品完整分类研究计划
- `docs/UI_SPEC.md`：页面与交互规范
- `docs/ROADMAP.md`：分阶段开发路线
- `docs/ACCEPTANCE_TESTS.md`：验收标准
- `docs/STORAGE_AND_BACKUP.md`：数据保留与备份规则
- `docs/OPEN_QUESTIONS.md`：少数可配置的待验证细节
- `codex-prompts/`：各阶段可直接交给 Codex 的任务提示词
