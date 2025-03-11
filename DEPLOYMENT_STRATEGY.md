# Universal Web Scraper: Full-Stack Deployment Strategy

This document outlines a comprehensive deployment strategy for the Universal Web Scraper application, which consists of a Next.js frontend and a FastAPI backend.

## Architecture Overview

```
┌────────────────────┐      ┌─────────────────────┐      ┌────────────────┐
│                    │      │                     │      │                │
│   Next.js Frontend │◄────►│   FastAPI Backend   │◄────►│   Supabase DB  │
│   (Vercel)         │      │   (Railway/Render)  │      │                │
│                    │      │                     │      │                │
└────────────────────┘      └─────────────────────┘      └────────────────┘
```

The application uses:
- **Frontend**: Next.js 15.x hosted on Vercel
- **Backend**: FastAPI hosted on Railway, Render, or similar
- **Database**: Supabase for data storage

## Deployment Options

### Option 1: Vercel + Railway (Recommended)

**Why this option**: Best developer experience, seamless deployments, and good free tier options.

#### Frontend (Vercel)
- Easy GitHub integration
- Built-in preview deployments for PRs
- Edge network for fast content delivery

#### Backend (Railway)
- Simple Python app deployment
- Automatic deployments from GitHub
- Good monitoring and logs

### Option 2: Vercel + Render

Similar to Option 1, but using Render for the backend.

### Option 3: All-in-one with DigitalOcean App Platform

Host both frontend and backend on DigitalOcean App Platform for a unified experience.

## Step-by-Step Deployment Guide

### 1. Prepare Your Project for Deployment

#### Backend Preparation

1. **Create/update the following files in your project root**:

   **`Procfile`** (for Heroku/Railway compatibility):
   ```
   web: python -m scripts.run_sql_api
   ```

   **`runtime.txt`** (for Python version specification):
   ```
   python-3.9.18
   ```

   **`requirements-prod.txt`** (optimized for production):
   ```
   fastapi>=0.95.0
   uvicorn[standard]>=0.21.0
   python-dotenv>=1.0.0
   supabase>=1.0.3
   httpx>=0.24.0
   pydantic>=2.0.0
   openai>=1.0.0
   requests>=2.28.0
   beautifulsoup4>=4.12.0
   pandas>=2.0.0
   numpy>=1.24.0
   gunicorn>=20.1.0
   ```

2. **Update the backend startup script** (`scripts/run_sql_api.py`):
   ```python
   import sys
   import os
   from pathlib import Path
   from dotenv import load_dotenv

   # Add project root to Python path
   project_root = Path(__file__).parent.parent
   sys.path.append(str(project_root))

   # Load environment variables
   load_dotenv()
   load_dotenv(project_root / '.env.local')

   import uvicorn

   if __name__ == "__main__":
       # Support cloud providers' PORT environment variable
       port = int(os.environ.get("PORT", os.environ.get("API_PORT", 8000)))
       host = "0.0.0.0"
       reload_mode = os.environ.get("ENVIRONMENT", "development").lower() != "production"
       
       print(f"Starting FastAPI server on {host}:{port} (reload: {reload_mode})...")
       uvicorn.run("src.api.main:app", host=host, port=port, reload=reload_mode)
   ```

3. **Add CORS support to the FastAPI application** (`src/api/main.py`):
   ```python
   from fastapi import FastAPI
   from fastapi.middleware.cors import CORSMiddleware
   from .routers import scraper
   from .routers import sql
   from .jobs import router as jobs_router

   app = FastAPI(title="China Auto Sales Scraper API")

   # Add CORS middleware
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # In production, replace with specific origins
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

   # Include routers
   app.include_router(scraper.router, prefix="/scraper", tags=["scraper"])
   app.include_router(jobs_router, prefix="/api")
   app.include_router(sql.router, prefix="/sql", tags=["sql"])
   ```

#### Frontend Preparation

1. **Add a custom `vercel.json` in the data-chat-ui directory**:
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "package.json",
         "use": "@vercel/next"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "/"
       }
     ]
   }
   ```

2. **Update Next.js configuration** (`data-chat-ui/next.config.ts`):
   ```typescript
   import type { NextConfig } from "next";

   const nextConfig: NextConfig = {
     output: 'standalone',
     async rewrites() {
       return [
         {
           source: '/api/:path*',
           destination: process.env.NEXT_PUBLIC_SQL_API_URL + '/:path*' // Proxy API requests
         }
       ];
     }
   };

   export default nextConfig;
   ```

### 2. Deploy the Backend (Railway)

1. **Sign up for Railway**: https://railway.app/

2. **Create a new project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your GitHub account and select your repository

3. **Configure the project**:
   - Set the root directory to `/` (project root)
   - Set the build command: `pip install -r requirements-prod.txt`
   - Set the start command: `python -m scripts.run_sql_api`

4. **Add environment variables**:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `SUPABASE_URL` - Your Supabase URL
   - `SUPABASE_KEY` - Your Supabase API key
   - `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key
   - `ENVIRONMENT=production` - Flags the environment as production
   - Any other required environment variables

5. **Deploy**:
   - Railway will automatically deploy your app
   - Note the URL provided by Railway (e.g., `https://your-app-name.up.railway.app`)

### 3. Deploy the Frontend (Vercel)

1. **Sign up for Vercel**: https://vercel.com/

2. **Create a new project**:
   - Connect your GitHub repository
   - Set the root directory to `/data-chat-ui`
   - Set the framework preset to "Next.js"

3. **Configure environment variables**:
   - `NEXT_PUBLIC_SQL_API_URL` - The URL of your deployed Railway backend (e.g., `https://your-app-name.up.railway.app`)
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `NEXT_PUBLIC_SUPABASE_URL` - Your Supabase URL
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Your Supabase anonymous key
   - `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key

4. **Deploy**:
   - Click "Deploy"
   - Vercel will build and deploy your frontend
   - Note the URL provided by Vercel (e.g., `https://your-app-name.vercel.app`)

## Environment Variables Management

### Strategy for Managing Environment Variables

1. **Local Development**:
   - Use `.env.local` files in both frontend and backend directories
   - Never commit these files to Git (ensure they're in `.gitignore`)

2. **Production**:
   - Store environment variables in the respective platform dashboards (Vercel, Railway)
   - Use platform-specific secret management

3. **CI/CD**:
   - Store sensitive variables as GitHub Secrets if using GitHub Actions
   - Reference these secrets in your workflow files

## CI/CD Pipeline

### GitHub Actions Workflow

Create a `.github/workflows/deploy.yml` file:

```yaml
name: Deploy Application

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd data-chat-ui && npm ci
      - name: Run tests
        run: cd data-chat-ui && npm test

  deploy-backend:
    needs: [test-backend]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      - name: Deploy to Railway
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

  deploy-frontend:
    needs: [test-frontend, deploy-backend]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./data-chat-ui
```

## Database and Infrastructure Considerations

### Supabase Setup

1. **Create a Supabase project**: https://supabase.com/
2. **Set up the database schema** according to your application needs
3. **Configure RLS (Row Level Security)** for enhanced security
4. **Create API keys** and add them to your environment variables

### Scaling Considerations

1. **Database Scaling**:
   - Monitor database performance
   - Increase capacity as needed
   - Consider read replicas for heavy read workloads

2. **Backend Scaling**:
   - Railway automatically scales based on demand
   - Monitor CPU and memory usage

3. **Frontend Scaling**:
   - Vercel automatically scales edge deployments
   - Use ISR (Incremental Static Regeneration) for dynamic content that can be cached

## Monitoring and Maintenance

### Monitoring Setup

1. **Backend Monitoring**:
   - Use Railway's built-in monitoring
   - Consider adding Sentry for error tracking

2. **Frontend Monitoring**:
   - Use Vercel Analytics
   - Consider adding Sentry for error tracking

### Regular Maintenance Tasks

1. **Dependency Updates**:
   - Regularly update dependencies in both frontend and backend
   - Use Dependabot to automate updates

2. **Database Maintenance**:
   - Regular backups (Supabase handles this)
   - Performance optimization

## Security Considerations

1. **API Security**:
   - Use proper authentication for API endpoints
   - Implement rate limiting
   - Validate and sanitize all inputs

2. **Frontend Security**:
   - Implement proper CSP (Content Security Policy)
   - Use HTTPS only
   - Handle user authentication securely

3. **Environment Security**:
   - Never expose sensitive keys in client-side code
   - Rotate API keys regularly
   - Use the principle of least privilege

## Disaster Recovery

1. **Backup Strategy**:
   - Regular database backups (automated by Supabase)
   - Code versioning through Git

2. **Recovery Process**:
   - Document steps for recovery from backups
   - Test recovery process periodically

## Communication Between Services

### API Communication

1. **Frontend to Backend**:
   - Use fetch API with appropriate error handling
   - Consider using SWR or React Query for data fetching

2. **Backend to Database**:
   - Use Supabase client with connection pooling
   - Implement proper error handling and retries

## Conclusion

This deployment strategy provides a robust foundation for deploying and maintaining your Universal Web Scraper application. By leveraging modern cloud platforms like Vercel, Railway, and Supabase, you can achieve a scalable, maintainable, and cost-effective deployment. 