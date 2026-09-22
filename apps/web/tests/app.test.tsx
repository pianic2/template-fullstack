import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { App } from '../src/routes/App';

vi.mock('@template/api-client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@template/api-client')>()),
  useGetHealthLive: () => ({ isSuccess: false, isPending: true, data: undefined }),
  useGetUsersMe: () => ({ isError: false, error: undefined, queryKey: ['/api/v1/users/me'] }),
}));

describe('web shell', () => {
  it('renders product navigation and the shared API health state', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByRole('heading', { name: /build the product/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Account' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('API checking');
  });
});
