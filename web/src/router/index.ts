import { createRouter, createWebHistory } from "vue-router";

import OverviewView from "@/views/OverviewView.vue";
import RealtimeView from "@/views/RealtimeView.vue";
import SearchView from "@/views/SearchView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "overview",
      component: OverviewView,
    },
    {
      path: "/search",
      name: "search",
      component: SearchView,
    },
    {
      path: "/realtime",
      name: "realtime",
      component: RealtimeView,
    },
  ],
});
