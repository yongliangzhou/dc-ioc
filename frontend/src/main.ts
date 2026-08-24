import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n, { setupI18nMessages } from './i18n'
import Toast from './components/ui/Toast.vue'
import './assets/styles/index.scss'
import './theme' // 应用持久化主题 (data-theme)

const app = createApp(App)
;(window as unknown as { __app?: typeof app }).__app = app
app.use(createPinia())
app.use(router)
app.use(i18n)
app.component('Toast', Toast) // 全局挂载，任意页面 toast 反馈
// 语言包为懒加载 chunk: 挂载前先加载当前语言, 避免闪 key
;(async () => {
  try {
    await setupI18nMessages()
  } catch (e) {
    console.error('[i18n] failed to load locale messages:', e)
  }
  app.mount('#app')
})()
