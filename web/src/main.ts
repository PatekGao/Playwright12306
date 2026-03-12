import { VueQueryPlugin, QueryClient } from "@tanstack/vue-query";
import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { router } from "./router";
import "./styles.css";

const app = createApp(App);
const queryClient = new QueryClient();

app.use(createPinia());
app.use(router);
app.use(VueQueryPlugin, { queryClient });

app.mount("#app");
