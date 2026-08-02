import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import i18n, { setupI18nMessages } from "./i18n";
import "./assets/styles/index.scss";
import "./theme"; // 应用持久化主题 (data-theme)

const app = createApp(App);
;(window as any).__app = app;
app.use(createPinia());
app.use(router);
app.use(i18n);
// 语言包为懒加载 chunk: 挂载前先加载当前语言, 避免闪 key
setupI18nMessages().finally(() => app.mount("#app"));
