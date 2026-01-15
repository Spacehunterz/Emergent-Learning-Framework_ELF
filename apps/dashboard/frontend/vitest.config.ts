import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    exclude: [
      '**/node_modules/**',
      '**/tests/**',
      '**/*.spec.ts',
    ],
    include: ['**/*.test.ts', '**/*.test.tsx'],
  },
})
