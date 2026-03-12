<script setup lang="ts">
import { useQuery } from "@tanstack/vue-query";
import { storeToRefs } from "pinia";
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";

import RealtimeDetailDrawer from "@/components/RealtimeDetailDrawer.vue";
import SummaryCard from "@/components/SummaryCard.vue";
import {
  buildRealtimeEventsUrl,
  buildRealtimeExportUrl,
  createRealtimeJob,
  fetchRealtimeJob,
  fetchRealtimeStations,
  fetchRealtimeTrainDetail,
} from "@/lib/api";
import { useUiStore } from "@/stores/ui";
import type {
  RealtimeAggregatedResult,
  RealtimeDailyItem,
  RealtimeJobEvent,
  RealtimeJobResponse,
  RealtimeQueryRequest,
  RealtimeTrainDetail,
} from "@/types";

const uiStore = useUiStore();
const { isDrawerOpen } = storeToRefs(uiStore);

const today = new Date().toISOString().slice(0, 10);
const form = reactive({
  dateMode: "single",
  queryMode: "route" as "route" | "single_head",
  queryScope: "station" as "station" | "city",
  date: today,
  dateFrom: today,
  dateTo: today,
  fromStationName: "",
  toStationName: "",
  trainCode: "",
  trainClassName: "",
});
const realtimeTrainClassOptions = [
  "G-高速",
  "C-城际",
  "D-动车",
  "Z-直达",
  "T-特快",
  "K-快速",
  "Y-旅游",
  "S-市域",
];
const viewMode = ref<"daily" | "aggregate">("daily");
const jobId = ref("");
const realtimeEvents = ref<RealtimeJobEvent[]>([]);
const submitError = ref("");
const selected = ref<{
  queryDate: string;
  trainNo: string;
  fromStationName?: string;
  toStationName?: string;
} | null>(null);
let eventSource: EventSource | null = null;

const stationsQuery = useQuery({
  queryKey: ["realtime-stations"],
  queryFn: () => fetchRealtimeStations(),
});

const jobQuery = useQuery({
  queryKey: computed(() => ["realtime-job", jobId.value]),
  queryFn: () => fetchRealtimeJob(jobId.value),
  enabled: computed(() => Boolean(jobId.value)),
  refetchInterval: (query) => {
    const status = (query.state.data as RealtimeJobResponse | undefined)?.status;
    return status && ["completed", "failed"].includes(status) ? false : 1000;
  },
});

const detailQuery = useQuery({
  queryKey: computed(() => ["realtime-detail", selected.value]),
  queryFn: () =>
    fetchRealtimeTrainDetail(
      selected.value!.queryDate,
      selected.value!.trainNo,
      selected.value!.fromStationName,
      selected.value!.toStationName,
    ),
  enabled: computed(() => Boolean(selected.value)),
});

const stations = computed(() => stationsQuery.data.value?.stations ?? []);
const cities = computed(() => stationsQuery.data.value?.cities ?? []);
const locationOptions = computed(() =>
  form.queryScope === "city" ? cities.value : stations.value,
);
const jobPayload = computed<RealtimeJobResponse | null>(() => jobQuery.data.value ?? null);
const jobResult = computed(() => jobPayload.value?.result ?? null);
const detail = computed<RealtimeTrainDetail | null>(() => detailQuery.data.value ?? null);
const detailLoading = computed(() => detailQuery.isLoading.value);
const running = computed(() => {
  const status = jobPayload.value?.status;
  return status === "queued" || status === "running";
});
const failed = computed(() => jobPayload.value?.status === "failed");
const exportCsvUrl = computed(() => (jobId.value ? buildRealtimeExportUrl(jobId.value, "csv") : ""));
const exportJsonUrl = computed(() => (jobId.value ? buildRealtimeExportUrl(jobId.value, "json") : ""));

watch(
  () => form.queryMode,
  (mode) => {
    if (mode === "route") {
      return;
    }
    form.toStationName = "";
  },
);

watch(
  () => jobPayload.value?.status,
  (status) => {
    if (status && ["completed", "failed"].includes(status)) {
      closeEventSource();
    }
  },
);

onBeforeUnmount(() => {
  closeEventSource();
});

function closeEventSource(): void {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function openEventSource(nextJobId: string): void {
  closeEventSource();
  eventSource = new EventSource(buildRealtimeEventsUrl(nextJobId));
  eventSource.onmessage = (event) => {
    realtimeEvents.value.push(JSON.parse(event.data) as RealtimeJobEvent);
  };
  ["queued", "bootstrap", "querying_date", "enriching_schedule", "completed", "failed"].forEach(
    (eventName) => {
      eventSource?.addEventListener(eventName, (event) => {
        const messageEvent = event as MessageEvent<string>;
        realtimeEvents.value.push(JSON.parse(messageEvent.data) as RealtimeJobEvent);
      });
    },
  );
}

function normalizeTrainClassFilter(value: string): string {
  const text = value.trim();
  if (!text) {
    return "";
  }
  const parts = text.split("-", 2);
  return parts.length === 2 ? parts[1].trim() : text;
}

async function submit(): Promise<void> {
  submitError.value = "";
  realtimeEvents.value = [];
  selected.value = null;
  uiStore.closeDrawer();
  const payload: RealtimeQueryRequest = {
    query_mode: form.queryMode,
    query_scope: form.queryScope,
    train_code: form.trainCode.trim() || undefined,
    train_class_name: normalizeTrainClassFilter(form.trainClassName) || undefined,
  };
  if (form.dateMode === "single") {
    payload.date = form.date;
  } else {
    payload.date_from = form.dateFrom;
    payload.date_to = form.dateTo;
  }
  if (form.fromStationName.trim()) {
    payload.from_station_name = form.fromStationName.trim();
  }
  if (form.toStationName.trim()) {
    payload.to_station_name = form.toStationName.trim();
  }
  try {
    const response = await createRealtimeJob(payload);
    jobId.value = response.job_id;
    openEventSource(response.job_id);
    await jobQuery.refetch();
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : "创建实时任务失败";
  }
}

function selectItem(item: RealtimeDailyItem): void {
  const detailFromStationName =
    item.query_scope === "city" ? item.matched_from_station_name || item.from_station_name : item.from_station_name;
  const detailToStationName =
    item.query_scope === "city" ? item.matched_to_station_name || item.to_station_name : item.to_station_name;
  selected.value = {
    queryDate: item.query_date,
    trainNo: item.train_no,
    fromStationName: detailFromStationName,
    toStationName: detailToStationName,
  };
  uiStore.openDrawer();
}

const flattenedDailyItems = computed(() =>
  (jobResult.value?.daily_results ?? []).flatMap((daily) => daily.items),
);

function renderRouteLabel(item: RealtimeDailyItem): string {
  if (item.query_scope === "city" && item.matched_from_station_name && item.matched_to_station_name) {
    return `${item.matched_from_station_name} → ${item.matched_to_station_name}`;
  }
  return `${item.from_station_name || item.matched_station_name || "--"} → ${item.to_station_name || item.end_station_name || "--"}`;
}

function renderAggregatedLabel(item: RealtimeAggregatedResult): string {
  if (item.query_mode === "route") {
    if (item.query_scope === "city" && item.matched_from_station_name && item.matched_to_station_name) {
      return `${item.matched_from_station_name} → ${item.matched_to_station_name}`;
    }
    if (item.route_signature) {
      return item.route_signature;
    }
  }
  return item.matched_station_name || "--";
}
</script>

<template>
  <main class="page page-search">
    <section class="search-topbar glass-card">
      <div>
        <p class="eyebrow">实时检索</p>
        <h1>12306 Realtime Studio</h1>
      </div>
      <div class="toolbar-actions">
        <a v-if="jobId" class="ghost-button" :href="exportJsonUrl">导出 JSON</a>
        <a v-if="jobId" class="primary-button" :href="exportCsvUrl">导出 CSV</a>
      </div>
    </section>

    <section class="search-layout">
      <div class="search-main">
        <section class="filters-panel glass-card">
          <div class="filters-header">
            <div>
              <p class="eyebrow">实时表单</p>
              <h2>区间 / 单头 / 车次号</h2>
            </div>
            <button class="primary-button" @click="submit">开始查询</button>
          </div>

          <div class="filters-grid realtime-filters-grid">
            <label class="field-mode-date">
              <span>日期模式</span>
              <select v-model="form.dateMode">
                <option value="single">单日</option>
                <option value="range">日期范围</option>
              </select>
            </label>
            <label class="field-mode-query">
              <span>查询模式</span>
              <select v-model="form.queryMode">
                <option value="route">双头区间</option>
                <option value="single_head">单头 / 车次号</option>
              </select>
            </label>
            <label class="field-mode-scope">
              <span>匹配范围</span>
              <select v-model="form.queryScope">
                <option value="station">站点对</option>
                <option value="city">城市对</option>
              </select>
            </label>

            <label class="field-date-single">
              <span>日期</span>
              <input
                v-model="form.date"
                type="date"
                :disabled="form.dateMode !== 'single'"
                :class="{ 'field-disabled': form.dateMode !== 'single' }"
              />
            </label>
            <label class="field-date-from">
              <span>开始日期</span>
              <input
                v-model="form.dateFrom"
                type="date"
                :disabled="form.dateMode !== 'range'"
                :class="{ 'field-disabled': form.dateMode !== 'range' }"
              />
            </label>
            <label class="field-date-to">
              <span>结束日期</span>
              <input
                v-model="form.dateTo"
                type="date"
                :disabled="form.dateMode !== 'range'"
                :class="{ 'field-disabled': form.dateMode !== 'range' }"
              />
            </label>

            <label class="field-station-from">
              <span>{{ form.queryMode === "route" ? (form.queryScope === "city" ? "出发城市" : "出发站") : (form.queryScope === "city" ? "城市" : "站点") }}</span>
              <input v-model="form.fromStationName" list="realtime-location-options" :placeholder="form.queryScope === 'city' ? '上海 / 北京' : '杭州东 / 济南西'" />
            </label>
            <label class="field-station-to">
              <span>{{ form.queryScope === "city" ? "到达城市" : "到达站" }}</span>
              <input
                v-model="form.toStationName"
                list="realtime-location-options"
                :placeholder="form.queryScope === 'city' ? '北京 / 上海' : '上海虹桥'"
                :disabled="form.queryMode !== 'route'"
                :class="{ 'field-disabled': form.queryMode !== 'route' }"
              />
            </label>

            <label class="field-train-code">
              <span>车次号</span>
              <input v-model="form.trainCode" placeholder="精确匹配，如 G5" />
            </label>
            <label class="field-train-class">
              <span>车型</span>
              <input
                v-model="form.trainClassName"
                list="realtime-train-classes"
                placeholder="G-高速 / D-动车"
              />
            </label>
          </div>

          <datalist id="realtime-location-options">
            <option v-for="location in locationOptions" :key="location" :value="location" />
          </datalist>
          <datalist id="realtime-train-classes">
            <option
              v-for="item in realtimeTrainClassOptions"
              :key="item"
              :value="item"
            />
          </datalist>

          <p class="hint-line">
            {{ form.queryMode === "route" ? (form.queryScope === "station" ? "站点对模式只保留精确站点命中的结果，并返回该区间价格与余票。" : "城市对模式采用宽松城市匹配：先查城市主站，再保留命中的真实站点区间。") : "单头模式为慢查询，只返回时刻，不返回票价和余票。" }}
          </p>
          <p v-if="submitError" class="error-line">{{ submitError }}</p>
        </section>

        <section v-if="jobResult" class="summary-grid compact">
          <SummaryCard label="命中车次" :value="jobResult.summary.matched_train_count" />
          <SummaryCard label="成功日期" :value="jobResult.summary.successful_days" />
          <SummaryCard label="失败日期" :value="jobResult.summary.failed_days" />
          <SummaryCard
            label="最低价"
            :value="jobResult.summary.cheapest_available_price !== null ? `¥${jobResult.summary.cheapest_available_price}` : '--'"
          />
        </section>

        <section v-if="running" class="status-card glass-card">
          正在执行实时查询…
          <ul class="event-list">
            <li v-for="(event, index) in realtimeEvents.slice(-6)" :key="`${event.timestamp}-${index}`">
              {{ event.timestamp }} · {{ event.message || event.event }}
            </li>
          </ul>
        </section>

        <section v-else-if="failed" class="status-card glass-card">
          任务失败：{{ jobPayload?.error || "请稍后重试" }}
        </section>

        <template v-if="jobResult">
          <section class="results-panel glass-card">
            <div class="results-header">
              <div>
                <p class="eyebrow">结果视图</p>
                <h2>按天明细 / 聚合摘要</h2>
              </div>
              <div class="toolbar-actions">
                <button
                  class="ghost-button"
                  :class="{ active: viewMode === 'daily' }"
                  @click="viewMode = 'daily'"
                >
                  按天明细
                </button>
                <button
                  class="ghost-button"
                  :class="{ active: viewMode === 'aggregate' }"
                  @click="viewMode = 'aggregate'"
                >
                  按车次聚合
                </button>
              </div>
            </div>

            <div v-if="jobResult.partial_failures.length" class="failure-grid">
              <article
                v-for="failure in jobResult.partial_failures"
                :key="`${failure.query_date}-${failure.stage}`"
                class="failure-card"
              >
                <strong>{{ failure.query_date }}</strong>
                <p>{{ failure.error_type }}</p>
                <small>{{ failure.message }}</small>
              </article>
            </div>

            <div v-if="viewMode === 'daily'" class="daily-results">
              <section
                v-for="daily in jobResult.daily_results"
                :key="daily.query_date"
                class="daily-card"
              >
                <header class="daily-card-header">
                  <h3>{{ daily.query_date }}</h3>
                  <p>{{ daily.summary.matched_train_count }} 列 · 最低价 {{ daily.summary.cheapest_available_price !== null ? `¥${daily.summary.cheapest_available_price}` : "--" }}</p>
                </header>
                <div class="table-shell">
                  <table class="results-table realtime-table">
                    <thead>
                      <tr>
                        <th>车次</th>
                        <th>车型</th>
                        <th>区间</th>
                        <th>出发</th>
                        <th>到达</th>
                        <th>历时</th>
                        <th>最低价</th>
                        <th>售卖状态</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr
                        v-for="item in daily.items"
                        :key="`${item.query_date}-${item.train_no}`"
                        class="result-row"
                        @click="selectItem(item)"
                      >
                        <td>{{ item.train_code }}</td>
                        <td>{{ item.train_class_name }}</td>
                        <td>{{ renderRouteLabel(item) }}</td>
                        <td>{{ item.depart_time }}</td>
                        <td>{{ item.arrive_time }}</td>
                        <td>{{ item.duration }}</td>
                        <td>{{ item.min_price !== null ? `¥${item.min_price.toFixed(1)}` : "--" }}</td>
                        <td>{{ item.sale_status || "--" }}</td>
                      </tr>
                      <tr v-if="daily.items.length === 0">
                        <td colspan="8" class="empty-row">当前日期没有命中结果</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </section>
            </div>

            <div v-else class="table-shell">
              <table class="results-table realtime-table">
                <thead>
                  <tr>
                    <th>车次</th>
                    <th>车型</th>
                    <th>区间/站点</th>
                    <th>首次出现</th>
                    <th>最后出现</th>
                    <th>可售天数</th>
                    <th>最低价</th>
                    <th>最快历时</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in jobResult.aggregated_results" :key="`${item.train_code}-${item.route_signature}-${item.matched_station_name}`">
                    <td>{{ item.train_code }}</td>
                    <td>{{ item.train_class_name }}</td>
                    <td>{{ renderAggregatedLabel(item) }}</td>
                    <td>{{ item.first_seen_date }}</td>
                    <td>{{ item.last_seen_date }}</td>
                    <td>{{ item.available_days }}</td>
                    <td>{{ item.min_price !== null ? `¥${item.min_price.toFixed(1)}` : "--" }}</td>
                    <td>{{ item.sample_duration }}</td>
                  </tr>
                  <tr v-if="jobResult.aggregated_results.length === 0">
                    <td colspan="8" class="empty-row">当前任务没有聚合结果</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </template>

        <section v-else-if="flattenedDailyItems.length === 0" class="status-card glass-card">
          提交实时查询后，这里会显示进度、按天结果和聚合摘要。
        </section>
      </div>

      <RealtimeDetailDrawer
        :open="isDrawerOpen"
        :detail="detail"
        :loading="detailLoading"
        @close="uiStore.closeDrawer()"
      />
    </section>
  </main>
</template>
