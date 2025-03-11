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

// Format data for display in charts (simplified)
export function formatChartData(data: any[], xKey: string, yKey: string) {
  if (!data || !data.length) return [];
  
  return data.map(item => ({
    name: item[xKey],
    value: typeof item[yKey] === 'number' ? item[yKey] : parseInt(item[yKey]),
  }));
}

// Format a date for display
export function formatDate(date: Date): string {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric',
  }).format(date);
} 