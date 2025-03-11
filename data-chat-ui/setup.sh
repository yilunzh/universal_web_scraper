#!/bin/bash

# Create the lib directory if it doesn't exist
mkdir -p ./src/lib

# Check if utils.ts exists in lib
if [ ! -f ./src/lib/utils.ts ]; then
  echo "Creating utils.ts file..."
  
  # Create the utils.ts file with necessary exports
  cat > ./src/lib/utils.ts << 'EOF'
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// Helper function for merging Tailwind CSS classes
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Generate a unique ID for messages
export function generateId(): string {
  return Math.random().toString(36).substring(2, 10);
}

// Format data for display in charts
export function formatChartData(data: any[], xKey: string, yKey: string) {
  if (!data || !data.length) return [];
  
  return data.map(item => ({
    name: item[xKey],
    value: typeof item[yKey] === 'number' ? item[yKey] : parseInt(item[yKey]),
  }));
}

// Helper to determine if result is time series data
export function isTimeSeriesData(data: any[]) {
  if (!data || !data.length) return false;
  
  const firstItem = data[0];
  return (
    (firstItem.hasOwnProperty('year') || firstItem.hasOwnProperty('month')) &&
    (firstItem.hasOwnProperty('total_units_sold') || 
     firstItem.hasOwnProperty('model_units_sold') ||
     firstItem.hasOwnProperty('sales') ||
     firstItem.hasOwnProperty('units'))
  );
}

// Helper to determine if result is categorical data
export function isCategoricalData(data: any[]) {
  if (!data || !data.length) return false;
  
  const firstItem = data[0];
  return (
    (firstItem.hasOwnProperty('manufacturer_name') || 
     firstItem.hasOwnProperty('model_name') ||
     firstItem.hasOwnProperty('manufacturer') ||
     firstItem.hasOwnProperty('model')) &&
    (firstItem.hasOwnProperty('total_units_sold') || 
     firstItem.hasOwnProperty('model_units_sold') ||
     firstItem.hasOwnProperty('sales') ||
     firstItem.hasOwnProperty('units'))
  );
}

// Format a date for display
export function formatDate(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric',
  }).format(date);
}
EOF

  echo "utils.ts file created successfully."
else
  echo "utils.ts file already exists."
fi

# Ensure types.ts exists
if [ ! -f ./src/lib/types.ts ]; then
  echo "Creating types.ts file..."
  
  cat > ./src/lib/types.ts << 'EOF'
export type Role = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: Date;
  isLoading?: boolean;
  isError?: boolean;
  errorMessage?: string;
  dataResult?: DataResult;
}

export type DataDisplayType = 'table' | 'bar' | 'line' | 'pie' | 'none';

export interface DataResult {
  data: any[];
  displayType: DataDisplayType;
  insight?: string;
  sqlQuery?: string;
  reasoning?: string;
  column_order?: string[];
}
EOF

  echo "types.ts file created successfully."
else
  echo "types.ts file already exists."
fi

# Ensure openai.ts exists
if [ ! -f ./src/lib/openai.ts ]; then
  echo "Creating openai.ts file..."
  
  cat > ./src/lib/openai.ts << 'EOF'
import OpenAI from "openai";

// Initialize the OpenAI client
export const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Function to generate chat completions
export async function generateChatCompletion(
  messages: Array<{ role: string; content: string }>,
  options: {
    model?: string;
    temperature?: number;
    max_tokens?: number;
  } = {}
) {
  const { model = "gpt-4-0125-preview", temperature = 0.7, max_tokens = 1500 } = options;

  try {
    const response = await openai.chat.completions.create({
      model,
      messages,
      temperature,
      max_tokens,
    });

    return response.choices[0].message.content;
  } catch (error) {
    console.error("Error generating chat completion:", error);
    throw error;
  }
}

// Analyze SQL query results and generate insights
export async function generateInsight(data: any[], sqlQuery: string, question: string) {
  try {
    // Prepare the prompt
    const messages = [
      {
        role: "system",
        content: `You are a data analyst assistant. Your task is to analyze SQL query results and provide insights.
        Be concise but informative. Focus on key trends, outliers, and important observations.
        Respond with 2-4 sentences of insight that directly answer the user's question.`
      },
      {
        role: "user",
        content: `I ran this SQL query: "${sqlQuery}" to answer the question: "${question}".
        Here's the data (showing first 5 rows): ${JSON.stringify(data.slice(0, 5), null, 2)}
        There are ${data.length} rows in total.
        Please provide a brief insight about what this data tells us.`
      }
    ];

    const insightResponse = await generateChatCompletion(messages, {
      temperature: 0.5,
      max_tokens: 300
    });

    return insightResponse;
  } catch (error) {
    console.error("Error generating insight:", error);
    return "Unable to generate insights from the data.";
  }
}

// Modify SQL query based on user suggestion
export async function modifyQuery(
  originalQuery: string,
  suggestion: string,
  originalResults: any[]
) {
  try {
    const messages = [
      {
        role: "system",
        content: `You are a SQL expert. Your task is to modify an existing SQL query based on a user's suggestion.
        Return only valid SQL that can be executed directly - no explanations or code blocks.`
      },
      {
        role: "user",
        content: `Here's my original SQL query: "${originalQuery}"
        The query returned these results (first few rows): ${JSON.stringify(originalResults, null, 2)}
        
        I want to modify the query to: "${suggestion}"
        
        Please provide the modified SQL query only.`
      }
    ];

    const modifiedQuery = await generateChatCompletion(messages, {
      temperature: 0.3,
      max_tokens: 500
    });

    return modifiedQuery?.trim();
  } catch (error) {
    console.error("Error modifying query:", error);
    throw error;
  }
}
EOF

  echo "openai.ts file created successfully."
else
  echo "openai.ts file already exists."
fi

# Ensure supabase.ts exists
if [ ! -f ./src/lib/supabase.ts ]; then
  echo "Creating supabase.ts file..."
  
  cat > ./src/lib/supabase.ts << 'EOF'
import { createClient } from '@supabase/supabase-js';

// Initialize the Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseKey);

// Execute SQL query
export async function executeSqlQuery(query: string) {
  try {
    const { data, error } = await supabase.rpc('exec_sql', { sql: query });
    
    if (error) {
      throw error;
    }
    
    return { data, error: null };
  } catch (error) {
    console.error('Error executing SQL query:', error);
    return { data: null, error: error };
  }
}

// Process chat message and generate SQL query
export async function processChatMessage(message: string, chatHistory: any[]) {
  try {
    // Call your SQL query processing logic here
    // This is a placeholder implementation
    return {
      success: true,
      query: `SELECT * FROM your_table WHERE condition = 'value' LIMIT 10`,
      data: []
    };
  } catch (error) {
    console.error('Error processing chat message:', error);
    return {
      success: false,
      error: 'Failed to process your message'
    };
  }
}
EOF

  echo "supabase.ts file created successfully."
else
  echo "supabase.ts file already exists."
fi

echo "Setup complete!" 