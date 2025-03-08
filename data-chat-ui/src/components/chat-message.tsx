"use client";

import React, { useState } from 'react';
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
import SimpleDataDisplay from '@/components/simple-data-display';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RefreshCw, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import DataDisplay from '@/components/data-display';

interface ChatMessageProps {
  message: ChatMessage;
  onModifyQuery?: (originalQuery: string, suggestion: string, originalData: any[]) => Promise<void>;
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

export function ChatMessageItem({ message, onModifyQuery }: ChatMessageProps) {
  const [modifiedQuerySuggestion, setModifiedQuerySuggestion] = useState('');
  const [isSubmittingSuggestion, setIsSubmittingSuggestion] = useState(false);

  const handleSubmitModification = (e: React.FormEvent) => {
    e.preventDefault();
    if (!modifiedQuerySuggestion.trim() || !message.dataResult?.sqlQuery || !onModifyQuery) return;
    
    setIsSubmittingSuggestion(true);
    onModifyQuery(
      message.dataResult.sqlQuery, 
      modifiedQuerySuggestion,
      message.dataResult.data || []
    )
      .finally(() => {
        setIsSubmittingSuggestion(false);
        setModifiedQuerySuggestion('');
      });
  };

  // Check if this is a query modification message
  const isQueryModification = message.role === 'user' && message.content.startsWith('Modify query:');

  return (
    <div className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      {message.role === 'assistant' && (
        <Avatar className="h-8 w-8 bg-primary text-white flex items-center justify-center">
          <span className="text-xs font-medium">AI</span>
        </Avatar>
      )}
      
      <div className={`max-w-[80%] ${message.role === 'user' ? 'order-first' : ''}`}>
        <Card className={`p-3 ${message.role === 'user' ? (isQueryModification ? 'bg-blue-100 dark:bg-blue-900/30' : 'bg-primary/10') : 'bg-card'}`}>
          {message.isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Generating response...</span>
            </div>
          ) : message.isError ? (
            <div>
              <p className="text-destructive font-medium">Error:</p>
              <p>{message.errorMessage || 'An unknown error occurred'}</p>
            </div>
          ) : (
            <>
              <div className="prose prose-sm dark:prose-invert">
                {isQueryModification ? (
                  <div className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 text-blue-500" />
                    <span>{message.content}</span>
                  </div>
                ) : (
                  message.content
                )}
              </div>
              
              {message.dataResult && (
                <div className="mt-3">
                  <DataDisplay 
                    data={message.dataResult.data} 
                    displayType={message.dataResult.displayType}
                    column_order={message.dataResult.column_order}
                  />
                  
                  {message.dataResult.insight && (
                    <div className="mt-3 p-2 bg-primary/5 rounded-md">
                      <p className="text-sm font-medium">Insight:</p>
                      <p className="text-sm">{message.dataResult.insight}</p>
                    </div>
                  )}
                  
                  {message.dataResult.sqlQuery && (
                    <div className="mt-3">
                      <div className="flex justify-between items-center">
                        <p className="text-sm font-medium">SQL Query:</p>
                      </div>
                      <pre className="mt-1 p-2 bg-muted rounded-md overflow-x-auto text-xs">
                        {message.dataResult.sqlQuery}
                      </pre>
                      
                      {/* Simple query modification section */}
                      {onModifyQuery && (
                        <form onSubmit={handleSubmitModification} className="mt-3">
                          <p className="text-sm font-medium">Suggest a query modification:</p>
                          <div className="flex gap-2 mt-1">
                            <Input
                              value={modifiedQuerySuggestion}
                              onChange={(e) => setModifiedQuerySuggestion(e.target.value)}
                              placeholder="Change the query to..."
                              className="text-sm flex-1"
                              disabled={isSubmittingSuggestion}
                            />
                            <Button
                              type="submit"
                              size="sm"
                              disabled={!modifiedQuerySuggestion.trim() || isSubmittingSuggestion}
                            >
                              {isSubmittingSuggestion ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <RefreshCw className="h-4 w-4" />
                              )}
                            </Button>
                          </div>
                        </form>
                      )}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </Card>
        
        <p className="text-xs text-muted-foreground mt-1">
          {formatDistanceToNow(new Date(message.createdAt), { addSuffix: true })}
        </p>
      </div>
    </div>
  );
} 