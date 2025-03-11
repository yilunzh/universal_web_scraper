import React from 'react';
import { 
  Table, TableBody, TableCell, 
  TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { DataDisplayType } from '@/lib/types';

interface SimpleDataDisplayProps {
  data: any[];
  displayType: DataDisplayType;
  column_order?: string[];
}

export default function SimpleDataDisplay({ 
  data, 
  displayType, 
  column_order 
}: SimpleDataDisplayProps) {
  // Just use a simple table for now
  if (!data || data.length === 0) {
    return <div className="text-center py-4">No data available</div>;
  }

  // Get the first row data
  const firstRow = data[0];
  
  // 1. Use explicit column_order if provided
  // 2. Use Object.keys() from data which preserves insertion order in modern JS/TS
  let columns = column_order || Object.keys(firstRow);
  
  // Remove all special case handling as it won't be necessary with proper column order preservation
  
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column}>{formatColumnName(column)}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {columns.map((column) => (
                <TableCell key={`${rowIndex}-${column}`}>
                  {formatCellValue(row[column])}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// Helper functions
function formatColumnName(column: string): string {
  return column
    .replace(/_/g, ' ')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function formatCellValue(value: any): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'number') {
    // Format large numbers with commas
    return value.toLocaleString();
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
} 