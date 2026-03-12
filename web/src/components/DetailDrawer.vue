<script setup lang="ts">
import type { TrainDetailResponse } from "@/types";

defineProps<{
  open: boolean;
  detail: TrainDetailResponse | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

function normalizeFlag(value: string): string {
  return value === "Y" ? "始发/终到" : "";
}
</script>

<template>
  <transition name="drawer-fade">
    <div v-if="open" class="drawer-backdrop" @click.self="emit('close')">
      <aside class="detail-drawer glass-card">
        <button class="drawer-close" @click="emit('close')">关闭</button>

        <div v-if="loading" class="drawer-loading">正在加载详情…</div>
        <div v-else-if="detail" class="drawer-content">
          <header class="detail-hero">
            <p class="eyebrow">列车详情</p>
            <h2>{{ detail.train.train_code }}</h2>
            <p>{{ detail.train.train_class_name }} · {{ detail.train.start_station_name }} → {{ detail.train.end_station_name }}</p>
          </header>

          <section class="detail-section">
            <h3>基础信息</h3>
            <div class="detail-grid">
              <div><span>出发</span><strong>{{ detail.train.depart_time }}</strong></div>
              <div><span>到达</span><strong>{{ detail.train.arrive_time }}</strong></div>
              <div><span>历时</span><strong>{{ detail.train.duration }}</strong></div>
              <div><span>价格快照区间</span><strong>{{ detail.route_signature || detail.train.route_signature }}</strong></div>
            </div>
          </section>

          <section class="detail-section">
            <h3>席别价格</h3>
            <div class="price-grid">
              <article v-for="seat in detail.seat_prices" :key="`${seat.route_signature}-${seat.seat_code}`" class="price-chip">
                <span>{{ seat.seat_name }}</span>
                <strong>¥{{ seat.price.toFixed(1) }}</strong>
              </article>
            </div>
          </section>

          <section class="detail-section">
            <h3>停站时间轴</h3>
            <ol class="stop-list">
              <li v-for="stop in detail.stops" :key="`${stop.train_no}-${stop.station_no}`">
                <div>
                  <strong>{{ stop.station_name }}</strong>
                  <p>{{ normalizeFlag(stop.is_start) || normalizeFlag(stop.is_end) }}</p>
                </div>
                <div class="stop-times">
                  <span>到 {{ stop.arrive_time }}</span>
                  <span>发 {{ stop.start_time }}</span>
                </div>
              </li>
            </ol>
          </section>
        </div>
        <div v-else class="drawer-empty">选择一条车次后查看详情</div>
      </aside>
    </div>
  </transition>
</template>
