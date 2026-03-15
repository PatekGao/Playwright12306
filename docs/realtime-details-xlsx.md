# 实时详情 JSON 导出 XLSX

这个工具把 `details/*.json` 转成更适合查看的 Excel 工作簿。

脚本路径：`scripts/export_realtime_details_xlsx.py`

## 适用场景

- 你已经跑完批量实时查询
- 输出目录里已经有 `details/*.json`
- 你想把每个 JSON 转成结构清晰的 `.xlsx`

## 运行单个 JSON

```bash
python3 scripts/export_realtime_details_xlsx.py \
  --input output/realtime_batch_Shanghai/details/row-002_上海_北京.json \
  --output-dir output/realtime_detail_xlsx
```

## 批量转换整个 details 目录

```bash
python3 scripts/export_realtime_details_xlsx.py \
  --input output/realtime_batch_Shanghai/details \
  --output-dir output/realtime_detail_xlsx
```

## 输出说明

每个 JSON 会生成一个同名 `.xlsx`，例如：

- `row-002_上海_北京.json`
- `row-002_上海_北京.xlsx`

每个工作簿会包含这些工作表：

- `overview`: 最常看的总览字段
- `request`: 原始请求参数
- `summary`: 顶层汇总
- `partial_failures`: 部分失败信息
- `aggregated_results`: 按车次聚合结果
- `daily_summaries`: 按天汇总
- `daily_items`: 每天每条车次结果
- `seat_offers`: 所有席别明细
- `json_tree`: 把整个 JSON 展开成 `path -> value`
- `raw_json`: 完整原始 JSON 文本逐行保存

这两个工作表保证不遗漏信息：

- `json_tree`
- `raw_json`

也就是说，就算将来 JSON 结构增加新字段，只要在文件里存在，导出的 Excel 里也能从完整原始内容看见。
