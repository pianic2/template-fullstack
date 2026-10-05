# Development setup

Install Docker Compose v2, Git, Node 24, Corepack/pnpm, Python 3.13 and uv. Copy `.env.example` to `.env`, then run `make setup`. `make dev` starts PostgreSQL, Django and Vite with hot reload. The example PostgreSQL credentials are local development defaults; replace them for any shared environment. On a fresh database, run `make migrate` in another terminal after the backend starts. `make down` retains database state; `make reset` removes the database volume.

Use `make doctor` to check local tool versions, package peers and environment defaults. `make logs` follows Compose logs. `make migrate` applies committed migrations. Use `make migrations` only after changing Django models and review the result before commit.

Optional local email: `make dev-email` starts Mailpit at SMTP `localhost:1025` and UI `localhost:8025`. Email uses the console backend in the default profile. S3 storage can be enabled with the `storage` Python extra and a product-owned S3-compatible endpoint; no local S3 container is supplied. The backend does not install a queue framework by default.
