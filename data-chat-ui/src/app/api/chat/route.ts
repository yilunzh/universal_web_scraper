import { NextResponse } from 'next/server';
import { processQuestion, generateInsights } from '@/lib/openai';
import { executeSqlQuery } from '@/lib/supabase';
import { OpenAIResponse } from '@/lib/types';

export async function POST(request: Request) {
  try {
    const { question, chatHistory } = await request.json();

    if (!question) {
      return NextResponse.json(
        { error: 'Question is required' },
        { status: 400 }
      );
    }

    // Process the question using OpenAI
    const response: OpenAIResponse = await processQuestion({
      question,
      chatHistory,
    });

    // If OpenAI suggests we need to ask a follow-up question
    if (response.type === 'follow_up') {
      return NextResponse.json({
        type: 'follow_up',
        content: response.content,
      });
    }

    // If OpenAI provides a SQL query
    if (response.type === 'sql' && response.sqlQuery) {
      try {
        // Execute the SQL query against Supabase
        const { data, error } = await executeSqlQuery(response.sqlQuery);

        if (error) {
          return NextResponse.json(
            {
              type: 'error',
              content: 'Error executing SQL query',
              error: error.toString(),
            },
            { status: 500 }
          );
        }

        // If we have data, generate insights
        let insight = '';
        if (data && data.length > 0 && response.insightTemplate) {
          insight = await generateInsights({
            data,
            question,
            sqlQuery: response.sqlQuery,
            insightTemplate: response.insightTemplate || '',
          });
        } else if (data && data.length === 0) {
          insight = 'No data found for your query.';
        }

        // Determine the best way to display this data
        const displayType = determineDisplayType(response.sqlQuery, data || []);

        return NextResponse.json({
          type: 'data',
          content: response.content,
          data,
          sqlQuery: response.sqlQuery,
          reasoning: response.reasoning || '',
          insight,
          displayType,
        });
      } catch (error: any) {
        console.error('SQL execution error:', error);
        return NextResponse.json(
          {
            type: 'error',
            content: 'Error executing the query',
            error: error.message || error.toString(),
          },
          { status: 500 }
        );
      }
    }

    // If something went wrong with the OpenAI response
    return NextResponse.json(
      {
        type: 'error',
        content: 'Invalid response from AI',
      },
      { status: 500 }
    );
  } catch (error: any) {
    console.error('API route error:', error);
    return NextResponse.json(
      {
        type: 'error',
        content: 'Error processing your request',
        error: error.message || error.toString(),
      },
      { status: 500 }
    );
  }
}

// Helper function to determine the best visualization type based on the query and data
function determineDisplayType(sqlQuery: string, data: any[]): 'table' | 'bar' | 'line' | 'pie' {
  if (!data || data.length === 0) return 'table';

  const query = sqlQuery.toLowerCase();
  const firstRow = data[0];
  const columns = Object.keys(firstRow || {});

  // Time series data (contains year/month and has ordered results) - use line chart
  if (
    (query.includes('year') || query.includes('month')) &&
    (query.includes('order by year') || query.includes('order by month'))
  ) {
    return 'line';
  }

  // Comparison between categories (typically fewer than 10 items) - use bar chart
  if (
    data.length < 10 && 
    columns.some(col => ['manufacturer_name', 'model_name'].includes(col.toLowerCase()))
  ) {
    return 'bar';
  }

  // Market share or percentage distribution - use pie chart
  if (
    query.includes('percentage') || 
    query.includes('market share') ||
    query.includes('proportion')
  ) {
    return 'pie';
  }

  // Default to table for complex data or when uncertain
  return 'table';
} 