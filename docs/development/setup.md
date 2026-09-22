# Development setup

Install Docker Compose v2, Git, Node 24, Corepack/pnpm, Python 3.13 and uv. Copy `.env.example` to `.env`, then run `make setup`. `make dev` starts PostgreSQL, Django and Vite with hot reload. `make down` retains database state; `make reset` removes the database volume.

Use `make doctor` to check local tool versions, package peers and environment defaults. `make logs` follows Compose logs. `make migrate` applies committed migrations. Use `make migrations` only after changing Django models and review the result before commit.

Optional local services: `make dev-storage` enables the S3-compatible MinIO adapter and Mailpit. Their endpoints are MinIO `localhost:9000` / console `9001`, Mailpit SMTP `localhost:1025` / UI `8025`. Email uses the console backend in the default profile. The backend does not install a queue framework by default.
