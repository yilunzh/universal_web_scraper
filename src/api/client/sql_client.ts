/**
 * Client for the SQL API
 * This can be used in your Next.js frontend to execute SQL queries against your backend
 */

// Declare process for TypeScript
declare const process: {
  env: {
    [key: string]: string | undefined;
  };
};

// Define the interface for SQL query requests
interface SQLQueryRequest {
  query: string;
  limit?: number;
}

// Define the interface for SQL query responses
interface SQLQueryResponse {
  data: Record<string, any>[];
  columns: string[];
  query: string;
  error?: string;
  rows_returned: number;
}

// Simple URL configuration with fallback
const API_URL = process.env.NEXT_PUBLIC_SQL_API_URL || 'http://localhost:8000';

/**
 * Execute a SQL query against the backend
 * @param query SQL query to execute
 * @param limit Maximum number of rows to return
 * @returns SQLQueryResponse object with query results
 */
export async function executeSqlQuery(
  query: string,
  limit: number = 1000
): Promise<SQLQueryResponse> {
  try {
    console.log(`Executing SQL query against ${API_URL}/sql/execute`);
    
    const response = await fetch(`${API_URL}/sql/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        limit,
      } as SQLQueryRequest),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    return result as SQLQueryResponse;
  } catch (error) {
    console.error('SQL API Error:', error);
    return {
      data: [],
      columns: [],
      query,
      error: error instanceof Error ? error.message : String(error),
      rows_returned: 0,
    };
  }
}

/**
 * Check if the SQL execution setup is ready
 * @returns Object with status of the SQL setup
 */
export async function checkSqlSetup(): Promise<{
  status: string;
  message: string;
  function_exists: boolean;
}> {
  try {
    const response = await fetch(`${API_URL}/sql/setup-check`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('SQL Setup Check Error:', error);
    return {
      status: 'error',
      message: error instanceof Error ? error.message : String(error),
      function_exists: false,
    };
  }
} 