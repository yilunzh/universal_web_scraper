"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { ChatMessage, DataDisplayType } from "@/lib/types";
import { cn } from "@/lib/utils";
import { 
  Table, TableBody, TableCell, 
  TableHead, TableHeader, TableRow 
} from '@/components/ui/table';

interface ChatMessageProps {
  message: ChatMessage;
}

// Simple inline component for data display
function SimpleDataDisplay({ data, displayType }: { data: any[], displayType: DataDisplayType }) {
  // Just use a simple table for now
  if (!data || data.length === 0) {
    return <div className="text-center py-4">No data available</div>;
  }

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
                  <Card className="px-4 py-3 mt-2 bg-muted-foreground/10">
                    <p className="text-sm">{message.dataResult.insight}</p>
                  </Card>
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
          <Card className="px-4 py-3 mt-2 bg-destructive/10 text-destructive">
            <p className="text-sm">
              {message.errorMessage || "An error occurred. Please try again."}
            </p>
          </Card>
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