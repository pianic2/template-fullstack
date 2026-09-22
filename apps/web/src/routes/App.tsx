import { Link, Route, Routes } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiError, useGetHealthLive, useGetUsersMe } from '@template/api-client';
import { useState } from 'react';
import { sessionLogin, sessionLogout } from '../auth/session';

function Home() {
  const health = useGetHealthLive();
  return (
    <main className="shell">
      <header>
        <span className="brand-mark">F</span>
        <strong>Product</strong>
        <nav>
          <Link to="/account">Account</Link>
        </nav>
      </header>
      <section className="hero">
        <p className="eyebrow">FULL STACK STARTER</p>
        <h1>
          Build the product.
          <br />
          <span>Keep the foundation.</span>
        </h1>
        <p className="lede">
          A Django API, a web client, and a native app connected by one generated contract.
        </p>
        <div className="status" role="status">
          <span className={health.isSuccess ? 'dot ok' : 'dot'} />
          API{' '}
          {health.isPending
            ? 'checking…'
            : health.data?.data.status === 'ok'
              ? 'connected'
              : 'unavailable'}
        </div>
      </section>
      <section className="tiles" aria-label="Product surfaces">
        <article>
          <span>01</span>
          <h2>One API</h2>
          <p>OpenAPI stays the source of truth for web and mobile clients.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Two clients</h2>
          <p>Accessible web UI and native mobile UI follow their own platform conventions.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Ready to grow</h2>
          <p>Start with PostgreSQL and add optional services only when needed.</p>
        </article>
      </section>
    </main>
  );
}

function Account() {
  const queryClient = useQueryClient();
  const account = useGetUsersMe({ query: { retry: false } });
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const login = useMutation({
    mutationFn: () => sessionLogin(email, password),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: account.queryKey }),
  });
  const logout = useMutation({
    mutationFn: sessionLogout,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: account.queryKey }),
  });
  const showAccountError =
    login.isError ||
    (account.isError && !(account.error instanceof ApiError && account.error.status === 401));

  return (
    <main className="shell">
      <header>
        <Link to="/">← Home</Link>
      </header>
      <section className="hero">
        <p className="eyebrow">AUTHENTICATED AREA</p>
        <h1>Your account</h1>
        {account.isSuccess ? (
          <>
            <p className="lede">Signed in as {account.data.data.email}</p>
            <button
              className="web-button"
              onClick={() => logout.mutate()}
              disabled={logout.isPending}
            >
              Sign out
            </button>
          </>
        ) : (
          <form
            className="login-form"
            onSubmit={(event) => {
              event.preventDefault();
              login.mutate();
            }}
          >
            <label>
              Email
              <input
                autoComplete="username"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                autoComplete="current-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <button className="web-button" disabled={login.isPending}>
              {login.isPending ? 'Signing in…' : 'Sign in'}
            </button>
            {showAccountError ? (
              <p role="alert">Sign-in failed. Check the API response and try again.</p>
            ) : null}
          </form>
        )}
      </section>
    </main>
  );
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/account" element={<Account />} />
      <Route
        path="*"
        element={
          <main className="shell">
            <h1>Page not found</h1>
            <Link to="/">Return home</Link>
          </main>
        }
      />
    </Routes>
  );
}
