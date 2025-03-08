import { NextResponse } from 'next/server';
import OpenAI from 'openai';
import { executeSqlQuery } from '@/lib/supabase';
import { generateInsights } from '@/lib/openai';

// Initialize the OpenAI client with API key from environment
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

export async function POST(request: Request) {
  try {
    const { originalQuery, suggestion, originalResults } = await request.json();

    if (!originalQuery || !suggestion) {
      return NextResponse.json(
        { 
          error: 'Original query and suggestion are required',
          modifiedQuery: originalQuery || '' // Return original if available
        },
        { status: 400 }
      );
    }

    console.log(`Modifying query - Original: ${originalQuery}`);
    console.log(`Suggestion: ${suggestion}`);

    try {
      // Generate the modified query using OpenAI
      const modifiedQueryResponse = await generateModifiedQuery({
        originalQuery,
        suggestion,
        originalResults
      });

      if (!modifiedQueryResponse.sqlQuery) {
        return NextResponse.json({
          modifiedQuery: originalQuery,
          explanation: "Could not modify the query. Using the original query instead.",
          data: originalResults || [],
          changes: []
        });
      }

      console.log(`Modified query: ${modifiedQueryResponse.sqlQuery}`);

      // Execute the modified query
      const { data, error } = await executeSqlQuery(modifiedQueryResponse.sqlQuery);

      if (error) {
        return NextResponse.json(
          {
            error: `Error executing the modified query: ${error instanceof Error ? error.message : String(error)}`,
            modifiedQuery: modifiedQueryResponse.sqlQuery
          },
          { status: 500 }
        );
      }

      // Determine the best display type for the data
      const displayType = determineDisplayType(modifiedQueryResponse.sqlQuery, data);

      // Try to generate a basic insight for the modified query
      let insight = '';
      try {
        if (data && data.length > 0) {
          insight = await generateInsights({
            data,
            question: suggestion,
            sqlQuery: modifiedQueryResponse.sqlQuery,
            insightTemplate: `Provide a brief insight about the data returned from this modified query: ${suggestion}`
          });
        }
      } catch (insightError) {
        console.error('Error generating insight:', insightError);
      }

      return NextResponse.json({
        modifiedQuery: modifiedQueryResponse.sqlQuery,
        explanation: modifiedQueryResponse.explanation,
        changes: modifiedQueryResponse.changes,
        data,
        displayType,
        insight
      });
    } catch (error) {
      console.error('Error modifying query:', error);
      return NextResponse.json(
        {
          error: `Failed to modify query: ${error instanceof Error ? error.message : 'Unknown error'}`,
          modifiedQuery: originalQuery
        },
        { status: 500 }
      );
    }
  } catch (error) {
    console.error('Error processing request:', error);
    return NextResponse.json(
      { error: 'Failed to process request' },
      { status: 500 }
    );
  }
}

interface ModifyQueryProps {
  originalQuery: string;
  suggestion: string;
  originalResults?: any[];
}

interface ModifiedQueryResponse {
  sqlQuery: string;
  explanation: string;
  changes: {
    type: string;
    description: string;
  }[];
}

// Generate a modified SQL query based on natural language suggestion
async function generateModifiedQuery({ 
  originalQuery, 
  suggestion,
  originalResults 
}: ModifyQueryProps): Promise<ModifiedQueryResponse> {
  try {
    // Send to OpenAI for modification
    const response = await openai.chat.completions.create({
      model: 'o3-mini',
      messages: [
        {
          role: 'system',
          content: `You are an expert SQL query generator specializing in modifying existing SQL queries based on user suggestions.
          
You will be given an original SQL query and a natural language suggestion for how to modify it.
You MUST generate a new SQL query that incorporates the suggested changes. The modified query should 
be different from the original query, reflecting the user's suggestion.

Your response should be in JSON format with the following structure:
{
  "sqlQuery": "The complete modified SQL query",
  "explanation": "A clear explanation of the changes made to the original query",
  "changes": [
    {
      "type": "addition|modification|removal",
      "description": "Description of a specific change"
    }
  ]
}

Follow these guidelines:
1. Always return valid SQL that will execute successfully
2. Maintain the security restrictions (SELECT queries only)
3. Use clear, descriptive column aliases for any new or modified columns
4. Preserve the original sort order unless explicitly asked to change it
5. Document all changes in the explanation and changes list
6. YOUR MOST IMPORTANT RESPONSIBILITY: Make actual changes to the query based on the suggestion
7. Do not return the original query unchanged - you must modify it according to the suggestion
8. If the suggestion mentions adding a column, condition, or calculation, be sure to implement it
9. The generated query MUST be different from the original query`
        },
        {
          role: 'user',
          content: `Original SQL Query:
${originalQuery}

${originalResults ? `Sample of original results:
${JSON.stringify(originalResults?.slice(0, 3))}` : ''}

User suggestion: "${suggestion}"

Please modify the query according to this suggestion. The modified query must be different from the original query.`
        }
      ],
      response_format: { type: 'json_object' },
    });

    const content = response.choices[0].message.content;
    if (!content) {
      throw new Error('No content in response');
    }

    let result;
    try {
      result = JSON.parse(content);
    } catch (e) {
      console.error('Failed to parse OpenAI response:', content);
      throw new Error('Invalid response from OpenAI');
    }

    // Add this helper function to better detect query changes
    const stripSqlCommentsAndWhitespace = (sql: string): string => {
      if (!sql) return '';
      // Remove SQL comments (both single-line and multi-line) and normalize whitespace
      return sql
        .replace(/--.*$/gm, '') // Remove single-line comments
        .replace(/\/\*[\s\S]*?\*\//g, '') // Remove multi-line comments
        .replace(/\s+/g, ' ') // Normalize whitespace to single spaces
        .trim();
    };

    // In the check for identical queries, use the helper function
    // Check if the modified query is actually different from the original
    const strippedOriginal = stripSqlCommentsAndWhitespace(originalQuery);
    const strippedResult = stripSqlCommentsAndWhitespace(result.sqlQuery);
    const queriesAreIdentical = strippedOriginal === strippedResult;

    if (queriesAreIdentical) {
      console.warn("OpenAI returned the same query without modifications", {
        suggestion,
        originalQueryStart: originalQuery.substring(0, 100) + "...",
        resultQuery: result.sqlQuery.substring(0, 100) + "..."
      });
      
      // Try to make a simple modification to show the system is working
      // This is a fallback for demonstration purposes
      let fallbackQuery = originalQuery;
      
      // Add a simple comment to the query explaining the issue
      fallbackQuery = "-- Note: AI couldn't modify the query as requested\n-- Suggestion: " + suggestion + "\n" + fallbackQuery;
      
      console.log("Generated fallback query with comments:", {
        fallbackQueryStart: fallbackQuery.substring(0, 150) + "..."
      });
      
      return {
        sqlQuery: fallbackQuery,
        explanation: `The AI attempted to modify the query based on "${suggestion}" but couldn't generate a different query. This could be because the suggestion wasn't clear or applicable to this query structure.`,
        changes: [
          {
            type: "information",
            description: "No changes were made to the query logic. The suggestion may not be applicable to this query structure."
          }
        ]
      };
    }
    
    return result;
  } catch (error) {
    console.error('OpenAI processing error:', error);
    throw error;
  }
}

// Helper function to determine the best visualization type based on the query and data
function determineDisplayType(sqlQuery: string, data: any[]): 'table' | 'bar' | 'line' | 'pie' {
  if (!data || data.length === 0) return 'table';

  const query = sqlQuery.toLowerCase();
  const firstRow = data[0];
  if (!firstRow) return 'table';
  
  const columns = Object.keys(firstRow || {});

  // Time series data (contains year/month and has ordered results) - use line chart
  if (
    (query.includes('year') || query.includes('month') || query.includes('date')) &&
    (query.includes('order by year') || 
     query.includes('order by month') || 
     query.includes('order by date') ||
     columns.includes('year') || 
     columns.includes('month'))
  ) {
    return 'line';
  }

  // Comparison between categories (typically fewer than 10 items) - use bar chart
  if (
    data.length < 10 && 
    columns.some(col => ['manufacturer_name', 'model_name', 'brand', 'category'].includes(col.toLowerCase()))
  ) {
    return 'bar';
  }

  // Market share or percentage distribution - use pie chart
  if (
    query.includes('percentage') || 
    query.includes('market share') ||
    query.includes('proportion') ||
    columns.some(col => col.includes('share') || col.includes('percent'))
  ) {
    return 'pie';
  }

  // Default to table for complex data or when uncertain
  return 'table';
} 