import { describe, expect, it } from 'vitest'
import {
  isIpOrHost,
  maxLen,
  minLen,
  rangeLen,
  required,
  useFormValidation,
} from '@/composables/useFormValidation'

describe('useFormValidation (U-05 表单校验)', () => {
  it('required 校验空值与被填值', () => {
    expect(required()('')).toBeTypeOf('string')
    expect(required()('  ')).toBeTypeOf('string')
    expect(required('必填')('ok')).toBe(true)
    expect(required('必填')(undefined)).toBeTypeOf('string')
  })

  it('minLen/maxLen/rangeLen 边界', () => {
    expect(minLen(3)('ab')).toBeTypeOf('string')
    expect(minLen(3)('abc')).toBe(true)
    expect(maxLen(5)('abcdef')).toBeTypeOf('string')
    expect(rangeLen(2, 4)('a')).toBeTypeOf('string')
    expect(rangeLen(2, 4)('abc')).toBe(true)
    expect(rangeLen(2, 4)('abcde')).toBeTypeOf('string')
  })

  it('isIpOrHost 接受 IPv4 与主机名', () => {
    expect(isIpOrHost('10.20.1.11')).toBe(true)
    expect(isIpOrHost('host-1.local')).toBe(true)
    expect(isIpOrHost('999.1.1.1')).toBe(true) // 格式正则不校验段范围
    expect(isIpOrHost('bad host')).toBeTypeOf('string')
  })

  it('单字段校验记录 touched 与错误', () => {
    const fv = useFormValidation({ rules: { name: [required('请填写')] } })
    const form = { name: '' }
    const ok = fv.validate('name', form)
    expect(ok).toBe(false)
    expect(fv.touched.name).toBe(true)
    expect(fv.errors.name).toBe('请填写')

    form.name = 'ok'
    expect(fv.validate('name', form)).toBe(true)
    expect(fv.errors.name).toBeUndefined()
  })

  it('validateAll 提交门禁: 任一不通过即 false', () => {
    const fv = useFormValidation({
      rules: { a: [required()], b: [required()] },
    })
    expect(fv.validateAll({ a: '', b: '' })).toBe(false)
    expect(fv.validateAll({ a: 'x', b: 'y' })).toBe(true)
  })

  it('applyServerErrors 解析 422 detail 数组', () => {
    const fv = useFormValidation({ rules: { device_id: [required()] } })
    fv.applyServerErrors([
      { loc: ['body', 'device_id'], msg: '已存在' },
      { loc: ['body', 'ip'], msg: '格式错' },
    ])
    expect(fv.errors.device_id).toBe('已存在')
    expect(fv.touched.device_id).toBe(true)
  })

  it('reset 清空错误与 touched', () => {
    const fv = useFormValidation({ rules: { a: [required()] } })
    fv.validate('a', { a: '' })
    fv.reset()
    expect(fv.errors.a).toBeUndefined()
    expect(fv.touched.a).toBeUndefined()
    expect(fv.submitting.value).toBe(false)
  })
})
