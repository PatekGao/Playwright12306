# 批量实时查询 CLI

这个脚本用于从 Excel 批量读取城市对或站点对，并逐行调用现有实时查询能力。

脚本路径：`scripts/batch_query_realtime_tickets.py`

示例 Excel：`docs/examples/realtime_batch_template.xlsx`

## 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Excel 列说明

工作表默认名为 `queries`。

推荐列：

- `enabled`: 是否执行当前行，留空或 `Y/YES/TRUE/1` 表示执行，`N/NO/FALSE/0` 表示跳过
- `date`: 单日查询，格式 `YYYY-MM-DD`
- `date_from`: 起始日期，做日期范围查询时使用
- `date_to`: 结束日期，做日期范围查询时使用
- `query_scope`: `city` 或 `station`
- `from_station_name`: 出发城市或站点
- `to_station_name`: 到达城市或站点
- `train_code`: 可选，精确车次过滤
- `train_class_name`: 可选，车次类型过滤，例如 `高速`
- `note`: 备注列，仅用于人工识别

规则：

- `date` 与 `date_from/date_to` 二选一
- 批量脚本当前按行执行，每一行仍然遵循现有实时查询限制
- 日期跨度仍然最多 `7` 天
- 结果是否成功仍受 12306 上游风控影响

## 运行方式

```bash
python3 scripts/batch_query_realtime_tickets.py \
  --input-xlsx docs/examples/realtime_batch_template.xlsx \
  --output-dir output/realtime-batch-demo
```

如果你的工作表名不是 `queries`，可以显式指定：

```bash
python3 scripts/batch_query_realtime_tickets.py \
  --input-xlsx /path/to/your.xlsx \
  --sheet-name queries \
  --output-dir output/realtime-batch-demo
```

## 输出内容

运行完成后，输出目录中会包含：

- `batch_summary.csv`: 便于脚本处理的批量汇总
- `batch_summary.xlsx`: 便于直接在 Excel 里查看的批量汇总
- `details/*.json`: 每个成功查询一份完整原始结果

其中汇总表会标出：

- `completed`: 当前行执行成功
- `skipped`: 当前行被 `enabled` 禁用
- `failed`: 当前行参数非法或查询失败

## 一个最小 Excel 示例

| enabled | date       | query_scope | from_station_name | to_station_name | train_class_name | note |
|---------|------------|-------------|-------------------|-----------------|------------------|------|
| Y       | 2026-03-18 | city        | 上海              | 北京            |                  | 单日城市对 |
| Y       |            | city        | 杭州              | 上海            | 高速             | 日期范围城市对 |

第二行需要同时填写：

- `date_from=2026-03-18`
- `date_to=2026-03-20`

## 退出码

- `0`: 所有已执行行都成功
- `1`: 至少一行执行失败
