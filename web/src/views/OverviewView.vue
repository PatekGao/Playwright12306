<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { computed } from "vue";
import { RouterLink } from "vue-router";

import SummaryCard from "@/components/SummaryCard.vue";
import { fetchMetaSummary } from "@/lib/api";

const { data, isLoading, isError } = useQuery({
  queryKey: ["meta-summary"],
  queryFn: () => fetchMetaSummary(),
});

const latestDate = computed(() => data.value?.query_dates?.[0] ?? "");
</script>

<template>
  <main class="page page-overview">
    <section class="hero glass-card">
      <p class="eyebrow">12306 Query Studio</p>
      <h1>把全量爬取数据变成顺手的本地检索工具</h1>
      <p class="hero-copy">
        基于本地 SQLite 与 Vue 界面，快速筛选车次、查看停站、核对价格快照，并导出当前结果集。
      </p>
      <RouterLink class="primary-button" :to="{ name: 'search', query: latestDate ? { query_date: latestDate } : {} }">
        进入检索
      </RouterLink>
    </section>

    <section class="summary-grid" v-if="!isLoading && data">
      <SummaryCard label="已导入日期" :value="data.query_dates.length" :hint="data.query_dates.join(' · ')" />
      <SummaryCard label="总车次" :value="data.total_trains.toLocaleString('zh-CN')" />
      <SummaryCard label="总停站" :value="data.total_stops.toLocaleString('zh-CN')" />
      <SummaryCard label="最新导入" :value="data.latest_imported_at ?? '--'" />
    </section>

    <section v-else-if="isLoading" class="status-card glass-card">正在加载概览…</section>
    <section v-else-if="isError" class="status-card glass-card">无法连接后端 API，请先启动查询服务。</section>
  </main>
</template>
