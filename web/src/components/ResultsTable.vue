<script setup lang="ts">
import { computed } from "vue";

import type { SortBy, SortOrder, TrainListItem } from "@/types";

const props = defineProps<{
  items: TrainListItem[];
  total: number;
  page: number;
  pageSize: number;
  sortBy: SortBy;
  sortOrder: SortOrder;
}>();

const emit = defineEmits<{
  select: [item: TrainListItem];
  sort: [sortBy: SortBy];
  pageChange: [page: number];
}>();

const headers: Array<{ key: SortBy | null; label: string }> = [
  { key: "train_code", label: "车次" },
  { key: null, label: "车型" },
  { key: null, label: "始发" },
  { key: null, label: "终到" },
  { key: "depart_time", label: "出发" },
  { key: "arrive_time", label: "到达" },
  { key: "duration", label: "历时" },
  { key: "min_price", label: "最低价" },
  { key: null, label: "价格区间" },
  { key: null, label: "售卖状态" },
];

function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `¥${value.toFixed(1)}`;
}

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)));

function toggleSort(key: SortBy | null): void {
  if (!key) return;
  emit("sort", key);
}
</script>

<template>
  <section class="results-panel glass-card">
    <div class="results-header">
      <div>
        <p class="eyebrow">检索结果</p>
        <h2>{{ total }} 条记录</h2>
      </div>
      <div class="pager">
        <button class="ghost-button" :disabled="page <= 1" @click="emit('pageChange', page - 1)">上一页</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button class="ghost-button" :disabled="page >= totalPages" @click="emit('pageChange', page + 1)">下一页</button>
      </div>
    </div>

    <div class="table-shell">
      <table class="results-table">
        <thead>
          <tr>
            <th v-for="header in headers" :key="header.label">
              <button
                v-if="header.key"
                class="sort-button"
                @click="toggleSort(header.key)"
              >
                {{ header.label }}
                <span
                  v-if="sortBy === header.key"
                  class="sort-indicator"
                >
                  {{ sortOrder === "asc" ? "↑" : "↓" }}
                </span>
              </button>
              <span v-else>{{ header.label }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in items"
            :key="`${item.query_date}-${item.train_no}`"
            class="result-row"
            @click="emit('select', item)"
          >
            <td>{{ item.train_code }}</td>
            <td>{{ item.train_class_name }}</td>
            <td>{{ item.start_station_name }}</td>
            <td>{{ item.end_station_name }}</td>
            <td>{{ item.depart_time }}</td>
            <td>{{ item.arrive_time }}</td>
            <td>{{ item.duration }}</td>
            <td>{{ formatPrice(item.min_price) }}</td>
            <td>{{ item.route_signature || "--" }}</td>
            <td>{{ item.sale_status || "--" }}</td>
          </tr>
          <tr v-if="items.length === 0">
            <td colspan="10" class="empty-row">当前筛选条件下没有结果</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
