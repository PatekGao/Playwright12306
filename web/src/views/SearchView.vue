<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import DetailDrawer from "@/components/DetailDrawer.vue";
import ResultsTable from "@/components/ResultsTable.vue";
import SummaryCard from "@/components/SummaryCard.vue";
import { buildApiUrl, fetchMetaOptions, fetchTrainDetail, fetchTrains } from "@/lib/api";
import {
  DEFAULT_FILTERS,
  buildExportUrl,
  buildSearchQuery,
  mergeFilters,
  parseSearchFilters,
} from "@/lib/searchFilters";
import { useUiStore } from "@/stores/ui";
import type {
  MetaOptions,
  SearchFilters,
  SortBy,
  TrainDetailResponse,
  TrainListItem,
  TrainListResponse,
} from "@/types";

const route = useRoute();
const router = useRouter();
const uiStore = useUiStore();
const { isDrawerOpen } = storeToRefs(uiStore);
const selected = ref<{ queryDate: string; trainNo: string } | null>(null);

const filters = computed<SearchFilters>(() => parseSearchFilters(route.query));
const emptyOptions: MetaOptions = {
  query_dates: [],
  train_classes: [],
  stations: [],
  seat_names: [],
};
const emptyTrains: TrainListResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
  summary: {
    total_trains: 0,
    matched_prices: 0,
    min_price: null,
    max_price: null,
  },
};

const optionsQuery = useQuery({
  queryKey: ["meta-options"],
  queryFn: () => fetchMetaOptions(),
});
const options = computed<MetaOptions>(() => optionsQuery.data.value ?? emptyOptions);

watch(
  () => options.value.query_dates,
  (queryDates) => {
    if (!queryDates?.length || filters.value.query_date) {
      return;
    }
    router.replace({
      query: buildSearchQuery({
        ...DEFAULT_FILTERS,
        query_date: queryDates[0],
      }),
    });
  },
  { immediate: true },
);

const trainsQuery = useQuery({
  queryKey: computed(() => ["trains", filters.value]),
  queryFn: () => fetchTrains(filters.value),
  enabled: computed(() => Boolean(filters.value.query_date)),
});
const trainsResponse = computed<TrainListResponse>(() => trainsQuery.data.value ?? emptyTrains);

const detailQuery = useQuery({
  queryKey: computed(() => ["train-detail", selected.value]),
  queryFn: () => fetchTrainDetail(selected.value!.queryDate, selected.value!.trainNo),
  enabled: computed(() => Boolean(selected.value)),
});
const detailResponse = computed<TrainDetailResponse | null>(() => detailQuery.data.value ?? null);
const detailLoading = computed<boolean>(() => detailQuery.isLoading.value);
const trainsError = computed<boolean>(() => trainsQuery.isError.value);
const trainsLoading = computed<boolean>(() => trainsQuery.isLoading.value);
const trainsErrorMessage = computed<string>(() => {
  const error = trainsQuery.error.value;
  if (!error) {
    return "无法加载结果，请确认后端服务已启动。";
  }
  return error instanceof Error ? error.message : "无法加载结果，请确认后端服务已启动。";
});

const exportBaseUrl = buildApiUrl("/api/trains/export");
const exportCsvUrl = computed(() => buildExportUrl(exportBaseUrl, filters.value, "csv"));
const exportJsonUrl = computed(() => buildExportUrl(exportBaseUrl, filters.value, "json"));

function updateFilters(patch: Partial<SearchFilters>): void {
  const next = mergeFilters(filters.value, patch);
  router.replace({ query: buildSearchQuery(next) });
}

function onSort(sortBy: SortBy): void {
  const sortOrder =
    filters.value.sort_by === sortBy && filters.value.sort_order === "asc" ? "desc" : "asc";
  updateFilters({ sort_by: sortBy, sort_order: sortOrder });
}

function onSelectTrain(item: TrainListItem): void {
  selected.value = {
    queryDate: item.query_date,
    trainNo: item.train_no,
  };
  uiStore.openDrawer();
}

function resetFilters(): void {
  router.replace({
    query: buildSearchQuery({
      ...DEFAULT_FILTERS,
      query_date: filters.value.query_date,
    }),
  });
}
</script>

<template>
  <main class="page page-search">
    <section class="search-topbar glass-card">
      <div>
        <p class="eyebrow">本地检索</p>
        <h1>12306 Query Studio</h1>
      </div>
      <div class="toolbar-actions">
        <a class="ghost-button" :href="exportJsonUrl">导出 JSON</a>
        <a class="primary-button" :href="exportCsvUrl">导出 CSV</a>
      </div>
    </section>

    <section class="search-layout">
      <div class="search-main">
        <section class="filters-panel glass-card">
          <div class="filters-header">
            <div>
              <p class="eyebrow">筛选器</p>
              <h2>结构化检索</h2>
            </div>
            <button class="ghost-button" @click="resetFilters">重置</button>
          </div>

          <div class="filters-grid">
            <label>
              <span>日期</span>
              <select :value="filters.query_date" @change="updateFilters({ query_date: ($event.target as HTMLSelectElement).value })">
                <option value="">请选择日期</option>
                <option v-for="date in options.query_dates" :key="date" :value="date">{{ date }}</option>
              </select>
            </label>
            <label>
              <span>车次号</span>
              <input :value="filters.train_code" placeholder="如 G5 / 1461" @input="updateFilters({ train_code: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>始发站</span>
              <input list="station-options" :value="filters.start_station_name" placeholder="北京" @input="updateFilters({ start_station_name: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>终到站</span>
              <input list="station-options" :value="filters.end_station_name" placeholder="上海" @input="updateFilters({ end_station_name: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>车型</span>
              <select :value="filters.train_class_name" @change="updateFilters({ train_class_name: ($event.target as HTMLSelectElement).value })">
                <option value="">全部</option>
                <option v-for="item in options.train_classes" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label>
              <span>席别</span>
              <select :value="filters.seat_name" @change="updateFilters({ seat_name: ($event.target as HTMLSelectElement).value })">
                <option value="">全部</option>
                <option v-for="item in options.seat_names" :key="item" :value="item">{{ item }}</option>
              </select>
            </label>
            <label>
              <span>最低价</span>
              <input type="number" min="0" :value="filters.min_price" @input="updateFilters({ min_price: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>最高价</span>
              <input type="number" min="0" :value="filters.max_price" @input="updateFilters({ max_price: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>售卖状态</span>
              <input :value="filters.sale_status" placeholder="预订 / 起售" @input="updateFilters({ sale_status: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>出发时间从</span>
              <input type="time" :value="filters.depart_time_from" @input="updateFilters({ depart_time_from: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>出发时间到</span>
              <input type="time" :value="filters.depart_time_to" @input="updateFilters({ depart_time_to: ($event.target as HTMLInputElement).value })" />
            </label>
            <label>
              <span>每页条数</span>
              <select :value="String(filters.page_size)" @change="updateFilters({ page_size: Number(($event.target as HTMLSelectElement).value) })">
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </label>
          </div>

          <datalist id="station-options">
            <option v-for="station in options.stations" :key="station" :value="station" />
          </datalist>
        </section>

        <section class="summary-grid compact">
          <SummaryCard label="当前结果" :value="trainsResponse.total" />
          <SummaryCard label="命中价格" :value="trainsResponse.summary.matched_prices" />
          <SummaryCard label="最低价" :value="trainsResponse.summary.min_price ? `¥${trainsResponse.summary.min_price}` : '--'" />
          <SummaryCard label="最高价" :value="trainsResponse.summary.max_price ? `¥${trainsResponse.summary.max_price}` : '--'" />
        </section>

        <section v-if="trainsError" class="status-card glass-card">{{ trainsErrorMessage }}</section>
        <section v-else-if="trainsLoading" class="status-card glass-card">正在加载检索结果…</section>
        <ResultsTable
          v-else
          :items="trainsResponse.items"
          :total="trainsResponse.total"
          :page="filters.page"
          :page-size="filters.page_size"
          :sort-by="filters.sort_by"
          :sort-order="filters.sort_order"
          @select="onSelectTrain"
          @sort="onSort"
          @page-change="(page) => updateFilters({ page })"
        />
      </div>

      <DetailDrawer
        :open="isDrawerOpen"
        :detail="detailResponse"
        :loading="detailLoading"
        @close="uiStore.closeDrawer()"
      />
    </section>
  </main>
</template>
