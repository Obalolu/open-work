# Deploying open-work on Coolify

## Prerequisites

1. A server with Coolify installed (see https://coolify.io)
2. Your GitHub account connected to Coolify
3. An OpenAI API key (or compatible provider)

## Step-by-Step Guide

### 1. Connect Your GitHub Repository

1. In Coolify dashboard, go to **Projects** → **New Project**
2. Select **Git Based** deployment
3. Choose **GitHub App** or **Deploy Key** (for private repos) or **Public Repository** (for public)
4. Paste your repository URL: `https://github.com/Obalolu/open-work.git`
5. Select the `main` branch

### 2. Select Docker Compose Build Pack

1. After selecting the repo, Coolify will ask for a build pack
2. Click **Nixpacks** and change it to **Docker Compose**
3. Configure:
   - **Base Directory:** `/`
   - **Docker Compose Location:** `docker-compose.production.yaml`

### 3. Set Environment Variables

In the Coolify UI, go to the **Environment Variables** section and add:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `OPENALEX_API_KEY` | No | OpenAlex API key for research |
| `SEMANTIC_SCHOLAR_API_KEY` | No | Semantic Scholar API key |

### 4. Configure Domains

Coolify uses Traefik as a reverse proxy. Configure domains for each service:

1. **web** service: Set your domain (e.g., `open-work.yourdomain.com`)
   - Coolify will automatically generate an SSL certificate
2. **api** service: No domain needed (internal only)

### 5. Deploy

Click **Deploy** in the Coolify dashboard. The first deployment will take a few minutes as it:
- Builds the Python API container
- Builds the Next.js frontend container
- Sets up the Docker network

### 6. Verify

Once deployed:
- Open your domain (e.g., `https://open-work.yourdomain.com`)
- You should see the open-work dashboard
- Go to Settings to verify API key configuration

## Architecture on Coolify

```
                    ┌─────────────────────────────┐
                    │      Coolify Traefik        │
                    │      (SSL + Routing)        │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
     ┌────────▼──────┐        │        ┌───────▼────────┐
     │   web:3000    │        │        │   api:8000     │
     │   (Next.js)   │◄───────┘        │   (FastAPI)    │
     │               │                 │                │
     │  Serves UI    │   Docker        │  Handles       │
     │  to browser   │   Network       │  pipeline      │
     └───────────────┘                 └───────┬────────┘
                                               │
                                      ┌────────▼────────┐
                                      │   SQLite DB     │
                                      │   (volume)      │
                                      └─────────────────┘
```

## Troubleshooting

### Build fails with "out of memory"
Add swap space to your server:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Frontend can't reach API
- Check that the API container is healthy (Coolify dashboard → api service → Health)
- Verify the `NEXT_PUBLIC_API_URL` build arg is set to `http://api:8000`

### API keeps restarting
- Check logs in Coolify dashboard → api service → Logs
- Verify all required environment variables are set

## Updating

To update after pushing new code:
1. Go to your resource in Coolify
2. Click **Redeploy** (or enable auto-deploy on push)
