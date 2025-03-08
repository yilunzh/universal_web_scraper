"use client";

import React, { useState } from 'react';
import { 
  BarChart, Bar, LineChart, Line, PieChart, Pie, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ResponsiveContainer, Cell 
} from 'recharts';
import { 
  Table, TableBody, TableCaption, TableCell, 
  TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { DataDisplayType } from '@/lib/types';
import { formatChartData, isTimeSeriesData, isCategoricalData } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { BarChart2, LineChart as LineChartIcon, PieChart as PieChartIcon, Table as TableIcon } from 'lucide-react';

interface DataDisplayProps {
  data: any[];
  displayType: DataDisplayType;
  column_order?: string[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFECC2', '#FF8C8C', '#A9D9A9'];

export default function DataDisplay({ data, displayType, column_order }: DataDisplayProps) {
  // Always start with table view, but remember the recommended display type
  const [activeView, setActiveView] = useState<'table' | 'chart'>('table');
  const hasChartOption = displayType !== 'none' && displayType !== 'table' && data.length > 0;

  if (!data || data.length === 0) {
    return <div className="text-center py-4">No data available</div>;
  }

  // Get all columns from the first row for table display
  const firstRow = data[0];
  
  // Use column_order if provided, otherwise use keys from the data
  let columns = column_order || Object.keys(firstRow);
  
  // If it's the specific columns from the user's market share query,
  // force the correct order - this is a special case for this particular query pattern
  if (!column_order && 
      columns.includes('manufacturer_name') && 
      columns.includes('total_model_units_sold') && 
      columns.includes('market_share')) {
    columns = ['manufacturer_name', 'total_model_units_sold', 'market_share'];
  }

  // Render chart based on display type
  const renderChart = () => {
    // Bar Chart
    if (displayType === 'bar') {
      // Determine keys for X and Y axis
      const { chartData, valueKeys } = prepareMultiSeriesChartData(data);
      
      return (
        <div className="h-[300px] w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              {valueKeys.map((key, index) => (
                <Bar 
                  key={key} 
                  dataKey={key} 
                  fill={COLORS[index % COLORS.length]} 
                  name={formatColumnName(key)}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // Line Chart
    if (displayType === 'line') {
      // Check for multi-series time series data
      const { chartData, valueKeys } = prepareMultiSeriesChartData(data);
      
      return (
        <div className="h-[300px] w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              {valueKeys.map((key, index) => (
                <Line 
                  key={key} 
                  type="monotone" 
                  dataKey={key} 
                  stroke={COLORS[index % COLORS.length]}
                  name={formatColumnName(key)}
                  dot={false}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }

    // Pie Chart
    if (displayType === 'pie') {
      // Determine keys for label and value
      const keys = determineChartKeys(data);
      const chartData = formatChartData(data, keys.xKey, keys.yKey);
      
      return (
        <div className="h-[300px] w-full mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={renderCustomizedLabel}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      );
    }

    return <div className="text-center py-4">No chart available for this data</div>;
  };

  // Render toggle buttons for switching between table and chart
  const renderViewToggle = () => {
    if (!hasChartOption) return null;

    return (
      <div className="flex justify-end mb-2 gap-1">
        <Button 
          size="sm" 
          variant={activeView === 'table' ? 'default' : 'outline'} 
          onClick={() => setActiveView('table')}
        >
          <TableIcon className="h-4 w-4 mr-1" />
          Table
        </Button>
        <Button 
          size="sm" 
          variant={activeView === 'chart' ? 'default' : 'outline'} 
          onClick={() => setActiveView('chart')}
        >
          {displayType === 'bar' && <BarChart2 className="h-4 w-4 mr-1" />}
          {displayType === 'line' && <LineChartIcon className="h-4 w-4 mr-1" />}
          {displayType === 'pie' && <PieChartIcon className="h-4 w-4 mr-1" />}
          Chart
        </Button>
      </div>
    );
  };

  return (
    <div>
      {renderViewToggle()}
      
      {activeView === 'table' ? (
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
      ) : (
        renderChart()
      )}
    </div>
  );
}

// Helper function to prepare data for multi-series charts (bar, line)
function prepareMultiSeriesChartData(data: any[]) {
  // Detect time-series or categorical data with multiple series
  const firstRow = data[0];
  const columns = Object.keys(firstRow);
  
  // Identify time or category key (usually year, month, or a name field)
  let xKey = '';
  if (columns.includes('year') && columns.includes('month')) {
    // If we have both year and month, combine them
    xKey = 'yearMonth';
  } else if (columns.includes('year')) {
    xKey = 'year';
  } else if (columns.includes('month')) {
    xKey = 'month';
  } else if (columns.includes('date')) {
    xKey = 'date';
  } else {
    // Find a key that could be a category
    xKey = columns.find(col => 
      ['manufacturer_name', 'model_name', 'category', 'name'].includes(col)
    ) || columns[0];
  }
  
  // Find all potential value columns (typically numbers excluding IDs and dates)
  const numericColumns = columns.filter(col => {
    const value = firstRow[col];
    return (
      typeof value === 'number' && 
      !['id', 'year', 'month'].includes(col) &&
      !col.includes('_id')
    );
  });
  
  // If we have manufacturer or model specific columns, use those
  let valueKeys = numericColumns.length > 0 ? numericColumns : [columns[1]];
  
  // Prepare data structure for chart
  let chartData: any[] = [];
  
  // Handle the case with both year and month (common in time series)
  if (xKey === 'yearMonth') {
    // Create a map to group data by year-month combination
    const groupedData = new Map();
    
    data.forEach(item => {
      const key = `${item.year}-${item.month.toString().padStart(2, '0')}`;
      if (!groupedData.has(key)) {
        groupedData.set(key, { name: key });
      }
      
      // For each value column, add it to the grouped data
      valueKeys.forEach(valueKey => {
        if (item[valueKey] !== undefined) {
          // If the item has a manufacturer_name field, use that to create series
          if (item.manufacturer_name) {
            // Use manufacturer name as the series name
            const seriesKey = item.manufacturer_name.replace(/\s+/g, '_');
            groupedData.get(key)[seriesKey] = item[valueKey];
          } else {
            groupedData.get(key)[valueKey] = item[valueKey];
          }
        }
      });
    });
    
    // Convert map to array and sort by date
    chartData = Array.from(groupedData.values())
      .sort((a, b) => a.name.localeCompare(b.name));
      
    // If we have manufacturer names, update valueKeys
    if (data[0].manufacturer_name) {
      // Get unique manufacturer names
      const uniqueManufacturers = [...new Set(data.map(item => item.manufacturer_name))];
      // Convert to valid keys (replace spaces with underscores)
      valueKeys = uniqueManufacturers.map(name => name.replace(/\s+/g, '_'));
    }
  } else {
    // Simple data grouping for non-combined date fields
    chartData = data.map(item => {
      const entry: any = { name: item[xKey] };
      
      // Add each value column
      valueKeys.forEach(key => {
        entry[key] = item[key];
      });
      
      return entry;
    });
  }
  
  return { chartData, valueKeys };
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

function determineChartKeys(data: any[]): { xKey: string; yKey: string } {
  const firstItem = data[0];
  const keys = Object.keys(firstItem);

  // For time series data
  if (isTimeSeriesData(data)) {
    const timeKey = keys.find(k => k === 'year' || k === 'month') || keys[0];
    const valueKey = keys.find(k => 
      k === 'total_units_sold' || 
      k === 'model_units_sold' || 
      k === 'sales' || 
      k === 'units'
    ) || keys[1];
    
    return { xKey: timeKey, yKey: valueKey };
  }

  // For categorical data
  if (isCategoricalData(data)) {
    const categoryKey = keys.find(k => 
      k === 'manufacturer_name' || 
      k === 'model_name' || 
      k === 'manufacturer' || 
      k === 'model'
    ) || keys[0];
    
    const valueKey = keys.find(k => 
      k === 'total_units_sold' || 
      k === 'model_units_sold' || 
      k === 'sales' || 
      k === 'units'
    ) || keys[1];
    
    return { xKey: categoryKey, yKey: valueKey };
  }

  // Default: first column for X, second for Y
  return { xKey: keys[0], yKey: keys[1] };
}

// Custom label renderer for pie chart
const RADIAN = Math.PI / 180;
function renderCustomizedLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }: any) {
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
} 