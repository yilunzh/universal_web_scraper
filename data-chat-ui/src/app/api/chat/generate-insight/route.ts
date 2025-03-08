import { NextResponse } from 'next/server';
import { generateInsights } from '@/lib/openai';

export async function POST(request: Request) {
  try {
    const { data, sqlQuery, question } = await request.json();

    if (!data || !sqlQuery) {
      return NextResponse.json(
        { error: 'Data and SQL query are required' },
        { status: 400 }
      );
    }

    // Generate insights based on the data and query
    let insight = '';
    try {
      insight = await generateInsights({
        data,
        question,
        sqlQuery,
        insightTemplate: `Provide insights about the data returned from this modified query: ${question}. Focus on key trends, patterns, or notable observations.`,
      });
    } catch (error) {
      console.error('Error generating insights:', error);
      insight = 'Could not generate insights for this data.';
    }

    return NextResponse.json({
      insight
    });
  } catch (error) {
    console.error('Insight generation error:', error);
    return NextResponse.json(
      { error: 'Failed to generate insights' },
      { status: 500 }
    );
  }
} 