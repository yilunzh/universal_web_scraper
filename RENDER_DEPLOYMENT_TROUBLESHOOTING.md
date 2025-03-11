# Render Deployment Troubleshooting Guide

## Fixing the f-string Syntax Error

We encountered a syntax error in the `src/api/jobs.py` file when deploying to Render:

```
SyntaxError: f-string expression part cannot include a backslash
```

### The Problem

The error occurs because Python f-strings cannot contain backslashes inside the expression part (the part inside the curly braces `{}`). In our code, we were trying to use string concatenation inside an f-string expression, which included newline characters (`\n`).

### The Fix

We've fixed the issue by changing:

```python
{"".join(f"    {url}\n" for url in failed_url_list)}
```

To:

```python
{"\n".join([f"    {url}" for url in failed_url_list])}
```

This approach properly joins the strings with newlines without using a backslash inside the f-string expression.

## Deploying to Render - Step by Step

After fixing the syntax error, follow these steps to deploy to Render:

1. **Commit and push the fixed code** to your GitHub repository.

2. **Create a new Web Service on Render**:
   - Sign in to your Render account
   - Click "New" and select "Web Service"
   - Connect your GitHub repository
   - Configure the service:
     - **Name**: `universal-web-scraper-api`
     - **Environment**: Python
     - **Build Command**: `pip install -r requirements-prod.txt`
     - **Start Command**: `python -m scripts.run_sql_api`

3. **Configure environment variables**:
   - Add the following variables:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `SUPABASE_URL`: Your Supabase URL
     - `SUPABASE_KEY`: Your Supabase API key
     - `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role key
     - `ENVIRONMENT`: `production`

4. **Deploy your service**:
   - Click "Create Web Service"
   - Wait for the deployment to complete

5. **Test your API**:
   - Once deployed, access `https://[your-service-name].onrender.com/docs`
   - This will open the FastAPI Swagger UI where you can test your endpoints

## Common Deployment Issues on Render

### 1. Package Installation Failures

If packages fail to install:
- Check `requirements-prod.txt` for compatibility issues
- Consider pinning specific package versions
- Monitor the build logs for detailed error messages

### 2. Runtime Errors

If your app starts but crashes:
- Check Render logs for detailed error messages
- Verify that all environment variables are correctly set
- Ensure database connections are properly configured

### 3. CORS Issues

If you encounter CORS errors:
- Verify that the CORS middleware is properly configured in your FastAPI app
- Consider restricting `allow_origins` to specific domains in production

### 4. Database Connection Issues

If your app can't connect to Supabase:
- Verify your Supabase credentials
- Check Supabase connection settings
- Test your database connection locally before deploying

## Monitoring Your Deployment

- Use Render's built-in logging to monitor your application
- Set up alerts for application errors
- Monitor usage to determine if you need to upgrade your plan

## Next Steps After Successful Deployment

1. **Deploy the frontend** on Vercel, pointing to your Render backend URL
2. **Test the full application** to ensure proper communication
3. **Set up monitoring and logging** for production use 