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

echo "Setup complete!" 