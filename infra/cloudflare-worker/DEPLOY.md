# ELF OAuth Worker Deployment

One-time setup to enable GitHub OAuth for all ELF users.

## Prerequisites

- Cloudflare account (free tier works)
- GitHub OAuth App credentials
- Node.js installed

## Step 1: Create GitHub OAuth App

1. Go to GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
2. Fill in:
   - **Application name**: `ELF Dashboard`
   - **Homepage URL**: `https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF`
   - **Authorization callback URL**: `http://localhost:8888/api/auth/callback`
3. Click "Register application"
4. Copy the **Client ID**
5. Generate and copy a **Client Secret**

## Step 2: Deploy Worker

```bash
cd infra/cloudflare-worker

# Install wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Set secrets (won't be in code)
wrangler secret put GITHUB_CLIENT_ID
# Paste your Client ID when prompted

wrangler secret put GITHUB_CLIENT_SECRET
# Paste your Client Secret when prompted

# Deploy
wrangler deploy
```

## Step 3: Update Worker URL (if different)

The default URL is `https://elf-oauth.spacehunterz.workers.dev`

If your worker deployed to a different URL, update it in:
- `apps/dashboard/backend/routers/auth.py` line 29

## That's It

New users can now:
1. Clone the repo
2. Run `npm run dev` in `apps/dashboard`
3. Click "Login with GitHub"
4. It just works

## How It Works

```
User clicks Login
    ↓
Redirect to GitHub OAuth (using client_id from worker)
    ↓
GitHub redirects back with code
    ↓
Backend calls worker to exchange code for token
    ↓
Worker uses client_secret to get access token
    ↓
Backend creates session, user is logged in
```

## Security Notes

- Client ID is public (safe to expose)
- Client Secret is stored only in Cloudflare Worker secrets
- Worker only accepts requests from allowed origins
- Sessions are encrypted with Fernet (auto-generated key if not set)

## Testing Locally

To test the worker locally:

```bash
cd infra/cloudflare-worker
wrangler dev
```

Then set `OAUTH_WORKER_URL=http://localhost:8787` in your environment.
