# Security

Security model and practices for Celestia Memoria.

## Authentication

### Production Mode

- **Provider**: Supabase Auth (email/password)
- **Token format**: JWT signed with HS256
- **Flow**:
  1. User signs in via NextAuth → Supabase `signInWithPassword`
  2. JWT stored in NextAuth session (JWT strategy, no server-side sessions)
  3. Frontend includes Bearer token in all API requests
  4. Backend `SupabaseAuthMiddleware` validates JWT signature and expiry
- **Secret**: `SUPABASE_JWT_SECRET` must match between the Supabase project and the backend

### Local Development Mode

- Auth middleware bypassed entirely
- Dev user injected: `user_id=dev-local-user`, `role=admin`
- No tokens required — all endpoints accessible without authentication

## Authorization

Role-based access control with two roles:

| Role | Chat / Query | Document Upload | Description |
|------|-------------|-----------------|-------------|
| `controller` | Yes | No | Default role for new users |
| `admin` | Yes | Yes | Can ingest documents |

Roles are stored in Supabase `app_metadata.role`. To promote a user to admin:

```sql
UPDATE auth.users
SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
WHERE email = 'user@example.com';
```

## Data Protection

### At Rest

- **Production**: Vectors stored in Pinecone (encrypted at rest). Metadata stored in Supabase PostgreSQL (encrypted at rest). Both services are SOC 2 compliant.
- **Local mode**: SQLite database file on disk. Ensure appropriate filesystem permissions.

### In Transit

- All client-to-server communication over HTTPS (enforced by Vercel and Railway)
- All backend-to-service communication uses TLS (Pinecone, Supabase, OpenRouter, Cohere APIs)

### Sensitive Data Handling

- API keys stored exclusively in environment variables, never in code
- JWT secrets never logged or exposed in error responses
- User passwords never stored by the application (delegated to Supabase)
- Error responses use generic messages — no stack traces exposed to clients
- Sentry strips sensitive headers before transmission

## CORS Policy

Configured in `services/ai-backend/app/main.py`:

- **Allowed origins**: `FRONTEND_URL` environment variable + `http://localhost:3000`
- **Credentials**: Enabled
- **Methods**: All
- **Headers**: All

In production, `FRONTEND_URL` must match the exact Vercel deployment URL.

## Input Validation

### Backend

- Pydantic models validate all request bodies with type checking
- ICAO codes validated against regex `^[A-Z]{4}$` or exact string `GLOBAL`
- Document types validated against a strict whitelist
- SQL injection prevented via parameterized queries and column whitelists (SQLite)
- Query length limits enforced
- PDF file size limits enforced before processing

### Frontend

- NextAuth handles CSRF protection for auth endpoints
- File uploads restricted to PDF format, max 100MB
- Form inputs validated before submission
- Markdown rendering sanitized to prevent XSS

## Known Limitations

Tracked for future improvement:

1. **JWT audience not validated** — `verify_aud=False` in JWT decode. Supabase JWTs don't include a custom audience claim by default. Risk is low when the JWT secret is kept secure.
2. **NextAuth beta** — Using next-auth 5.0.0-beta.30. Monitor for security patches.
3. **No rate limiting** — API endpoints are not rate-limited. A future update will add per-user rate limiting middleware.

## Responsible Disclosure

If you discover a security vulnerability:

1. **Do NOT** open a public GitHub issue
2. Email the maintainer directly with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
3. Allow reasonable time for a fix before any public disclosure

## Deployment Security Checklist

- [ ] All API keys set as environment variables (not in code or committed to git)
- [ ] `SUPABASE_JWT_SECRET` matches the Supabase project setting
- [ ] `NEXTAUTH_SECRET` is a strong random value (`openssl rand -base64 32`)
- [ ] `FRONTEND_URL` in backend matches the actual production domain
- [ ] `USE_LOCAL_MODE=false` in production
- [ ] HTTPS enforced on all endpoints (Vercel and Railway do this by default)
- [ ] Admin users have strong passwords
- [ ] Supabase RLS policies configured for data tables
- [ ] Sentry configured for error monitoring
- [ ] `.env` files excluded from git (verify `.gitignore`)
