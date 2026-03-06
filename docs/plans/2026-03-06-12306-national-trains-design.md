# 12306 National Trains Pure HTTP Design

## Goal

为指定日期抓取 12306 当天全国车次与结构化价格，并尽量保留页面可见的高价值字段。

## Scope

- 输入一个 `query_date`
- 输出当天全国车次、经停站、结构化价格
- 余票状态与可售状态作为可选增强，不是硬性目标
- 结果全部固化到本地文件，包含原始响应与标准化结果
- 不登录，不下单，不进行不可逆操作

## Non-goals

- 不做抢票或自动预订
- 不做长期定时调度
- 不做跨多日历史回补
- 不保证绕过所有风控；重点是可维护与可恢复

## Options Considered

### Option 1: Pure DOM scraping

通过 Playwright 打开查询页，读取页面表格。

优点：
- 直观
- 贴近用户页面

缺点：
- 全国范围难以覆盖
- 表格字段不全
- 速度慢且脆弱

结论：不采用。

### Option 2: Playwright + captured network

先用浏览器拿请求模板，再批量复放接口。

优点：
- 稳定
- 更容易适应风控

缺点：
- 依赖浏览器会话
- 与用户选择的方案 3 不一致

结论：保留为 fallback。

### Option 3: Pure HTTP client

直接调用页面当前使用的公开接口与静态资源。

优点：
- 运行快
- 资源消耗低
- 易于脚本化和断点续跑

缺点：
- 对接口变化敏感
- 需要自己管理 cookies、限流、重试与字段解析

结论：采用。

## Verified Endpoints

以下接口在 2026-03-06 已实测可达：

1. `GET /otn/queryTrainInfo/getTrainName?date=YYYY-MM-DD`
   - 返回当天全国车次种子集
   - 关键字段：`station_train_code`、`train_no`

2. `GET /otn/queryTrainInfo/query`
   - 参数：
     - `leftTicketDTO.train_no`
     - `leftTicketDTO.train_date`
     - `rand_code`
   - 返回单车次时刻表详情

3. `GET /otn/leftTicket/init?linktypeid=dc`
   - 用于建立查询会话

4. `GET /otn/leftTicket/queryG`
   - 需要先访问 `leftTicket/init`
   - 返回区间余票、可售状态、价格编码、站码映射

5. `GET /otn/resources/js/framework/station_name.js`
   - 返回全量站名站码映射

## Architecture

程序采用四层结构：

### 1. Bootstrap Layer

职责：
- 初始化 `requests.Session`
- 访问 `leftTicket/init` 建立 cookies
- 下载并解析 `station_name.js`
- 统一 User-Agent、Referer、超时、重试策略

输出：
- 可复用 HTTP session
- station code map

### 2. Discovery Layer

职责：
- 调用 `queryTrainInfo/getTrainName`
- 生成当天全国车次种子清单

输出记录：
- `query_date`
- `station_train_code`
- `train_no`

说明：
- 这是全国车次种子集来源
- 不依赖过期的 `train_list.js`

### 3. Schedule Layer

职责：
- 对每个 `train_no` 调用 `queryTrainInfo/query`
- 获取始发/终到、经停站、时刻、历时、到达日偏移

输出：
- 车次主记录
- 停站明细记录

### 4. Price Layer / Optional Sale Snapshot Layer

职责：
- 按区间调用 `leftTicket/queryG`
- 获取席别编码、价格编码
- 如接口返回稳定，再顺手记录余票状态和是否可售
- 解析 `infoAll_list` 到结构化 `seatList`

说明：
- 12306 的价格以及可售快照都是 `日期 + 区间` 维度，不是纯车次维度
- 价格层是必做项
- 余票与可售快照仅在命中且字段稳定时写入主表

## Nationwide Coverage Strategy

### Seed generation

当天全国车次使用 `getTrainName(query_date)` 获取，不做站点两两爆破。

### Route coverage

为了获得价格，并在可选情况下补充余票/可售状态，需要设计区间扫描策略：

1. 从时刻表详情中取每个车次的首站和末站，优先扫描完整区间
2. 对完整区间查询不到的车次，再用热门中间站补扫
3. 若仍未命中，则保留该车次的时刻表记录，价格与可售字段为空

MVP 先做第 1 步，只保证：
- 全国车次种子齐全
- 时刻表齐全
- 能命中大部分首末站价格快照

增强版再补第 2 步、命中率统计，以及余票/可售状态覆盖率优化。

## Data Model

输出分为 `raw` 和 `normalized` 两层。

### Raw files

- `artifacts/raw/get_train_name.jsonl`
- `artifacts/raw/query_train_info/<train_no>.json`
- `artifacts/raw/left_ticket/<route_key>.json`

每个原始文件都要附带：
- `query_date`
- `fetched_at`
- `endpoint`
- `request_params`
- `response_body`

### Normalized files

- `artifacts/normalized/trains.csv`
- `artifacts/normalized/stops.csv`
- `artifacts/normalized/routes.csv`
- `artifacts/normalized/trains.jsonl`

`trains.csv` 建议字段：

- `query_date`
- `train_no`
- `station_train_code`
- `train_class_name`
- `start_station_name`
- `end_station_name`
- `from_station_name`
- `to_station_name`
- `depart_time`
- `arrive_time`
- `duration`
- `arrive_day_diff`
- `from_station_code`
- `to_station_code`
- `seat_price_json`
- `stop_count`
- `route_signature`
- `sale_status` (optional)
- `can_web_buy` (optional)
- `seat_inventory_json` (optional)

`stops.csv` 建议字段：

- `query_date`
- `train_no`
- `station_train_code`
- `station_no`
- `station_name`
- `arrive_time`
- `start_time`
- `running_time`
- `arrive_day_diff`
- `is_start`
- `is_end`

`routes.csv` 建议字段：

- `query_date`
- `from_station_code`
- `to_station_code`
- `result_count`
- `fetched_at`

## Price Parsing

不额外猜价格规则，直接复用 12306 票价页当前前端逻辑：

- 余票接口中的 `infoAll_list` 包含席别价格编码
- 页面前端会将其解析为 `queryLeftNewDTO.seatList`
- 程序复制该解析逻辑，生成结构化席别价格

优势：
- 与站点展示口径一致
- 避免自创席别映射

## Error Handling

必须显式处理：

- 无效日期
- 空车次列表
- 接口返回 HTML 错误页而非 JSON
- 接口返回 `status=false`
- 字段缺失
- 某车次详情为空
- 某区间余票接口被限流或超时

错误策略：

- 单个车次失败写错误日志并继续
- 单个区间失败重试后继续
- 全局任务保留进度文件，允许恢复

## Rate Limit and Retry

默认策略：

- `queryTrainInfo/getTrainName`: 单次请求
- `queryTrainInfo/query`: 并发 3
- `leftTicket/queryG`: 并发 2
- 超时 20 秒
- 指数退避重试 3 次
- 429、5xx、网络错误可重试
- 连续失败达到阈值时自动降并发

原因：
- 余票接口更敏感
- 先保守跑通，再考虑提速

## Checkpoint and Resume

需要本地状态文件：

- `artifacts/state/train_info_done.txt`
- `artifacts/state/left_ticket_done.txt`
- `artifacts/state/errors.jsonl`

恢复规则：

- 已完成车次不重复拉取详情
- 已完成区间不重复拉取余票
- 可通过 `--force` 重新抓取

## Project Layout

建议新建：

- `src/playwright12306/`
- `scripts/`
- `tests/`
- `artifacts/`

推荐模块：

- `src/playwright12306/config.py`
- `src/playwright12306/http_client.py`
- `src/playwright12306/stations.py`
- `src/playwright12306/train_seed.py`
- `src/playwright12306/train_info.py`
- `src/playwright12306/left_ticket.py`
- `src/playwright12306/price_parser.py`
- `src/playwright12306/pipeline.py`
- `src/playwright12306/models.py`

入口脚本：

- `scripts/fetch_national_trains.py`

## Testing Strategy

测试不直连 12306，优先使用固定夹具。

需要覆盖：

1. `station_name.js` 解析
2. `getTrainName` 响应解析
3. `queryTrainInfo/query` 响应归一化
4. `leftTicket/queryG` 单行解析
5. `infoAll_list` 价格解析
6. 断点续跑与去重

测试文件建议：

- `tests/test_stations.py`
- `tests/test_train_seed.py`
- `tests/test_train_info.py`
- `tests/test_left_ticket.py`
- `tests/test_price_parser.py`
- `tests/test_pipeline_resume.py`

## Risks

1. 12306 接口字段随时可能变
2. `leftTicket/queryG` 更容易出现风控或错误页
3. 价格与可售状态都依赖区间命中，不是纯车次静态属性
4. 仅靠首末站区间查询，可能漏掉部分仅区间售卖的价格/可售快照

## MVP Definition

MVP 目标：

- 输入日期
- 拉取全国车次种子
- 拉取所有车次时刻表详情
- 用首末站区间抓价格快照
- 解析结构化价格与席别
- 输出 `trains.csv`、`stops.csv`、原始响应

MVP 不做：

- 区间命中率优化
- 余票/可售状态覆盖率优化
- 多轮补扫
- 数据库存储
- 自动调度

## Fallback Plan

如果后续纯 HTTP 方案失效，保留降级路径：

- 使用 Playwright 先建立浏览器会话
- 把 cookies/headers 注入同一套 HTTP client
- 其余数据处理逻辑完全复用

这样不会推翻当前架构。
