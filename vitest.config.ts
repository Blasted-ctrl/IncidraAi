import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['packages/**/test-*.ts', 'packages/**/*.test.ts', 'apps/**/test-*.ts', 'apps/**/*.test.ts'],
    exclude: ['**/node_modules/**', 'dist', '.idea', '.git', '.cache'],
    testTimeout: 10000,
  },
});
