# Vercel Deployment Guide for Universal Web Scraper

This guide will help you fix the 404 NOT_FOUND error when deploying to Vercel.

## Prerequisites

1. A Vercel account
2. Your API backend deployed and accessible via a public URL

## Steps to Fix 404 NOT_FOUND Error

### 1. Environment Variables

Make sure to set the following environment variables in your Vercel project settings:

- `OPENAI_API_KEY` - Your OpenAI API key
- `NEXT_PUBLIC_SUPABASE_URL` - Your Supabase URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Your Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key
- `NEXT_PUBLIC_SQL_API_URL` - The URL of your deployed backend API (**NOT** localhost)

### 2. Deployment Configuration

1. Make sure you're deploying from the `data-chat-ui` directory, not the root of the repository.
2. Use the following deployment command in Vercel:

```bash
cd data-chat-ui && npm install && npm run build
```

3. Set the build output directory to `.next` in your Vercel project settings.

### 3. Troubleshooting

If you're still experiencing issues:

1. Check the Vercel deployment logs for any build errors
2. Verify that your backend API is accessible from the internet
3. Ensure all environment variables are correctly set in Vercel
4. Try adding the `vercel.json` file to override configurations

## Backend Deployment

For the backend API, ensure it's deployed and accessible via a public URL. Update the `NEXT_PUBLIC_SQL_API_URL` in Vercel to point to this URL.

If your backend is not yet deployed, consider deploying it to:
- Railway
- Heroku
- DigitalOcean
- AWS
- Azure

## Additional Resources

- [Vercel Documentation](https://vercel.com/docs)
- [Next.js Deployment Documentation](https://nextjs.org/docs/deployment) 