"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ChatMessageItem } from '@/components/chat-message';
import { ChatMessage } from '@/lib/types';
import { generateId } from '@/lib/utils';
import { Card } from './ui/card';
import { Separator } from './ui/separator';

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hi! I can help you analyze China auto sales data. Ask me anything about sales by manufacturer, model, time period, or trends.',
      createdAt: new Date(),
    },
  ]);
  
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);
  
  // Scroll to the bottom when messages change
  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim() || isLoading) return;
    
    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: inputValue,
      createdAt: new Date(),
    };
    
    // Add user message
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    
    // Create a placeholder for the assistant's response
    const assistantMessageId = generateId();
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      createdAt: new Date(),
      isLoading: true,
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    setIsLoading(true);
    
    try {
      // Format chat history for the API
      const chatHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));
      
      // Call the API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: userMessage.content,
          chatHistory,
        }),
      });
      
      const data = await response.json();
      
      // Update the assistant message based on the response
      setMessages(prev => 
        prev.map(msg => {
          if (msg.id === assistantMessageId) {
            if (data.type === 'follow_up') {
              return {
                ...msg,
                content: data.content,
                isLoading: false,
              };
            } else if (data.type === 'data') {
              return {
                ...msg,
                content: data.content,
                isLoading: false,
                dataResult: {
                  data: data.data,
                  displayType: data.displayType,
                  insight: data.insight,
                  sqlQuery: data.sqlQuery,
                  reasoning: data.reasoning,
                  column_order: data.column_order,
                },
              };
            } else if (data.type === 'error') {
              return {
                ...msg,
                content: data.content,
                isLoading: false,
                isError: true,
                errorMessage: data.error,
              };
            }
          }
          return msg;
        })
      );
    } catch (error) {
      // Handle fetch errors
      setMessages(prev => 
        prev.map(msg => {
          if (msg.id === assistantMessageId) {
            return {
              ...msg,
              content: 'Sorry, there was an error processing your request.',
              isLoading: false,
              isError: true,
              errorMessage: error instanceof Error ? error.message : 'Unknown error',
            };
          }
          return msg;
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  // Example questions to help users get started
  const exampleQuestions = [
    'What were the total sales of Tesla in 2020?',
    'Which manufacturer sold the most cars in 2021?',
    'Show me the monthly sales trend for Toyota in 2019',
    'Compare sales of BMW and Mercedes in 2022',
  ];

  // Add a simplified query modification handler
  const handleQueryModification = async (originalQuery: string, suggestion: string, originalData: any[]): Promise<void> => {
    // Don't allow modifications if already loading
    if (isLoading) return;
    
    setIsLoading(true);
    
    try {
      // Add the user's suggestion as a new message
      const userMessageId = generateId();
      const userMessage: ChatMessage = {
        id: userMessageId,
        role: 'user',
        content: `Modify query: ${suggestion}`,
        createdAt: new Date(),
      };
      
      // Add user message
      setMessages(prev => [...prev, userMessage]);
      
      // Create a placeholder for the assistant's response to the modification
      const assistantMessageId = generateId();
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: `Modifying query to ${suggestion}...`,
        createdAt: new Date(),
        isLoading: true,
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      
      // Call the API to modify the query
      const response = await fetch('/api/chat/modify-query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          originalQuery,
          suggestion,
          originalResults: originalData.slice(0, 5)
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to modify query');
      }
      
      const data = await response.json();
      
      // Generate insights for the modified data if not provided by the API
      let insight = data.insight || '';
      
      if (!insight && data.data && data.data.length > 0) {
        try {
          // Call the API to generate insights for the modified data
          const insightResponse = await fetch('/api/chat/generate-insight', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              data: data.data,
              sqlQuery: data.modifiedQuery,
              question: suggestion
            }),
          });
          
          if (insightResponse.ok) {
            const insightData = await insightResponse.json();
            insight = insightData.insight || '';
          }
        } catch (error) {
          console.error('Error generating insights:', error);
        }
      }
      
      // Update the assistant message with the modification results
      setMessages(prev => 
        prev.map(msg => {
          if (msg.id === assistantMessageId) {
            return {
              ...msg,
              content: `Modified query to ${suggestion}: ${data.explanation || 'Query modified successfully.'}`,
              isLoading: false,
              dataResult: {
                data: data.data || [],
                displayType: data.displayType || 'table',
                sqlQuery: data.modifiedQuery,
                insight: insight,
              },
            };
          }
          return msg;
        })
      );
    } catch (error) {
      // Handle errors during modification
      setMessages(prev => 
        prev.map(msg => {
          if (msg.isLoading) {
            return {
              ...msg,
              content: 'Sorry, there was an error modifying the query.',
              isLoading: false,
              isError: true,
              errorMessage: error instanceof Error ? error.message : 'Unknown error',
            };
          }
          return msg;
        })
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="bg-gradient-to-r from-indigo-600 to-blue-500 py-4 px-6 text-white">
        <h1 className="text-2xl font-bold">China Auto Sales Data Analyzer</h1>
        <p className="text-gray-100">Ask questions about China's auto market data since 2018</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <ChatMessageItem 
            key={message.id} 
            message={message} 
            onModifyQuery={handleQueryModification}
          />
        ))}
        <div ref={endOfMessagesRef} />
      </div>
      
      {messages.length <= 1 && (
        <Card className="mx-4 my-2 p-4">
          <h3 className="font-medium mb-2">Try asking:</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {exampleQuestions.map((question, i) => (
              <Button 
                key={i} 
                variant="outline" 
                className="justify-start h-auto py-2 px-3 text-left"
                onClick={() => {
                  setInputValue(question);
                }}
              >
                {question}
              </Button>
            ))}
          </div>
        </Card>
      )}
      
      <Separator />
      
      <form onSubmit={handleSubmit} className="p-4">
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask a question about China auto sales data..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || !inputValue.trim()}>
            {isLoading ? (
              <span className="flex items-center gap-1">
                <span className="h-1 w-1 rounded-full bg-white animate-bounce"></span>
                <span className="h-1 w-1 rounded-full bg-white animate-bounce delay-75"></span>
                <span className="h-1 w-1 rounded-full bg-white animate-bounce delay-150"></span>
              </span>
            ) : (
              'Send'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}