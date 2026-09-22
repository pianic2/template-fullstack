import { defineConfig } from 'orval';

export default defineConfig({
  productApi: {
    input: { target: './openapi/openapi.yaml' },
    output: {
      target: './packages/api-client/src/generated/api.ts',
      schemas: './packages/api-client/src/generated/model',
      client: 'fetch',
      mode: 'split',
      clean: true,
      override: { mutator: { path: './packages/api-client/src/fetcher.ts', name: 'customFetch' } },
    },
  },
});
