# Deployment

Production deployment guide for Celestia Memoria using **Vercel** (frontend) and **Railway** (backend).

## Prerequisites

| Service | Purpose | Required |
|---------|---------|----------|
| [Vercel](https://vercel.com) | Next.js frontend hosting | Yes |
| [Railway](https://railway.app) | FastAPI backend hosting | Yes |
| [Supabase](https://supabase.com) | Auth + PostgreSQL database | Yes |
| [Pinecone](https://pinecone.io) | Vector storage | Yes |
| [OpenRouter](https://openrouter.ai) | LLM access (Claude Sonnet, Gemini Flash) | Yes |
| [Cohere](https://cohere.com) | Reranking | Yes |
| [Sentry](https://sentry.io) | Error tracking + performance | Recommended |

## Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Enable **email/password** authentication (Authentication → Providers)
3. Create an admin user and set their role:
   ```sql
   -- Run in Supabase SQL Editor
   UPDATE auth.users
   SET raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
   WHERE email = 'your-admin@example.com';
   ```
4. Note these values from Settings → API:
   - **Project URL** → `SUPABASE_URL`
   - **Service role key** → `SUPABASE_SERVICE_ROLE_KEY`
   - **JWT Secret** → `SUPABASE_JWT_SECRET`
   - **Anon key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Pinecone Setup

1. Create a free account at [pinecone.io](https://pinecone.io)
2. Create an index:
   - **Name**: `celestia-memoria`
   - **Dimensions**: `1536` (for OpenAI `text-embedding-3-small`)
   - **Metric**: `cosine`
   - **Region**: Choose one close to your Railway region
3. Note the **API key** from the Pinecone console

## Backend Deployment (Railway)

### 1. Create Project

1. Connect your GitHub repository in Railway
2. Create a new service
3. Set **root directory** to `services/ai-backend`
4. Railway auto-detects the Dockerfile

### 2. Environment Variables

Set these in Railway's service settings:

```env
# Mode
USE_LOCAL_MODE=false

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret

# OpenRouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=anthropic/claude-sonnet-4-5
OPENROUTER_ROUTER_MODEL=google/gemini-flash-1.5

# Pinecone
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=celestia-memoria
PINECONE_ENVIRONMENT=us-east-1-aws

# Cohere
COHERE_API_KEY=your-cohere-key
COHERE_RERANK_MODEL=rerank-english-v3.0

# CORS — must match your Vercel URL
FRONTEND_URL=https://celestia-memoria.vercel.app

# Server
PORT=8000

# Sentry (optional)
SENTRY_DSN=https://...@sentry.io/...
```

### 3. Verify

After deployment, check the health endpoint:

```bash
curl https://your-backend.up.railway.app/health
# {"status":"ok","version":"0.1.0","mode":"production"}
```

## Frontend Deployment (Vercel)

### 1. Import Project

1. Import your GitHub repository in Vercel
2. Set **root directory** to `apps/web`
3. Framework preset: **Next.js**
4. Build command: `pnpm build`
5. Install command: `pnpm install`

### 2. Environment Variables

Set in Vercel project settings (Settings → Environment Variables):

```env
NEXTAUTH_URL=https://celestia-memoria.vercel.app
NEXTAUTH_SECRET=<generate with: openssl rand -base64 32>
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
BACKEND_URL=https://your-backend.up.railway.app

# Sentry (optional)
SENTRY_DSN=https://...@sentry.io/...
```

### 3. Verify

Visit your Vercel URL — you should see the login page.

## Sentry Setup (Recommended)

1. Create two Sentry projects: one for **Next.js**, one for **Python (FastAPI)**
2. Add the respective `SENTRY_DSN` to Vercel and Railway environment variables
3. Frontend: `@sentry/nextjs` handles error boundaries + performance tracing
4. Backend: `sentry-sdk[fastapi]` captures exceptions + request tracing
5. Configure source maps upload for readable stack traces in Vercel builds

## Custom Domain

1. Add your domain in Vercel project settings (Settings → Domains)
2. Configure DNS:
   - **CNAME** record pointing to `cname.vercel-dns.com`
   - Or **A** record to Vercel's IP
3. Vercel auto-provisions SSL via Let's Encrypt
4. Update these values after domain setup:
   - `NEXTAUTH_URL` in Vercel → your custom domain
   - `FRONTEND_URL` in Railway → your custom domain

## Post-Deployment Checklist

- [ ] Backend `/health` returns `{"status":"ok","mode":"production"}`
- [ ] Frontend loads the login page
- [ ] User can sign in with Supabase credentials
- [ ] Admin user can upload a PDF via Upload Dialog
- [ ] Document appears in ingestion logs (check Railway logs)
- [ ] Chat query returns a cited answer
- [ ] Non-admin user gets 403 on document upload
- [ ] CORS works (no blocked requests in browser console)
- [ ] Sentry captures a test error (if configured)

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| 401 on all requests | JWT secret mismatch | Ensure `SUPABASE_JWT_SECRET` matches Supabase project |
| CORS errors | Frontend URL mismatch | Update `FRONTEND_URL` in Railway to match Vercel URL |
| 502 from /api/chat | Backend unreachable | Check `BACKEND_URL` in Vercel points to Railway URL |
| Ingestion fails | Missing Pinecone index | Create index with dimension=1536, metric=cosine |
| Empty search results | No documents ingested | Upload and ingest a PDF first |
| Login page loops | NEXTAUTH_URL wrong | Must match exact Vercel domain (with https://) |
