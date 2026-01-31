/** @type {import("eslint").Linter.Config} */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2020: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  plugins: ['@typescript-eslint', 'react-hooks', 'react-refresh'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist/', 'node_modules/'],
  rules: {
    // NOTE: The repo uses contexts + hooks modules (non-component exports), which the
    // react-refresh rule flags aggressively. Keep lint actionable by disabling it.
    'react-refresh/only-export-components': 'off',

    // This repo uses TypeScript strictness and sometimes requires `any` (e.g., API payload metadata).
    // Keep the lint pass actionable by avoiding "warn" severity that would fail `--max-warnings 0`.
    '@typescript-eslint/no-explicit-any': 'off',

    // Allow underscore-prefixed unused values (common for intentionally ignored props/args).
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
      },
    ],
  },
}

