# Security policy

Report vulnerabilities privately to the repository maintainers. Do not disclose exploitable issues in public issues.

## Deployment requirements

- Keep `.env` and production secrets out of Git. `.env.example` contains development placeholders only.
- Use a unique Django secret from a secret manager, `DEBUG=False`, explicit hosts, HTTPS and explicit CORS/CSRF origins.
- Browser sessions are HttpOnly and Secure in production; unsafe cookie-authenticated requests require CSRF. Never use localStorage for browser auth secrets.
- Mobile tokens belong in Expo SecureStore. Never embed secrets in `EXPO_PUBLIC_*` variables.
- Treat user uploads as untrusted; validate size/type, scan where appropriate, and serve from a separate origin with safe content headers.
- Production containers run non-root where practical. Migrations run as a deployment step.
- Keep dependencies current through Dependabot and review security alerts. CI runs CodeQL.

See `docs/architecture/authentication.md` and `docs/deployment/production.md` before exposing the API publicly.
