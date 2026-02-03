"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageCircle, X, Send, RefreshCw } from "lucide-react";
import { toast } from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";
import ChatMarkdownRenderer from './ChatMarkdownRenderer';
import { ChatDrawerProps, ChatMessage, ChatResponse } from './types';

// Optimized Chatbot Drawer Component
const ChatDrawer = React.memo(({ 
  isOpen, 
  onClose,
  projectId,
  title = "Chat with AI",
  placeholder = "Type your message...",
  emptyStateTitle = "Start a conversation",
  emptyStateDescription = "Ask questions and get AI-powered insights.",
  suggestedQuestions = [
    "Summarize the key findings",
    "What are the main recommendations?",
    "Explain the validation results"
  ],
  selectedPersona = null
}: ChatDrawerProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [chatSessionId] = useState(() => `chat_session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]); // Fix for stale closure
  const apiEndpoint = `/api/v2/mvp/projects/${projectId}/solution-critique/chat/message`;
  
  // Enhanced Zustand authentication
  const token = useAuthStore((state) => state.token);

  // Sync ref with messages state to avoid stale closures
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !projectId || !token) {
      if (!token) {
        toast.error('Authentication required');
      }
      return;
    }

    // Abort previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    // Use functional update to ensure correct state sequence
    setMessages(prev => {
      const updatedMessages = [...prev, userMessage];
      return updatedMessages;
    });
    setInputMessage('');
    setIsLoading(true);

    try {
      abortControllerRef.current = new AbortController();
      
      // Build conversation history from current ref (fixes stale closure)
      const conversationHistory = messagesRef.current.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${apiEndpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: inputMessage.trim(),
          persona_id: selectedPersona || "P1",
          conversation_history: conversationHistory
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorText}`);
      }

      const data: ChatResponse = await response.json();

      // Validate API response structure
      if (!data.success) {
        throw new Error(data.error || 'Failed to get response from AI');
      }

      // Handle different response structures safely
      const assistantContent = data.answer || data.content;
      if (!assistantContent) {
        throw new Error('Invalid response format from AI service');
      }

      const assistantMessage: ChatMessage = {
        id: data.id || `assistant_${Date.now()}`,
        role: 'assistant',
        content: assistantContent,
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      // Ignore abort errors
      if (error.name === 'AbortError') return;
      
      console.error('Chat API error:', error);
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: 'system', // Changed to system for error messages
        content: error.message.includes('Network') 
          ? '**Network Error**: Failed to connect to AI service. Please try again.'
          : `**Error**: ${error.message || 'Failed to get response from AI'}`,
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
      toast.error(error.message || 'Failed to get AI response');
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [inputMessage, projectId, token, apiEndpoint, selectedPersona]); // Removed messages dependency

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  // Memoized message list with optimized rendering
  const messageList = useMemo(() => 
    messages.map((message) => (
      <div
        key={message.id}
        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div
          className={`max-w-[85%] rounded-lg px-3 py-2 ${
            message.role === 'user'
              ? 'bg-brand-500 text-white'
              : message.role === 'system'
              ? 'bg-red-100 border border-red-300 text-red-800 dark:bg-red-900 dark:border-red-700 dark:text-red-200'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
          }`}
        >
          {message.role === 'user' ? (
            <div className="text-sm whitespace-pre-wrap">{message.content}</div>
          ) : (
            <ChatMarkdownRenderer content={message.content} />
          )}
          <div
            className={`text-xs mt-1 ${
              message.role === 'user'
                ? 'text-brand-100'
                : message.role === 'system'
                ? 'text-red-600 dark:text-red-300'
                : 'text-gray-500 dark:text-gray-400'
            }`}
          >
            {message.timestamp.toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
            {message.role === 'system' && ' • Error'}
          </div>
        </div>
      </div>
    )), [messages]
  );

  // Enhanced loading state with timeout detection
  const [showSlowConnection, setShowSlowConnection] = useState(false);
  useEffect(() => {
    let timeout: NodeJS.Timeout;
    if (isLoading) {
      timeout = setTimeout(() => {
        setShowSlowConnection(true);
      }, 10000); // Show slow connection message after 10 seconds
    } else {
      setShowSlowConnection(false);
    }
    return () => clearTimeout(timeout);
  }, [isLoading]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-brand-500/80 opacity-25 h-screen"
        onClick={onClose}
        aria-hidden="true"
      />
      
      {/* Drawer */}
      <div 
        className={`absolute right-0 top-0 h-screen w-96 bg-white dark:bg-gray-800 shadow-2xl transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="dialog"
        aria-label={title}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-500 rounded-full flex items-center justify-center">
              <MessageCircle className="h-4 w-4 text-white" />
            </div>
            <div>
              <h3 className="font-semibold text-brand-500 dark:text-white">{title}</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {messages.length} message{messages.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={clearChat}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              disabled={messages.length === 0}
              aria-label="Clear chat"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              aria-label="Close chat"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Messages Container */}
        <div className="flex-1 h-[calc(100%-8rem)] overflow-hidden">
          <ScrollArea className="h-full p-4">
            {messages.length === 0 ? (
              <div className="text-center py-8">
                <MessageCircle className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                <h4 className="font-medium text-gray-900 dark:text-white mb-2">{emptyStateTitle}</h4>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {emptyStateDescription}
                </p>
                {suggestedQuestions.length > 0 && (
                  <div className="mt-4 text-xs text-gray-400 dark:text-gray-500">
                    <p>Try asking:</p>
                    <ul className="mt-2 space-y-1">
                      {suggestedQuestions.map((question, index) => (
                        <li key={index}>• "{question}"</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {messageList}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] rounded-lg px-3 py-2 bg-gray-100 dark:bg-gray-700">
                      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        thinking...
                        
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} aria-live="polite" aria-atomic="true" />
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex gap-2">
            <Input
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={placeholder}
              disabled={isLoading || !projectId}
              className="flex-1"
              aria-label="Type your message"
            />
            <Button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim() || !projectId}
              size="sm"
              className="bg-brand-500 hover:bg-brand-600"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          {!projectId && (
            <p className="text-xs text-red-500 mt-2">Project ID is required for chat</p>
          )}
          {!token && (
            <p className="text-xs text-red-500 mt-2">Authentication required</p>
          )}
        </div>
      </div>
    </div>
  );
});

ChatDrawer.displayName = 'ChatDrawer';

export default ChatDrawer;