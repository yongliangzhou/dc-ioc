import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AsyncSection from '@/components/common/AsyncSection.vue'

/** 阶段 1/2 验收：加载 / 错误 / 空 / 成功四态严格区分，错误态可重试。 */
describe('AsyncSection 四态', () => {
  it('loading 显示骨架，且不显示错误/空态', () => {
    const wrapper = mount(AsyncSection, { props: { loading: true } })
    expect(wrapper.find('.loading-state').exists()).toBe(true)
    expect(wrapper.find('.ls-skel-row').exists()).toBe(true)
    expect(wrapper.find('.error-retry').exists()).toBe(false)
    expect(wrapper.find('.empty-state').exists()).toBe(false)
  })

  it('error 显示错误原因与重试按钮，点击后 emit retry', async () => {
    const wrapper = mount(AsyncSection, { props: { error: '后端不可达' } })
    expect(wrapper.find('.error-retry').exists()).toBe(true)
    expect(wrapper.find('.empty-state').exists()).toBe(false)
    expect(wrapper.find('.loading-state').exists()).toBe(false)
    expect(wrapper.text()).toContain('后端不可达')
    await wrapper.find('.er-btn').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('empty 显示空态，不显示错误态', () => {
    const wrapper = mount(AsyncSection, {
      props: { empty: true, emptyTitle: '暂无数据', emptyDesc: '请稍后重试' },
    })
    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('暂无数据')
    expect(wrapper.text()).toContain('请稍后重试')
    expect(wrapper.find('.error-retry').exists()).toBe(false)
  })

  it('success 渲染默认插槽', () => {
    const wrapper = mount(AsyncSection, {
      slots: { default: '<div class="payload">指标内容</div>' },
    })
    expect(wrapper.find('.payload').text()).toBe('指标内容')
    expect(wrapper.find('.loading-state').exists()).toBe(false)
  })

  it('状态优先级 loading > error > empty，且可吃 useAsyncPage 风格 page 对象', () => {
    const wrapper = mount(AsyncSection, {
      props: {
        loading: true,
        error: '失败',
        empty: true,
      },
    })
    expect(wrapper.find('.loading-state').exists()).toBe(true)

    const byPage = mount(AsyncSection, {
      props: {
        page: { loading: false, error: '网络异常', empty: true },
      },
    })
    expect(byPage.find('.error-retry').exists()).toBe(true)
    expect(byPage.find('.empty-state').exists()).toBe(false)
  })
})
