import { createConfigForNuxt } from '@nuxt/eslint-config'

export default createConfigForNuxt()
  // Keep Nuxt-aware defaults, but avoid blocking commits on
  // overly-strict typing/style rules in this UI package.
  .override('nuxt/typescript/rules', {
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
    },
  })
  .override('nuxt/vue/rules', {
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/attributes-order': 'off',
      'vue/html-self-closing': 'off',
      'vue/no-unused-vars': 'warn',
    },
  })
  .override('nuxt/rules', {
    rules: {
      'nuxt/prefer-import-meta': 'off',
    },
  })
