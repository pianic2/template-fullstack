# Full-stack product template

An agent-first starting point for products that need a Django API, a React web client, and an Expo mobile app. The clients share one generated OpenAPI contract. Native UI comes from the maintained [`@personal-library/react-native-components`](https://www.npmjs.com/package/@personal-library/react-native-components) package.

## Architecture

```mermaid
flowchart LR
  Web[React Web] -->|generated API client| API[Django API]
  Mobile[Expo Mobile] -->|generated API client| API
  API --> DB[(PostgreSQL)]
  API -. optional .-> Redis[Redis / Workers]
  API -. optional .-> S3[S3 compatible storage]
  Mobile --> UI[@personal-library/react-native-components]
```

The web and mobile apps share the API contract. The component library is the mobile rendering foundation and does not participate in the backend contract.

## Stack

- Python 3.13, Django 5.2 LTS, Django REST Framework, PostgreSQL 18.4, psycopg 3, uv.
- Node.js 24 LTS, pnpm workspaces, React 19, TypeScript, Vite 8, React Router, TanStack Query.
- Expo SDK 57, React Native 0.86.3, Expo Router, SecureStore, personal component library 0.1.0-rc.2.
- drf-spectacular and Orval-generated Fetch clients with TanStack Query hooks.

Mobile compatibility is pinned to the newest stable Expo/RN line accepted by the personal library's peers. The component library's `rc` channel is the only prerelease dependency exception. See [mobile UI architecture](docs/architecture/mobile-ui.md) and [upgrade policy](docs/upgrades.md).

## Quick start

Requirements: Git, Docker with Compose v2, Node 24, Corepack/pnpm, Python 3.13 and uv.

```sh
git clone <your-template-url> my-product
cd my-product
make init
make setup
make dev
```

Copy `.env.example` to `.env` before `make dev`. On a fresh database, run `make migrate` in a second terminal after the backend starts; committed migrations are never applied at application startup. The web app is at `http://localhost:5173`, API at `http://localhost:8000`, and PostgreSQL is exposed on loopback port 5432. Start the Expo app from the host with `corepack pnpm --filter @template/mobile start`.

## Repository map

```text
apps/backend/       Django API, settings, domain apps and PostgreSQL tests
apps/web/           Accessible React DOM application
apps/mobile/        Expo Router app using the personal native component library
packages/api-client OpenAPI-generated TypeScript Fetch client
packages/shared     Platform-neutral TypeScript only
packages/*-config   Shared TypeScript and ESLint configuration
openapi/            Committed generated API contract
infra/docker/       Development and production images
docs/               Architecture, setup, agent and deployment guidance
.agents/skills/     Focused repository-local agent workflows
.codex/             Project Codex settings and custom agents
```

## Common commands

Run `make help` for the full list. Main commands: `make init`, `make setup`, `make dev`, `make down`, `make logs`, `make doctor`, `make migrate`, `make lint`, `make typecheck`, `make test`, `make api-schema`, `make api-client`, `make api-check`, `make check`.

## Backend and API contract

Django owns `/api/v1/`, email identity, browser session/CSRF authentication and mobile JWT endpoints. PostgreSQL is required for local development, CI and production. Schema and client updates are generated in order:

```sh
make api-schema
make api-client
make api-check
```

Never hand-edit OpenAPI generated client files. Read [the contract guide](docs/architecture/api-contract.md) and [authentication architecture](docs/architecture/authentication.md).

## Web development

`apps/web` uses semantic DOM elements, React Router and TanStack Query. It imports API methods from `@template/api-client`; browser auth uses same-origin/credentialed session cookies and CSRF, never localStorage tokens.

## Mobile development

`apps/mobile` is run on the host; Compose does not try to host iOS simulators or Android emulators. The app uses the personal component package's public root exports for its theme, text, layout and buttons. Follow [mobile setup](docs/development/mobile.md) and [library ownership rules](docs/architecture/mobile-ui.md).

Android emulators use API origin `http://10.0.2.2:8000`; physical devices need the host machine's LAN address. Set `EXPO_PUBLIC_API_URL` accordingly. Never put native secrets in Expo public environment variables.

## Docker and optional services

The default Compose stack is PostgreSQL, Django and web. `make dev-email` adds the optional Mailpit inbox. S3 support is an optional backend dependency configured against a product-owned endpoint; this template does not ship an unmaintained local S3 container. A queue/worker is intentionally omitted until a product needs background work. See [Docker development](docs/development/setup.md).

## Tests and CI

Backend tests target PostgreSQL; web uses Vitest and Testing Library; mobile tests render library components, then Expo/Metro export checks package resolution. `make check` runs deterministic repository gates; `make security-check` queries live vulnerability databases. CI separates backend, clients, contract, bootstrap, Docker and security checks.

## Coding agents

Start with `AGENTS.md`, then the nearest scoped instructions. `.codex/agents/` provides narrow architect, backend, web, mobile, tester and reviewer roles. Repository-local skills live in `.agents/skills/`. Mobile UI ownership is explicit: inspect and reuse the canonical library before creating generic primitives.

## Bootstrap a new product

Use GitHub **Use this template**, clone the result, then run `make init`. Non-interactive example:

```sh
python3 scripts/bootstrap.py --name "Acme Video" --slug acme-video \
  --python-package acme_video --bundle-id com.acme.video --non-interactive
```

Bootstrap renames only an explicit list of identity/config files, writes an ignored local initialization marker, and leaves the component package/version unchanged.

## Deployment philosophy

The backend image runs Gunicorn as an unprivileged user; the static web image uses unprivileged Nginx. Set a strong secret, explicit hosts/origins, HTTPS proxy settings and a managed PostgreSQL URL. Migrations are a release step, not application startup. Review [production deployment](docs/deployment/production.md) and `SECURITY.md` before deploying.

## Dependency upgrades

Dependabot proposes weekly patch/minor updates. Django upgrades follow the LTS support window; Expo/RN upgrades are accepted only after validating the personal library peer range, Expo's SDK mapping, render test and Metro export. See [upgrade policy](docs/upgrades.md).
