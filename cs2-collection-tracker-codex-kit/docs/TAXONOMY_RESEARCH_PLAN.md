# 收藏品完整分类研究计划

## 1. 目标

建立完整、可追溯、可人工修正的收藏品分类体系。不能把产品限制为四个固定大类，也不能仅根据当前获取方式分类。

## 2. 分类原则

收藏品具有多重身份，采用“多对多来源组＋事件时间线”模型。

每个收藏品至少研究：

- 首次推出日期
- 推出公告
- 所属行动
- 所属地图
- 是否成为Major地图收藏品
- 是否存在纪念品版本
- 普通版获取方式
- 是否进入过每周掉落
- 是否通过武库点数兑换
- 是否通过商店或礼包获取
- 是否停止供应
- 当前状态
- 隐秘级枪皮
- 与武器箱或容器的关系

## 3. 初始研究维度

以下是研究维度，不是最终封闭分类：

- CS2武库直兑收藏品
- 当前武库收藏品
- 已退出武库收藏品
- 激流大行动地图系列
- 狂牙大行动系列
- 裂网大行动系列
- 血猎及更早期行动系列
- 新版比赛地图收藏品
- 经典Major地图收藏品
- 早期地图收藏品
- 常规/每周掉落收藏品
- 早期非地图收藏品
- 独立礼包或商店型收藏品
- 常规武器箱
- 大行动武器箱
- 电竞武器箱
- 活跃掉落武器箱
- 稀有掉落武器箱
- 无新增产出渠道的容器
- 刀具特殊稀有池
- 手套特殊稀有池

## 4. 资料优先级

1. Valve / Counter-Strike 官方更新公告
2. 官方赛事、Major、地图池和行动资料
3. 可靠百科、数据库和专业资料站
4. 论坛、视频和个人文章，仅作线索

每条结论必须保存来源URL、访问日期和可信度。

## 5. 研究输出

### `research/taxonomy/collections.csv`

建议字段：

- canonical_name
- yyyp_name
- name_en
- first_release_date
- current_status
- group_codes
- has_covert
- has_souvenir
- normal_acquisition
- notes
- source_urls
- confidence

### `research/taxonomy/events.csv`

- target
- event_type
- title
- announced_at
- effective_at
- original_timezone
- source_url
- confidence
- notes

### `research/taxonomy/case_relations.csv`

- case_name
- asset_name
- relation_type
- valid_from
- valid_to
- source_url
- confidence

## 6. 去重与重复展示

- 收藏品实体只建一条。
- 分类归属使用多对多关系。
- 同一资产只建一条。
- 首页可在多个分类重复展示同一收藏品。
- 重复展示共享价格和K线。

## 7. 第一轮验证范围

- 蔓藤纹收藏品
- 狂牙大行动：远古、控制、浩劫
- 一个经典Major地图收藏品
- 一个包含刀具特殊稀有池的武器箱
- 一个包含手套特殊稀有池的武器箱

研究阶段应选择关联关系清晰、资料来源稳定、能覆盖关键数据模型的两个武器箱。
