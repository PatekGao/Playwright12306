import { createRouter, createWebHistory } from "vue-router";

import OverviewView from "@/views/OverviewView.vue";
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
  ],
});
