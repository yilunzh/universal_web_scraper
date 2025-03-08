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
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  message: ChatMessage;
  onModifyQuery?: (originalQuery: string, suggestion: string, originalData: any[]) => Promise<void>;
}

// Render Markdown content for insights
function FormattedInsight({ insight }: { insight: string }) {
  if (!insight) return null;

  // Add Markdown heading if it doesn't start with one
  const enhancedInsight = insight.trim().startsWith('#') 
    ? insight 
    : `# Key Insights\n\n${insight}`;

  return (
    <div className="mt-3 p-4 bg-primary/5 rounded-md">
      <div className="text-sm prose prose-sm prose-headings:font-semibold prose-headings:mt-4 prose-headings:mb-2 prose-h1:text-base prose-h2:text-sm prose-p:my-1.5 prose-li:my-0.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-strong:text-primary/90 prose-code:text-xs prose-code:px-1 prose-code:py-0.5 prose-code:bg-primary/10 prose-code:rounded max-w-none">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {enhancedInsight}
        </ReactMarkdown>
      </div>
    </div>
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
                    <FormattedInsight insight={message.dataResult.insight} />
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