"use client";

import React from 'react';
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

interface DataDisplayProps {
  data: any[];
  displayType: DataDisplayType;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFECC2', '#FF8C8C', '#A9D9A9'];

export default function DataDisplay({ data, displayType }: DataDisplayProps) {
  if (!data || data.length === 0) {
    return <div className="text-center py-4">No data available</div>;
  }

  // Table display (default)
  if (displayType === 'table' || displayType === 'none') {
    const columns = Object.keys(data[0]);
    
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

  // Bar Chart
  if (displayType === 'bar') {
    // Determine keys for X and Y axis
    const keys = determineChartKeys(data);
    const chartData = formatChartData(data, keys.xKey, keys.yKey);
    
    return (
      <div className="h-[300px] w-full mt-4">
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
            <Bar dataKey="value" fill="#8884d8" name={formatColumnName(keys.yKey)}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Line Chart
  if (displayType === 'line') {
    // Determine keys for X and Y axis
    const keys = determineChartKeys(data);
    const chartData = formatChartData(data, keys.xKey, keys.yKey);
    
    return (
      <div className="h-[300px] w-full mt-4">
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
            <Line type="monotone" dataKey="value" stroke="#8884d8" name={formatColumnName(keys.yKey)} />
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
      <div className="h-[300px] w-full mt-4">
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

  return <div className="text-center py-4">Unsupported display type</div>;
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