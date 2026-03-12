# Playwright12306

用于抓取 `12306` 指定某一天的全国可售车次基础信息、时刻表和价格信息的本地脚本项目。

当前仓库已经实现的是一个 `纯 HTTP 客户端` MVP：
- 用 `queryTrainInfo/getTrainName` 获取当天全国车次种子
- 用 `queryTrainInfo/query` 获取单车次时刻表
- 用 `leftTicket/init + leftTicket/queryG` 获取价格来源数据
- 将原始响应和标准化结果落盘到本地 `artifacts/`
- 支持把 `artifacts/<date>/normalized` 导入本地 `SQLite`
- 提供 `FastAPI + Vue 3` 的本地检索工具，支持结构化筛选、详情查看和导出

注意：仓库名里有 `Playwright`，但当前实现并不依赖 Playwright 浏览器自动化；这是此前方案收敛后保留的项目名。现阶段价格层已实现，`余票/可售状态` 仅作为可选附带字段，不保证完整。

## 当前能力

已实现：
- 按日期抓取全国车次种子
- 抓取单车次完整经停时刻表
- 解析 `leftTicket/queryG` 的价格编码，输出结构化 `seat_price_json`
- 保存原始响应，便于后续复查和二次清洗
- 保存断点状态，支持中断后继续跑
- 为核心解析逻辑提供 `pytest` 测试

当前不保证：
- 不保证全国所有车次都能命中价格快照
- 不保证 `sale_status`、`can_web_buy`、`seat_inventory_json` 全量可用
- 不包含 Playwright 浏览器态获取、验证码处理、登录态管理

## 项目结构

```text
src/playwright12306/        核心实现
scripts/fetch_national_trains.py
scripts/import_artifacts_to_db.py
scripts/run_query_api.py
tests/                      自动化测试
web/                        Vue 3 前端
docs/plans/                 设计与实现计划
artifacts/                  运行产物，不建议提交
data/                       本地 SQLite 数据库（运行时生成）
```

关键模块：
- `src/playwright12306/train_seed.py`: 车次种子抓取与解析
- `src/playwright12306/train_info.py`: 时刻表抓取与解析
- `src/playwright12306/left_ticket.py`: 区间价格来源抓取与解析
- `src/playwright12306/price_parser.py`: `infoAll_list` 价格编码解析
- `src/playwright12306/pipeline.py`: 端到端流程编排

## 安装

先安装 Python 依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

再安装前端依赖：

```bash
cd web
npm install
cd ..
```

## 快速开始

先做一次干跑，确认参数和产物目录：

```bash
python3 scripts/fetch_national_trains.py --query-date 2026-03-20 --dry-run
```

抓取少量样本做验证：

```bash
python3 scripts/fetch_national_trains.py --query-date 2026-03-20 --limit-trains 5
```

跑完整日期：

```bash
python3 scripts/fetch_national_trains.py --query-date 2026-03-20
```

CLI 参数：

```bash
python3 scripts/fetch_national_trains.py --help
```

- `--query-date`: 必填，格式 `YYYY-MM-DD`
- `--dry-run`: 只打印执行计划，不发网络请求
- `--limit-trains`: 仅抓前 N 条车次种子，适合快速验收
- `--artifacts-dir`: 自定义输出目录，原始数据、标准化结果和断点状态都会写到这里

## 本地检索工具

如果你已经完成全量爬取，并且数据在 [artifacts/2026-03-18](/Users/steve/PycharmProjects/Playwright12306/artifacts/2026-03-18)，建议按下面顺序启动本地检索工具。

### 1. 导入到 SQLite

```bash
python3 scripts/import_artifacts_to_db.py \
  --artifacts-dir artifacts/2026-03-18 \
  --db-path data/train_search.db
```

默认会：
- 读取 `normalized/trains.csv`
- 读取 `normalized/stops.csv`
- 读取 `normalized/routes.csv`
- 解析 `seat_price_json` 到独立 `seat_prices` 表
- 生成本地数据库 [train_search.db](/Users/steve/PycharmProjects/Playwright12306/data/train_search.db)

### 2. 启动本地 API

```bash
python3 scripts/run_query_api.py \
  --db-path data/train_search.db \
  --host 127.0.0.1 \
  --port 8000
```

启动后可用接口包括：
- `GET /api/meta/summary`
- `GET /api/meta/options`
- `GET /api/trains`
- `GET /api/trains/{query_date}/{train_no}`
- `GET /api/trains/export`

### 3. 启动 Vue 前端

```bash
cd web
npm run dev
```

默认访问地址：
- `http://127.0.0.1:5173`

前端能力包括：
- 概览页
- 结构化筛选
- 结果表格排序/分页
- 右侧详情抽屉
- 当前筛选结果导出 CSV / JSON

如果你只想产出前端静态构建：

```bash
cd web
npm run build
```

## 输出结果

运行后默认写到 [artifacts](/Users/steve/PycharmProjects/Playwright12306/artifacts)：

如果你想按日期分目录保存，可以直接指定：

```bash
python3 scripts/fetch_national_trains.py \
  --query-date 2026-03-18 \
  --artifacts-dir artifacts/2026-03-18
```

### 原始数据

- [artifacts/raw/get_train_name.jsonl](/Users/steve/PycharmProjects/Playwright12306/artifacts/raw/get_train_name.jsonl)
- [artifacts/raw/query_train_info/](/Users/steve/PycharmProjects/Playwright12306/artifacts/raw/query_train_info)
- [artifacts/raw/left_ticket/](/Users/steve/PycharmProjects/Playwright12306/artifacts/raw/left_ticket)

这些文件保留原始接口响应，适合做排错、字段回溯和二次清洗。

### 标准化数据

- [artifacts/normalized/trains.csv](/Users/steve/PycharmProjects/Playwright12306/artifacts/normalized/trains.csv)
- [artifacts/normalized/trains.jsonl](/Users/steve/PycharmProjects/Playwright12306/artifacts/normalized/trains.jsonl)
- [artifacts/normalized/stops.csv](/Users/steve/PycharmProjects/Playwright12306/artifacts/normalized/stops.csv)
- [artifacts/normalized/routes.csv](/Users/steve/PycharmProjects/Playwright12306/artifacts/normalized/routes.csv)

其中：
- `trains.csv`: 一车次一行，包含车次摘要、区间编码、结构化价格等
- `trains.jsonl`: 与 `trains.csv` 同粒度，一行一个 JSON 对象，更适合脚本消费、流式处理和后续入库
- `stops.csv`: 一停站一行
- `routes.csv`: 实际查询过的区间及命中结果数量

`trains.csv` 的核心字段包括：
- `query_date`
- `train_no`
- `train_code`
- `station_train_code`
- `train_class_name`
- `start_station_name`
- `end_station_name`
- `depart_time`
- `arrive_time`
- `duration`
- `arrive_day_diff`
- `from_station_code`
- `to_station_code`
- `seat_price_json`

其中：
- `train_code`: 面向使用者的车次号，比如 `G5`、`1461`
- `station_train_code`: 与 `train_code` 保持一致的兼容别名，供旧脚本继续使用

`trains.jsonl` 当前与 `trains.csv` 保持同一套字段，常见字段包括：
- `query_date`
- `train_no`
- `train_code`
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
- `sale_status`
- `can_web_buy`
- `seat_inventory_json`

`seat_price_json` 形如：

```json
[
  {"code": "O", "name": "二等座", "price": "669.3"},
  {"code": "M", "name": "一等座", "price": "1070.0"}
]
```

## 断点续跑与错误日志

状态文件位于 [artifacts/state](/Users/steve/PycharmProjects/Playwright12306/artifacts/state)：

- `train_info_done.txt`: 已完成的 `train_no`
- `left_ticket_done.txt`: 已完成的区间键，如 `BJP_SHH`
- `errors.jsonl`: 运行期错误日志

这意味着：
- 中途失败后可以直接重跑同一日期
- 已落盘的车次详情和区间查询会被跳过
- 若你需要强制全量重抓，当前版本需要手动清理对应 `artifacts/` 状态文件

## 测试

运行测试：

```bash
pytest tests -q
```

前端测试：

```bash
cd web
npm test
```

前端构建验证：

```bash
cd web
npm run build
```

当前测试覆盖的重点包括：
- 日期参数解析
- 脚本入口干跑
- 站点映射解析
- 车次种子去重
- 时刻表解析
- `leftTicket` 行解析
- 价格编码解析
- 断点续跑辅助逻辑
- SQLite 导入
- 查询 API
- 前端 URL 参数同步
- 结果表格与详情抽屉渲染

## 已知限制

1. 价格是通过区间查询命中的车次快照推导出来的，不是 12306 官方独立“全国统一票价表”。
2. 如果某车次没有在当前查询区间命中，`seat_price_json` 可能为空。
3. `sale_status`、`can_web_buy`、`seat_inventory_json` 目前不是验收硬指标。
4. 当前实现默认串行请求；全国完整抓取时，耗时和接口稳定性会受网络环境影响。
5. 当前没有封装命令行参数来强制重抓或自定义输出目录，需要修改代码配置或清理 `artifacts/`。

## 后续可扩展方向

- 增加重试、退避和更稳的限流
- 提高区间命中率，补更多车次的价格快照
- 增加 `force`、`artifacts-dir` 等 CLI 参数
- 增加 Playwright 浏览器引导层，在接口失效时获取更稳的会话态

## 参考文档

- [2026-03-06-12306-national-trains-design.md](/Users/steve/PycharmProjects/Playwright12306/docs/plans/2026-03-06-12306-national-trains-design.md)
- [2026-03-06-12306-national-trains-plan.md](/Users/steve/PycharmProjects/Playwright12306/docs/plans/2026-03-06-12306-national-trains-plan.md)
