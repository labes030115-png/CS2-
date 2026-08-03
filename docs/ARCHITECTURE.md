# 建议架构

## 1. 总体结构

```text
Windows Desktop Launcher / Tray
          │
          ├── starts/stops
          ▼
FastAPI Local Backend ───── SQLite
          │                    │
          ├── Scheduler        ├── raw snapshots
          ├── Source adapters  ├── OHLC
          ├── Gap recovery     ├── events
          ├── Aggregation      ├── taxonomy
          ├── Backup           └── overrides
          │
          ▼
React + TypeScript Local Dashboard
```

## 2. 推荐目录

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
      collectors/
      aggregation/
      gaps/
      backups/
      taxonomy/
    sources/
      base.py
      csqaq.py
      c5.py
      file_import.py
      mock.py
    main.py
  alembic/
  tests/

frontend/
  src/
    pages/
    components/
    features/
      dashboard/
      item-detail/
      comparisons/
      taxonomy/
      admin/
    api/
    state/
  tests/

desktop/
  launcher/
  tray/
  packaging/

scripts/
  dev.ps1
  test.ps1
  build_windows.ps1
  backup.ps1

research/
  samples/
  source-reports/
  taxonomy/
```

## 3. 本地后端

- 监听 `127.0.0.1`，端口可配置。
- 提供健康检查、采集状态、缺口状态和本地数据API。
- 静态前端可由 FastAPI 提供，减少安装后运行进程数量。
- 生产打包时，桌面启动器负责查找空闲端口并打开浏览器。

## 4. 数据源适配器

统一接口示例：

```python
class PriceSourceAdapter(Protocol):
    source_code: str

    async def health_check(self) -> SourceHealth: ...
    async def fetch_catalog(self) -> list[SourceItem]: ...
    async def fetch_current_prices(
        self, external_ids: list[str]
    ) -> list[CurrentPrice]: ...
    async def fetch_historical_points(
        self, external_id: str, start: datetime, end: datetime
    ) -> list[HistoricalPoint]: ...
```

每个返回值必须包含：

- source
- source_item_id
- observed_at
- currency
- metric
- value
- resolution
- completeness
- raw_reference

## 5. 调度

- 每15分钟触发采集。
- 使用“计划时间”而不是“程序实际执行时间”作为周期归属依据。
- 单次任务加互斥锁，避免重叠。
- 网络错误使用指数退避，但不超过下一周期。
- 每次启动先执行缺口分析。
- 缺口补回和实时采集使用不同任务队列。
- API频率限制必须由适配器显式控制。

## 6. OHLC聚合

15分钟快照聚合到1小时：

- Open：周期内首个有效值
- High：周期内最大有效值
- Low：周期内最小有效值
- Close：周期内最后有效值
- sample_count：实际样本数
- expected_count：预期样本数
- is_complete：是否完整
- has_gap：是否有缺口

4小时从小时线动态聚合，日线按北京时间从小时或原始点聚合，周线从日线动态聚合。

## 7. 前端

首页：

- 大类和收藏品树。
- 虚拟滚动。
- 固定表头。
- 来源标签醒目。
- 展开状态保存在本地设置表或浏览器本地存储。
- 多分类展示共享同一个资产ID。

详情页：

- 蜡烛图。
- 外部参考线。
- 事件标线。
- 完整度提示。
- 来源切换。
- 指标面板。

## 8. 桌面打包

- PySide6 托盘应用。
- 后台启动 FastAPI 子进程。
- 等待健康检查通过后打开浏览器。
- Windows Credential Manager 通过 `keyring` 存储Token。
- PyInstaller 生成目录型发行包，稳定后再评估单文件EXE。
- 使用安装器创建桌面快捷方式。
- 卸载时询问是否保留SQLite数据库和备份。

## 9. 可观测性

- 结构化日志。
- 日志按日期轮转。
- 默认保留30天。
- Token和Cookie自动脱敏。
- 设置页显示：
  - 最后成功采集时间
  - 下次采集时间
  - API健康
  - 待补缺口
  - 数据库大小
  - 备份大小
  - 最近错误
