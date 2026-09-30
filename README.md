# Full-stack product template

An agent-first starting point for products that need a Django API, a React web client, and an Expo mobile app. The web and mobile clients consume a shared OpenAPI contract through a generated TypeScript client. Native UI uses the maintained [`@personal-library/react-native-components`](https://www.npmjs.com/package/@personal-library/react-native-components) package.

## Overview

This repository is a product template organized as a monorepo. Django owns persistence, authentication, and HTTP behavior; PostgreSQL is the supported database. The API contract is generated from Django, committed as `openapi/openapi.yaml`, and used to generate the TypeScript client. Web and mobile apps own their platform-specific rendering.

The development Compose stack runs PostgreSQL, Django, and the web app. Expo runs on the host so it can connect to local simulators and devices. Mailpit is available through an optional Compose profile. S3-compatible storage is optional and uses a product-owned endpoint; no queue or worker is included by default.

## Tech stack

| Area | Technology |
| --- | --- |
| Backend | Python 3.13, Django 5.2, Django REST Framework, psycopg 3, uv |
| Database | PostgreSQL 18.4 |
| Web | Node.js 24, pnpm workspaces, React 19, TypeScript, Vite 8, React Router, TanStack Query |
| Mobile | Expo SDK 57, React Native 0.86.3, Expo Router, SecureStore, personal component library 0.1.0-rc.2 |
| API contract | drf-spectacular, OpenAPI, Orval-generated Fetch client |

Mobile compatibility follows the newest stable Expo/React Native line accepted by the personal library's peer dependencies. Its `rc` channel is the only prerelease dependency exception. See [mobile UI architecture](docs/architecture/mobile-ui.md) and the [dependency upgrade policy](docs/upgrades.md).

## Architecture

```mermaid
flowchart LR
  Web[React Web] -->|generated API client| API[Django API]
  Mobile[Expo Mobile] -->|generated API client| API
  API --> DB[(PostgreSQL)]
  API -. optional .-> S3[S3-compatible storage]
  Mobile --> UI[@personal-library/react-native-components]
```

The web and mobile apps share the API contract. The component library is the mobile rendering foundation and does not participate in the backend contract. S3-compatible storage is an optional backend integration; the default stack does not include it.

## Getting started

### Prerequisites

Git, Docker with Compose v2, Node.js 24, Corepack/pnpm, Python 3.13, and uv.

### Install and run

```sh
git clone <your-template-url> my-product
cd my-product
make init
make setup
cp .env.example .env
make dev
```

On a fresh database, run `make migrate` in a second terminal after the backend starts. Migrations are not applied automatically at application startup. The web app is at `http://localhost:5173`, and the API is at `http://localhost:8000` with routes under `/api/v1/`. PostgreSQL is published on loopback port 5432.

Run the Expo app from the host with:

```sh
corepack pnpm --filter @template/mobile start
```

Android emulators use API origin `http://10.0.2.2:8000`; physical devices need the host machine's LAN address. Set `EXPO_PUBLIC_API_URL` to a reachable API URL for the device; the mobile client uses its origin. Never put native secrets in Expo public environment variables.

## Configuration

The Compose backend requires a root `.env` file; start from [`.env.example`](.env.example). It contains local development defaults for database access, Django settings, service ports, API URLs, and optional email and S3 settings. Replace development credentials before using the configuration in a shared environment. Production variables and requirements are documented in [production deployment](docs/deployment/production.md).

## Development commands

Run `make help` for the full list.

| Command | Purpose |
| --- | --- |
| `make init` | Configure this clone as a new product |
| `make setup` | Install Python and JavaScript dependencies |
| `make dev` | Start PostgreSQL, Django, and the web app |
| `make dev-email` | Start the core Compose stack with Mailpit |
| `make down` | Stop services and retain database data |
| `make reset` | Remove development containers and the database volume |
| `make logs` | Follow Compose service logs |
| `make doctor` | Check local tools, environment, and mobile compatibility metadata |
| `make migrate` | Apply database migrations |
| `make migrations` | Create Django migrations after model changes |
| `make lint` | Run Python and JavaScript lint and format checks |
| `make typecheck` | Type-check backend, web, mobile, and shared packages |
| `make test` | Run backend, web, mobile, and bootstrap tests |
| `make web-e2e` | Run the Playwright browser smoke test (requires installed Chromium) |
| `make mobile-check` | Validate Expo config, dependencies, types, tests, and Android export |
| `make api-schema` | Generate the OpenAPI schema from Django |
| `make api-client` | Generate the TypeScript client from the committed schema |
| `make api-check` | Regenerate schema and client and fail on drift |
| `make check` | Run the repository quality gate; PostgreSQL and Docker are required |
| `make security-check` | Audit locked dependencies against vulnerability databases |
| `make docker-build` | Build production backend and web images |

## Testing and quality

Backend tests use PostgreSQL. Web tests use Vitest and Testing Library, with a Playwright browser smoke test. Mobile tests render the personal component library; the Expo check also runs `expo-doctor`, type-checking, and an Android Metro export. CI workflows are defined in [`.github/workflows`](.github/workflows): `ci.yml` separates backend, clients, contract, bootstrap, and Docker jobs, while `codeql.yml` runs CodeQL analysis. `make security-check` queries live vulnerability databases.

## Project structure

```text
apps/backend/       Django API, settings, domain apps, and PostgreSQL tests
apps/web/           React DOM application
apps/mobile/        Expo Router app using the personal native component library
packages/api-client OpenAPI-generated TypeScript Fetch client
packages/shared     Platform-neutral TypeScript
packages/*-config   Shared TypeScript and ESLint configuration
openapi/            Generated API contract
infra/docker/       Development and production images
docs/               Architecture, setup, agent, upgrade, and deployment guides
.agents/skills/     Repository-local agent workflows
.codex/             Project Codex settings and custom agents
```

## API contract and authentication

Django owns the versioned `/api/v1/` API, email identity, browser session/CSRF authentication, and mobile JWT endpoints. PostgreSQL is required for local development, CI, and production. Generate contract changes in this order:

```sh
make api-schema
make api-client
make api-check
```

Never hand-edit files under `packages/api-client/src/generated/`. Read the [API contract guide](docs/architecture/api-contract.md) and [authentication architecture](docs/architecture/authentication.md) for details.

The web app uses same-origin/credentialed session cookies and CSRF; it does not store browser tokens in localStorage. The mobile app stores short-lived JWT credentials in Expo SecureStore. `apps/web` uses semantic DOM elements, React Router, and TanStack Query; `apps/mobile` uses the public root exports of the personal component package for its theme, text, layout, and buttons. See [mobile setup](docs/development/mobile.md) and [library ownership rules](docs/architecture/mobile-ui.md).

## Docker and optional services

The default Compose stack is PostgreSQL, Django, and the web app. `make dev-email` adds the optional Mailpit inbox at `localhost:8025` (SMTP is `localhost:1025`). S3 support is an optional backend dependency configured against a product-owned endpoint; this template does not ship a local S3 container. A queue/worker is omitted until a product needs background work. See [Docker development setup](docs/development/setup.md).

## Deployment

Production images are built from `infra/docker/Dockerfile.backend` and `infra/docker/Dockerfile.web`, each using the `production` target. The production Compose configuration runs the backend with Gunicorn and serves the static web app with unprivileged Nginx. PostgreSQL is an external managed service, and the stack expects a trusted TLS reverse proxy. Set explicit hosts/origins, a strong secret, HTTPS proxy settings, and a managed PostgreSQL URL. Run migrations as a release step, not at application startup. See [production deployment](docs/deployment/production.md) and [`SECURITY.md`](SECURITY.md) before deploying.

## Coding agents

Start with [`AGENTS.md`](AGENTS.md), then read the nearest scoped instructions. `.codex/agents/` provides architect, backend, web, mobile, tester, and reviewer roles. Repository-local skills live in `.agents/skills/`. Mobile UI ownership is explicit: inspect and reuse the canonical library before creating generic primitives.

## Bootstrap a new product

Use GitHub **Use this template**, clone the result, then run `make init`. Non-interactive example:

```sh
python3 scripts/bootstrap.py --name "Acme Video" --slug acme-video \
  --python-package acme_video --bundle-id com.acme.video --non-interactive
```

Bootstrap renames only an explicit list of identity/configuration files, writes an ignored local initialization marker, and leaves the component package and version unchanged.

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) and the repository's [`AGENTS.md`](AGENTS.md) before making changes. API changes must regenerate the schema and client; model changes need reviewed migrations and PostgreSQL tests.

## License

This project is licensed under the [MIT License](LICENSE).
