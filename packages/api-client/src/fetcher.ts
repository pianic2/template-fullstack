export type ApiConfiguration = { baseUrl: string; accessToken?: () => Promise<string | null> };
let configuration: ApiConfiguration = { baseUrl: 'http://localhost:8000' };

export function configureApiClient(next: ApiConfiguration): void {
  configuration = next;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly body: unknown,
  ) {
    super(`API request failed (${status})`);
    this.name = 'ApiError';
  }
}

export async function customFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  const accessToken = await configuration.accessToken?.();
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(new URL(url, configuration.baseUrl), {
    ...options,
    credentials: 'include',
    headers,
  });
  const data = response.status === 204 ? undefined : await response.json().catch(() => undefined);
  if (!response.ok) throw new ApiError(response.status, data);
  return { data, status: response.status, headers: response.headers } as T;
}
