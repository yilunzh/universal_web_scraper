# China Auto Sales Data API

This project provides a FastAPI backend for querying auto sales data in China, along with a Next.js frontend for visualizing the data.

## Architecture

The project consists of two main components:

1. **FastAPI Backend**: Provides SQL query execution capabilities, web scraping functionality, and other data processing features.
2. **Next.js Frontend**: Provides a natural language interface for querying the data and visualizing results.

## Setup Instructions

### Environment Variables

Create or update your `.env.local` file with the following variables:

```bash
# OpenAI API Key
OPENAI_API_KEY="your-openai-api-key"

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL="your-supabase-url"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"

# SQL API URL - URL for the FastAPI backend running the SQL service
NEXT_PUBLIC_SQL_API_URL="http://localhost:8000"
```

### Prerequisites

- Python 3.8+ for the FastAPI backend
- Node.js 16+ for the Next.js frontend
- Supabase database with auto sales data

### Installing Dependencies

For the FastAPI backend:

```bash
pip install -r requirements.txt
```

For the Next.js frontend:

```bash
cd data-chat-ui
npm install
```

## Starting the Services

### Start the FastAPI Backend

```bash
python start_api.py
```

This will start the FastAPI server on port 8000 by default. You can change the port by setting the `API_PORT` environment variable.

### Start the Next.js Frontend

```bash
cd data-chat-ui
npm run dev
```

This will start the Next.js development server on port 3000 by default.

## Features

### SQL Query API

The FastAPI backend provides a SQL query API that allows executing SQL queries against the database. The API is secured to only allow SELECT queries for security reasons.

#### API Endpoints

- `POST /sql/execute`: Execute a SQL query
- `GET /sql/setup-check`: Check if the SQL execution function exists in the database

#### Sample Query

```sql
SELECT manufacturer_name, SUM(total_units_sold) as total_sales 
FROM china_auto_sales 
WHERE year = 2020 AND manufacturer_name = '比亚迪' 
GROUP BY manufacturer_name
```

### Using the SQL Client

You can use the SQL client in your Next.js frontend to execute SQL queries:

```typescript
import { executeSqlQuery } from '@/lib/supabase';

// Example usage
async function fetchData() {
  const query = "SELECT * FROM china_auto_sales WHERE manufacturer_name = '比亚迪' LIMIT 10";
  const { data, error } = await executeSqlQuery(query);
  
  if (error) {
    console.error('Error executing query:', error);
    return;
  }
  
  console.log('Query results:', data);
}
```

## Troubleshooting

### SQL Function Setup

If you encounter errors with SQL query execution, try hitting the `/sql/setup-check` endpoint to verify that the SQL execution function exists in the database. If it doesn't exist, the endpoint will attempt to create it.

### Environment Variables

Make sure your environment variables are correctly set in both the FastAPI backend and Next.js frontend. The backend uses `.env.local` and the frontend uses `.env.local` with the `NEXT_PUBLIC_` prefix for browser-accessible variables.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Installation

```bash
pip install -e .
```

## Usage

Start the API server:
```