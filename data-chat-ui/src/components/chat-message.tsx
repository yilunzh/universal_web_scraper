"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { ChatMessage, DataDisplayType } from "@/lib/types";
import { cn } from "@/lib/utils";
import { 
  Table, TableBody, TableCell, 
  TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { 
  LineChart, Line, XAxis, YAxis, Tooltip, 
  ResponsiveContainer, Legend 
} from 'recharts';

interface ChatMessageProps {
  message: ChatMessage;
}

// Simple inline component for data display
function SimpleDataDisplay({ data, displayType, column_order }: { 
  data: any[], 
  displayType: DataDisplayType,
  column_order?: string[]
}) {
  // Just use a simple table for now
  if (!data || data.length === 0) {
    return <div className="text-center py-4">No data available</div>;
  }

  // Get the first row data
  const firstRow = data[0];
  
  // Use column_order if provided, otherwise use keys from data
  let columns = column_order || Object.keys(firstRow);
  
  // Special handling for market share query to match SQL column order if no column_order provided
  if (!column_order && 
      columns.includes('manufacturer_name') && 
      columns.includes('total_model_units_sold') && 
      columns.includes('market_share')) {
    columns = ['manufacturer_name', 'total_model_units_sold', 'market_share'];
  }
  
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

// Create a new component for formatted insights
function FormattedInsight({ insight }: { insight: string }) {
  // Function to extract numerical data from monthly insights
  const extractTimeSeriesData = (text: string) => {
    // Look for patterns like "2024-01, 小米SU7 sold 0 units while model 3 sold 29,574 units"
    const entries: { date: string; model1Value: number; model2Value: number }[] = [];
    
    // Extract month entries with unit values
    const monthlyPattern = /(20\d{2}-\d{2})[^0-9]*(小米SU7|SU7)[^0-9]*sold[^0-9]*([0-9,]+)[^0-9]*units[^0-9]*(model 3)[^0-9]*sold[^0-9]*([0-9,]+)/gi;
    let match;
    
    while ((match = monthlyPattern.exec(text)) !== null) {
      const date = match[1];
      const model1 = match[2];
      const model1Sales = parseInt(match[3].replace(/,/g, ''), 10);
      const model2 = match[4];
      const model2Sales = parseInt(match[5].replace(/,/g, ''), 10);
      
      entries.push({
        date,
        model1Value: model1Sales,
        model2Value: model2Sales,
      });
    }
    
    // If we have enough data points, return the structured data
    return entries.length >= 3 ? entries : null;
  };

  // Format the insight text
  const formatInsightText = (text: string) => {
    // Check if this appears to be a time-series or month-by-month insight
    const monthlyPattern = /([0-9]{4}-[0-9]{2})/g;
    const matches = text.match(monthlyPattern);
    const isMonthlyFormat = matches && matches.length > 2;

    if (isMonthlyFormat) {
      // Split by bullet points and format as a structured list
      const bulletPoints = text.split('•');
      
      return (
        <div className="space-y-3">
          {bulletPoints.map((point, index) => {
            if (!point.trim()) return null;
            
            // Extract month/date if it exists (YYYY-MM format)
            const monthMatch = point.match(/([0-9]{4}-[0-9]{2})/);
            const monthDisplay = monthMatch ? monthMatch[0] : null;
            
            // Extract numbers (for highlighting)
            const formattedPoint = point
              .replace(/([0-9,]+\s*units)/g, '<span class="font-medium text-primary">$1</span>')
              .replace(/\b(\d+(\.\d+)?%)\b/g, '<span class="font-medium text-indigo-600">$1</span>');
            
            return (
              <div key={index} className="border-l-2 border-indigo-200 pl-3 py-1">
                {monthDisplay && (
                  <h4 className="text-sm font-semibold text-indigo-600 mb-1">
                    {monthDisplay}
                  </h4>
                )}
                <p 
                  className="text-sm" 
                  dangerouslySetInnerHTML={{ __html: formattedPoint }}
                />
              </div>
            );
          })}
        </div>
      );
    } else if (text.includes(":") && text.split("\n").filter(line => line.includes(":")).length > 3) {
      // This looks like a key-value format report
      const lines = text.split("\n").filter(line => line.trim());
      
      return (
        <div className="space-y-2">
          {lines.map((line, index) => {
            if (line.includes(":")) {
              const [key, value] = line.split(":", 2);
              return (
                <div key={index} className="flex">
                  <div className="font-medium text-indigo-700 dark:text-indigo-300 min-w-[30%]">{key.trim()}:</div>
                  <div className="flex-1">{value.trim()}</div>
                </div>
              );
            } else {
              return <p key={index} className="text-sm">{line}</p>
            }
          })}
        </div>
      );
    } else {
      // For other formats, break into paragraphs and apply basic formatting
      const paragraphs = text.split('\n\n').filter(p => p.trim());
      if (paragraphs.length === 0) {
        // If no double line breaks, try single line breaks
        const lines = text.split('\n').filter(p => p.trim());
        
        return (
          <div className="space-y-2">
            {lines.map((line, index) => {
              // Check if this line starts with a bullet or number
              const isBullet = line.trim().startsWith("-") || line.trim().startsWith("•");
              const isNumbered = /^\d+[).]\s/.test(line.trim());
              
              if (isBullet || isNumbered) {
                return (
                  <div key={index} className="flex">
                    <div className="w-6 flex-shrink-0 text-indigo-600">
                      {isBullet ? "•" : line.trim().match(/^\d+/)?.[0] + "."}
                    </div>
                    <div className="flex-1">
                      {line.trim().replace(/^[-•\d).\s]+/, "")}
                    </div>
                  </div>
                );
              }
              
              // Highlight numbers and percentages
              const formattedLine = line
                .replace(/\b(\d+(\.\d+)?%)\b/g, '<span class="font-medium text-indigo-600">$1</span>')
                .replace(/\b(\d{1,3}(,\d{3})*(\.\d+)?)\b(?!\s*%)/g, '<span class="font-medium">$1</span>');
                
              return (
                <p 
                  key={index} 
                  className="text-sm" 
                  dangerouslySetInnerHTML={{ __html: formattedLine }}
                />
              );
            })}
          </div>
        );
      }
      
      return (
        <div className="space-y-2">
          {paragraphs.map((paragraph, index) => {
            // Highlight numbers and percentages
            const formattedParagraph = paragraph
              .replace(/\b(\d+(\.\d+)?%)\b/g, '<span class="font-medium text-indigo-600">$1</span>')
              .replace(/\b(\d{1,3}(,\d{3})*(\.\d+)?)\b(?!\s*%)/g, '<span class="font-medium">$1</span>');
              
            return (
              <p 
                key={index} 
                className="text-sm" 
                dangerouslySetInnerHTML={{ __html: formattedParagraph }}
              />
            );
          })}
        </div>
      );
    }
  };

  // Extract time series data for visualization
  const timeSeriesData = extractTimeSeriesData(insight);

  return (
    <Card className="px-4 py-3 mt-2 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-indigo-950/30 dark:to-blue-950/30">
      <div className="border-b border-indigo-100 dark:border-indigo-900 pb-2 mb-2">
        <h3 className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
          Insights
        </h3>
      </div>
      
      {/* If we have time series data, show a chart */}
      {timeSeriesData && timeSeriesData.length > 0 && (
        <div className="mb-4 mt-2 h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={timeSeriesData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip 
                formatter={(value) => new Intl.NumberFormat().format(value as number)}
              />
              <Legend />
              <Line 
                type="monotone" 
                dataKey="model1Value" 
                name="小米SU7" 
                stroke="#8884d8" 
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line 
                type="monotone" 
                dataKey="model2Value" 
                name="Model 3" 
                stroke="#82ca9d" 
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      
      {formatInsightText(insight)}
    </Card>
  );
}

export function ChatMessageItem({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex w-full items-start gap-4 py-4",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <Avatar className="h-8 w-8">
          <AvatarImage src="/assets/bot-avatar.png" alt="AI Assistant" />
          <AvatarFallback>AI</AvatarFallback>
        </Avatar>
      )}

      <div className="flex flex-col gap-2 max-w-[80%]">
        <Card
          className={cn(
            "px-4 py-3 rounded-lg",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted"
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </Card>

        {message.dataResult && (
          <div className="mt-2">
            {message.dataResult.data && message.dataResult.data.length > 0 ? (
              <>
                <SimpleDataDisplay
                  data={message.dataResult.data}
                  displayType={message.dataResult.displayType}
                  column_order={message.dataResult.column_order}
                />
                
                {/* Chain of Thought Reasoning */}
                {message.dataResult.reasoning && (
                  <div className="mt-2">
                    <details className="text-xs">
                      <summary className="cursor-pointer font-medium text-indigo-600">
                        View Chain of Thought
                      </summary>
                      <Card className="px-4 py-3 mt-2 bg-indigo-50 dark:bg-indigo-950/30">
                        <p className="text-sm whitespace-pre-wrap">
                          <span className="font-semibold">Reasoning:</span> {message.dataResult.reasoning}
                        </p>
                      </Card>
                    </details>
                  </div>
                )}
                
                {message.dataResult.insight && (
                  <FormattedInsight insight={message.dataResult.insight} />
                )}
                
                {message.dataResult.sqlQuery && (
                  <div className="mt-2">
                    <details className="text-xs text-muted-foreground">
                      <summary className="cursor-pointer font-medium">
                        View SQL Query
                      </summary>
                      <pre className="mt-2 p-2 bg-muted rounded overflow-x-auto">
                        {message.dataResult.sqlQuery}
                      </pre>
                    </details>
                  </div>
                )}
              </>
            ) : (
              <Card className="px-4 py-3 mt-2 bg-muted-foreground/10">
                <p className="text-sm">No data found for your query.</p>
              </Card>
            )}
          </div>
        )}

        {message.isLoading && (
          <div className="flex items-center gap-1 text-sm text-muted-foreground mt-2">
            <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground delay-75"></div>
            <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground delay-150"></div>
            <span className="ml-2">Thinking...</span>
          </div>
        )}

        {message.isError && (
          <div className="mt-2">
            <Card className="px-4 py-3 bg-destructive/10 text-destructive">
              <p className="text-sm">
                {message.errorMessage || "An error occurred. Please try again."}
              </p>
            </Card>
            
            {/* Display SQL query if available with the error */}
            {message.sqlQuery && (
              <div className="mt-2">
                <details className="text-xs text-muted-foreground" open>
                  <summary className="cursor-pointer font-medium">
                    SQL Query that caused the error
                  </summary>
                  <pre className="mt-2 p-2 bg-muted rounded overflow-x-auto">
                    {message.sqlQuery}
                  </pre>
                </details>
              </div>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <Avatar className="h-8 w-8">
          <AvatarFallback>U</AvatarFallback>
        </Avatar>
      )}
    </div>
  );
} 