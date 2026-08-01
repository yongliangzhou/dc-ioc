<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>DC-IOC Platform</h1>
        <p>{{ tl('数据中心智能运营中心') }}</p>
      </div>
      <form @submit.prevent="handleLogin">
        <label>{{ tl('用户名') }}</label>
        <input v-model="form.username" type="text" placeholder="admin" autocomplete="username" />
        <label>{{ tl('密码') }}</label>
        <input v-model="form.password" type="password" :placeholder="tl('请输入密码')" autocomplete="current-password" />
        <p v-if="error" class="err">{{ error }}</p>
        <button type="submit" :disabled="loading">{{ loading ? '登录中...' : '登 录' }}</button>
      </form>
      <div class="login-footer">{{ tl('演示账号') }}: admin / admin123</div>
    </div>
  </div>
</template>

<script setup lang="ts">import { useI18n } from "vue-i18n";
const { t: tl } = useI18n();
import { ref, reactive } from 'vue';import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/modules/auth';

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({ username: 'admin', password: 'admin123' });
const loading = ref(false);
const error = ref('');

async function handleLogin() {
  if (!form.username || !form.password) {
    error.value = '请输入用户名和密码';
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    await authStore.login(form.username, form.password);
    router.replace('/overview');
  } catch (e: any) {
    error.value = e?.detail || e?.message || '登录失败';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0a0e27 0%, #161d3b 50%, #0d1230 100%);
}
.login-card {
  width: 380px;
  padding: 40px 36px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
}
.login-header { text-align: center; margin-bottom: 32px; }
.login-header h1 { font-size: 22px; color: #22e3ff; margin: 0 0 6px; font-weight: 700; }
.login-header p { color: #8892b0; font-size: 13px; margin: 0; }
label { display: block; color: #ccd6f6; font-size: 13px; margin: 14px 0 6px; }
input {
  width: 100%; padding: 10px 12px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  border-radius: 6px; color: #e6f1ff; font-size: 14px; outline: none;
  box-sizing: border-box;
}
input:focus { border-color: #22e3ff; }
.err { color: #ff6b6b; font-size: 12px; margin: 10px 0 0; }
button {
  width: 100%; margin-top: 22px; padding: 11px;
  background: linear-gradient(135deg, #1a73e8, #22e3ff); border: none;
  border-radius: 6px; color: #fff; font-size: 15px; font-weight: 600; cursor: pointer;
}
button:disabled { opacity: 0.5; cursor: not-allowed; }
.login-footer { text-align: center; color: #5a6380; font-size: 11px; margin-top: 20px; }
</style>
