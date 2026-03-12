import { defineStore } from "pinia";

export const useUiStore = defineStore("ui", {
  state: () => ({
    isDrawerOpen: false,
  }),
  actions: {
    openDrawer() {
      this.isDrawerOpen = true;
    },
    closeDrawer() {
      this.isDrawerOpen = false;
    },
  },
});
