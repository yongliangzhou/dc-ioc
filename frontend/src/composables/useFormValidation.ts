/**
 * 通用表单校验 composable (U-05)
 *
 * 设计目标:
 * - 字段级实时校验: 失焦/输入即校验, 不依赖后端 422
 * - 提交门禁: validateAll() 返回是否可提交, 配合 submitting 禁用按钮
 * - 框架无关: 仅依赖 reactive/ref/computed, 不绑定任何 UI 库
 *
 * 用法:
 *   const { errors, touched, validate, validateAll, reset, bind } = useFormValidation(rules)
 *   errors.value.name / touched.value.name 在模板中驱动 <FieldError>
 *   <input v-model="form.name" @blur="validate('name')" :class="{ invalid: touched.name && errors.name }" />
 *   <button :disabled="submitting || !validateAll()" @click="onSubmit">提交</button>
 */
import { reactive, ref, type Ref } from 'vue'

export type Validator = (value: unknown, form: Record<string, unknown>) => string | true
export type FormRules<T extends string = string> = Partial<Record<T, Validator[]>>

export interface UseFormValidationOptions<T extends string = string> {
  rules: FormRules<T>
  /** 初始值, 用于 reset 还原 */
  initial?: Record<T, unknown>
}

export function useFormValidation<T extends string = string>(
  options: UseFormValidationOptions<T>,
) {
  const { rules, initial } = options

  const errors = reactive<Record<string, string>>({}) as Record<T, string>
  const touched = reactive<Record<string, boolean>>({}) as Record<T, boolean>
  const submitting: Ref<boolean> = ref(false)

  function runField(field: T, form: Record<string, unknown>): string {
    const validators = rules[field] ?? []
    for (const v of validators) {
      const r = v(form[field], form)
      if (r !== true) return r
    }
    return ''
  }

  /** 校验单个字段, 记录 touched 与错误 */
  function validate(field: T, form: Record<string, unknown>): boolean {
    touched[field] = true
    const msg = runField(field, form)
    if (msg) errors[field] = msg
    else delete (errors as Record<string, string>)[field]
    return !msg
  }

  /** 校验全部字段, 返回是否全部通过 (用于提交门禁) */
  function validateAll(form: Record<string, unknown>): boolean {
    let ok = true
    for (const field of Object.keys(rules) as T[]) {
      if (!validate(field, form)) ok = false
    }
    return ok
  }

  function reset() {
    for (const k of Object.keys(errors)) delete (errors as Record<string, string>)[k]
    for (const k of Object.keys(touched)) delete (touched as Record<string, boolean>)[k]
    submitting.value = false
  }

  /** 归一化后端 422 detail 数组到字段错误 */
  function applyServerErrors(detail: unknown) {
    if (!Array.isArray(detail)) return
    for (const d of detail as Array<{ loc?: unknown[]; msg?: string }>) {
      const field = (d.loc?.slice(-1)[0] || '') as string
      if (field && d.msg) {
        ;(errors as Record<string, string>)[field] = d.msg
        ;(touched as Record<string, boolean>)[field] = true
      }
    }
  }

  return {
    errors: errors as Record<T, string>,
    touched: touched as Record<T, boolean>,
    submitting,
    validate,
    validateAll,
    reset,
    applyServerErrors,
  }
}

/* ---------- 常用校验器工厂 ---------- */

export const required =
  (msg = '此项必填'): Validator =>
  (v) =>
    v === undefined || v === null || (typeof v === 'string' && v.trim() === '') ? msg : true

export const minLen =
  (n: number, msg?: string): Validator =>
  (v) =>
    typeof v === 'string' && v.trim().length < n ? (msg ?? `至少 ${n} 个字符`) : true

export const maxLen =
  (n: number, msg?: string): Validator =>
  (v) =>
    typeof v === 'string' && v.length > n ? (msg ?? `最多 ${n} 个字符`) : true

/** 资源名/设备ID: 字母数字开头, 允许 ._:- */
export const pattern =
  (re: RegExp, msg: string): Validator =>
  (v) =>
    typeof v === 'string' && v !== '' && !re.test(v) ? msg : true

export const ipPattern = pattern(
  /^(?:\d{1,3}\.){3}\d{1,3}$/,
  'IP 格式不正确 (如 10.0.0.1)',
)

export const isIpOrHost = pattern(
  /^(?:(?:\d{1,3}\.){3}\d{1,3}|[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*)$/,
  '主机名/IP 格式不正确',
)

export const rangeLen =
  (min: number, max: number, msg?: string): Validator =>
  (v) => {
    const s = typeof v === 'string' ? v.trim() : ''
    if (s.length < min || s.length > max) return msg ?? `长度需在 ${min}-${max} 之间`
    return true
  }
