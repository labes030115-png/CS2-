# 数据模型

以下为逻辑模型。Codex应使用Alembic逐步实现，不要一次创建所有未来字段。

## 1. taxonomy_groups

收藏品来源分类。

- id
- code
- name_zh
- description
- display_order
- is_active
- created_at
- updated_at

示例仅作为研究种子，不代表完整分类：

- CS2武库收藏品
- 激流大行动地图系列
- 狂牙大行动系列
- 裂网大行动系列
- 早期大行动系列
- 新版比赛地图系列
- 经典Major地图收藏品
- 早期地图/常规掉落收藏品
- 早期非地图收藏品
- 独立礼包或商店型收藏品
- 武器箱系列

## 2. collections

- id
- canonical_name
- yyyp_name
- name_en
- collection_kind
- first_release_at
- current_status
- description
- primary_source_confidence
- created_at
- updated_at

## 3. collection_group_memberships

多对多；允许一个收藏品在多个来源组重复展示。

- id
- collection_id
- taxonomy_group_id
- display_order
- label_text
- label_emphasis
- is_visible
- created_at

唯一约束：`collection_id + taxonomy_group_id`。

## 4. assets

统一表示枪皮、刀、手套、武器箱。

- id
- asset_type: gun_skin / knife / glove / case
- canonical_name
- yyyp_display_name
- weapon_type
- finish_name
- wear
- rarity
- is_souvenir
- is_stattrak
- is_gem_variant
- is_template_variant
- market_hash_name
- collection_id
- active
- created_at
- updated_at

## 5. case_asset_relations

武器箱与枪皮、刀具、手套池的关联。

- id
- case_asset_id
- contained_asset_id
- relation_type: covert_drop / rare_special / other
- valid_from
- valid_to
- source_event_id
- confidence
- created_at

## 6. source_item_mappings

- id
- asset_id
- source_code
- external_item_id
- external_name
- currency
- mapping_status
- verified_at
- raw_metadata_json

唯一约束：`source_code + external_item_id`。

## 7. price_snapshots

15分钟原始快照。

- id
- asset_id
- source_code
- metric: lowest_listing / highest_buy_order
- price_minor
- currency
- observed_at_utc
- scheduled_at_utc
- listing_count
- data_quality
- is_backfilled
- raw_reference
- created_at

索引：

- asset_id, source_code, metric, observed_at_utc
- scheduled_at_utc
- data_quality

## 8. ohlc_bars

- id
- asset_id
- source_code
- metric
- timeframe: 1h / 1d
- bucket_start_utc
- open_minor
- high_minor
- low_minor
- close_minor
- sample_count
- expected_count
- is_complete
- has_gap
- source_resolution
- created_at
- updated_at

4h和1w默认动态生成，不永久保存。

## 9. events

- id
- event_type
- title
- summary
- announced_at_utc
- effective_at_utc
- original_timezone
- confidence
- created_at
- updated_at

## 10. event_targets

事件可关联收藏品、资产、武器箱或分类。

- id
- event_id
- target_type
- target_id
- impact_role
- created_at

## 11. event_sources

- id
- event_id
- source_title
- source_url
- publisher
- source_kind
- accessed_at
- confidence
- notes

## 12. event_impact_metrics

- id
- event_id
- asset_id
- source_code
- baseline_price_minor
- change_24h
- change_7d
- change_30d
- change_90d
- max_gain
- max_drawdown
- completeness
- calculated_at

## 13. external_historical_series

用于2021年前或悠悠缺失期的独立参考线。

- id
- asset_id
- source_code
- metric
- currency
- resolution
- starts_at
- ends_at
- import_batch_id
- provenance
- confidence
- created_at

实际价格点可复用price_snapshots或单独建表，需根据导入规模评估。

## 14. manual_overrides

- id
- entity_type
- entity_id
- field_name
- original_value_json
- override_value_json
- reason
- created_at
- updated_at

## 15. user_ui_state

- id
- key
- value_json
- updated_at

用于记忆展开状态、列宽、筛选和排序。

## 16. collector_runs

- id
- job_type
- source_code
- started_at
- finished_at
- status
- requested_count
- success_count
- failure_count
- error_summary
- log_reference

## 17. gaps

- id
- asset_id
- source_code
- metric
- starts_at
- ends_at
- cause
- recovery_status
- last_attempt_at
- created_at
- updated_at

## 18. backups

- id
- file_path
- backup_type
- size_bytes
- created_at
- verified_at
- status

## 19. 通知预留表

第一版只建迁移或接口，不实际发送：

- alert_rules
- alert_events
- notification_queue
- notification_deliveries

必须包含触发时间、发现时间、补发时间和去重键。
