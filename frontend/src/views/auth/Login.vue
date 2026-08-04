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
        <input
          v-model="form.password"
          type="password"
          :placeholder="tl('请输入密码')"
          autocomplete="current-password"
        />
        <p v-if="error" class="err">{{ error }}</p>
        <button type="submit" :disabled="loading">{{ loading ? '登录中...' : '登 录' }}</button>
      </form>

      <!-- 5.4.1 自助注册 (后端 ALLOW_SELF_REGISTER 开关控制, 默认关闭) -->
      <div class="register-block">
        <button class="link-btn" type="button" @click="showRegister = !showRegister">
          {{ showRegister ? '收起注册' : '注册新账号' }}
        </button>
        <form v-if="showRegister" @submit.prevent="handleRegister" class="register-form">
          <input v-model="reg.username" type="text" placeholder="用户名 (2-64 位)" />
          <input v-model="reg.display_name" type="text" placeholder="显示名 (可选)" />
          <input v-model="reg.password" type="password" placeholder="密码 (至少 6 位)" />
          <p v-if="regError" class="err">{{ regError }}</p>
          <button type="submit" :disabled="regLoading">
            {{ regLoading ? '提交中...' : '注册为只读账号' }}
          </button>
        </form>
      </div>

      <div class="login-footer">{{ tl('演示账号') }}: admin / admin123</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/modules/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({ username: 'admin', password: 'admin123' })
const loading = ref(false)
const error = ref('')

const showRegister = ref(false)
const reg = reactive({ username: '', display_name: '', password: '' })
const regLoading = ref(false)
const regError = ref('')

async function handleLogin() {
  if (!form.username || !form.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await authStore.login(form.username, form.password)
    router.replace('/overview')
  } catch (e: any) {
    error.value = e?.detail || e?.message || '登录失败'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  if (!reg.username || !reg.password) {
    regError.value = '请输入用户名和密码'
    return
  }
  regLoading.value = true
  regError.value = ''
  try {
    const { registerUser } = await import('@/api')
    await registerUser({
      username: reg.username,
      password: reg.password,
      display_name: reg.display_name,
    })
    regError.value = '注册成功，请使用新账号登录'
    showRegister.value = false
  } catch (e: any) {
    regError.value = e?.detail || e?.message || '注册失败（可能未开放自助注册）'
  } finally {
    regLoading.value = false
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
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-header h1 {
  font-size: 22px;
  color: #22e3ff;
  margin: 0 0 6px;
  font-weight: 700;
}
.login-header p {
  color: #8892b0;
  font-size: 13px;
  margin: 0;
}
label {
  display: block;
  color: #ccd6f6;
  font-size: 13px;
  margin: 14px 0 6px;
}
input {
  width: 100%;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: #e6f1ff;
  font-size: 14px;
  outline: none;
  box-sizing: border-box;
}
input:focus {
  border-color: #22e3ff;
}
.err {
  color: #ff6b6b;
  font-size: 12px;
  margin: 10px 0 0;
}
button {
  width: 100%;
  margin-top: 22px;
  padding: 11px;
  background: linear-gradient(135deg, #1a73e8, #22e3ff);
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.login-footer {
  text-align: center;
  color: #5a6380;
  font-size: 11px;
  margin-top: 20px;
}
.register-block {
  margin-top: 18px;
  text-align: center;
}
.link-btn {
  background: none;
  border: none;
  color: #22e3ff;
  font-size: 12px;
  cursor: pointer;
  margin: 0;
  padding: 0;
  width: auto;
}
.register-form {
  margin-top: 14px;
}
.register-form input {
  margin-bottom: 10px;
}
.register-form button {
  margin-top: 4px;
  background: linear-gradient(135deg, #2a3a5e, #3a4a6e);
}
</style>
