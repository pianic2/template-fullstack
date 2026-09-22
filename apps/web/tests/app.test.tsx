import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { App } from '../src/routes/App';
import { vi } from 'vitest';

vi.mock('@template/api-client', () => ({ getHealthLive: () => new Promise(() => undefined) }));

describe('web shell', () => {
  it('renders product navigation and the shared API health state', () => {
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><App /></MemoryRouter></QueryClientProvider>);
    expect(screen.getByRole('heading', { name: /build the product/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Account' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('API checking');
  });
});
