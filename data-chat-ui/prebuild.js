#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

// Ensure lib directory exists
const libDir = path.join(__dirname, 'src', 'lib');
if (!fs.existsSync(libDir)) {
  fs.mkdirSync(libDir, { recursive: true });
  console.log('Created lib directory');
}

// Ensure the utils file exists in lib
const utilsFile = path.join(libDir, 'utils.ts');
if (!fs.existsSync(utilsFile)) {
  const utilsContent = `
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
`;
  fs.writeFileSync(utilsFile, utilsContent);
  console.log('Created utils.ts file');
}

console.log('Pre-build script completed successfully'); 