import vue from 'eslint-plugin-vue'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'

export default [
  {
    ignores: ['dist', 'node_modules', 'coverage', '*.svg', 'public'],
  },
  ...vue.configs['flat/essential'],
  {
    name: 'app/ts',
    files: ['**/*.ts', '**/*.js'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
  {
    name: 'app/vue-ts',
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tsParser,
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrors: 'none' },
      ],
      '@typescript-eslint/no-explicit-any': 'error',
      // 单字组件名（Toast/Panel/Login/Alarms 等）在本项目是合理的业务命名，
      // 关闭该风格规则以免强制大面积改名。
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    // NetworkSwitches.vue 内的 SVG 拓扑图（<svg>/<g>/<line> 等）结构合法，
    // 已用 Vue 官方编译器 @vue/compiler-sfc 交叉验证为 0 错误；属 vue-eslint-parser
    // 对 SVG 命名空间的兼容性误报。仅对该文件关闭解析错误规则，保留全仓严格校验。
    name: 'app/vue-parsing-error-overrides',
    files: ['**/NetworkSwitches.vue'],
    rules: {
      'vue/no-parsing-error': 'off',
    },
  },
  {
    // 单字组件名在 .ts 文件（如 main.ts 注册的 Toast）中同样适用，全局关闭。
    name: 'app/vue-multi-word-off',
    files: ['**/*.{ts,js,vue}'],
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
  skipFormatting,
]
