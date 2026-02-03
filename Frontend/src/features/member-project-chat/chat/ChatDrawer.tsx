"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageCircle, X, Send, History, Plus, ArrowLeft, MoreHorizontal, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/authStore";
import ChatMarkdownRenderer from './ChatMarkdownRenderer';
import { ChatDrawerProps, ChatMessage, ChatThread } from './types';
import { projectChatService } from '@/lib/api/projectChatService';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";

// Optimized Chatbot Drawer Component
const ChatDrawer = React.memo(({
  isOpen,
  onClose,
  projectId,
  organizationId,
  title = "Project Chat",
  placeholder = "Type your message...",
  emptyStateTitle = "Start a conversation",
  emptyStateDescription = "Ask questions and get AI-powered insights about your project.",
  suggestedQuestions = [
    "Summarize the key findings",
    "What are the main recommendations?",
    "Explain the validation results"
  ],
  selectedPersona = null
}: ChatDrawerProps) => {
  // State for view navigation - REMOVED currentView as we always stay in chat

  // Data state
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeThread, setActiveThread] = useState<ChatThread | null>(null);

  // UI state
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isThreadsLoading, setIsThreadsLoading] = useState(false);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<ChatMessage[]>([]); // To prevent stale closures

  // Auth
  const token = useAuthStore((state) => state.token);

  // Sync ref
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Load threads when drawer opens, but don't blocking the view
  useEffect(() => {
    if (isOpen && projectId && organizationId) {
      fetchThreads();
      // On open, if no active thread, we are in "New Chat" mode by default (activeThread is null)
      if (!activeThread) {
        setMessages([]);
      }
    }
  }, [isOpen, projectId, organizationId]);

  const fetchThreads = async () => {
    if (!projectId || !organizationId) return;
    setIsThreadsLoading(true);
    try {
      const response = await projectChatService.getThreads(organizationId, projectId);
      setThreads((response.threads || []).sort((a: ChatThread, b: ChatThread) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
    } catch (error) {
      console.error('Failed to load threads:', error);
      toast.error('Failed to load chat history');
    } finally {
      setIsThreadsLoading(false);
    }
  };

  const startNewChat = () => {
    setActiveThread(null);
    setMessages([]);
    setInputMessage('');
    // Ensure we focus input? (Input has autoFocus but that's only on mount usually)
  };

  const selectThread = async (thread: ChatThread) => {
    if (!projectId || !organizationId) return;

    setActiveThread(thread);
    setMessages([]); // Clear previous messages immediately
    setIsLoading(true);

    try {
      const response = await projectChatService.getMessages(organizationId, thread.id, { order: 'asc' });
      const mappedMessages: ChatMessage[] = (response.messages || []).map((msg: any) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.created_at),
        metadata: msg.metadata
      })).sort((a: ChatMessage, b: ChatMessage) => a.timestamp.getTime() - b.timestamp.getTime());

      setMessages(mappedMessages);
    } catch (error) {
      console.error('Failed to load messages:', error);
      toast.error('Failed to load messages');
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim() || !projectId || !organizationId) return;

    const messageContent = inputMessage.trim();
    setInputMessage('');

    const userMessage: ChatMessage = {
      id: `temp_${Date.now()}`,
      role: 'user',
      content: messageContent,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    let currentThread = activeThread;

    try {
      // If no active thread, create one first
      if (!currentThread) {
        // Create title from first few words of message or default
        const title = messageContent.substring(0, 30) + (messageContent.length > 30 ? '...' : '');
        try {
          currentThread = await projectChatService.createThread(organizationId, projectId, title);
          setActiveThread(currentThread);
          setThreads(prev => [currentThread!, ...prev]); // Add to history
        } catch (err) {
          console.error('Failed to create thread', err);
          throw new Error('Failed to start conversation');
        }
      }

      if (!currentThread) throw new Error('No active thread');

      const response = await projectChatService.postMessage(organizationId, currentThread.id, messageContent);

      if (response.assistant_message) {
        const assistantMessage: ChatMessage = {
          id: response.assistant_message.id,
          role: 'assistant',
          content: response.assistant_message.content,
          timestamp: new Date(response.assistant_message.created_at),
          metadata: response.assistant_message.metadata
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error: any) {
      console.error('Failed to send message:', error);
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: 'system',
        content: '**Error**: Failed to send message. Please try again.',
        timestamp: new Date(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
      toast.error('Failed to send message');
    } finally {
      setIsLoading(false);
    }
  }, [inputMessage, projectId, organizationId, activeThread]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-gray-900/20 backdrop-blur-sm dark:bg-black/40 transition-opacity h-screen"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        className={`absolute right-0 top-0 h-screen w-full sm:w-[450px] bg-white dark:bg-gray-800 shadow-2xl transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : 'translate-x-full'
          } border-l border-gray-200 dark:border-gray-700 flex flex-col`}
        role="dialog"
        aria-label={title}
      >
        {/* Main Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-20">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 bg-brand-100 dark:bg-brand-900/30 rounded-lg flex items-center justify-center text-brand-600 dark:text-brand-400 shrink-0">
              <MessageCircle className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-brand-500 dark:text-white truncate">
                {activeThread ? activeThread.title : "New Chat"}
              </h3>
              <p className="text-xs text-brand-600 dark:text-brand-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 inline-block"></span>
                Chat with Project
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {/* History Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="hover:bg-gray-100 dark:hover:bg-gray-700">
                  <History className="h-4 w-4 text-gray-500" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 max-h-80 overflow-y-auto">
                <div className="px-2 py-1.5 text-xs font-semibold text-gray-500">Recent Chats</div>
                {isThreadsLoading ? (
                  <div className="p-2 space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                  </div>
                ) : threads.length === 0 ? (
                  <div className="px-2 py-2 text-sm text-gray-500">No history available</div>
                ) : (
                  threads.map(thread => (
                    <DropdownMenuItem key={thread.id} onClick={() => selectThread(thread)} className="cursor-pointer">
                      <div className="flex flex-col gap-0.5 max-w-full">
                        <span className="truncate font-medium text-brand-600">{thread.title || "Untitled"}</span>
                        <span className="text-xs text-gray-500">{new Date(thread.updated_at).toLocaleDateString()}</span>
                      </div>
                    </DropdownMenuItem>
                  ))
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            {/* New Chat Button */}
            <Button variant="ghost" size="icon" onClick={startNewChat} className="hover:bg-gray-100 dark:hover:bg-gray-700" title="New Chat">
              <Plus className="h-4 w-4 text-gray-500" />
            </Button>

            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 h-8 w-8"
              aria-label="Close chat"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Chat Content - Main View */}
        <div className="flex-1 flex flex-col relative overflow-hidden">
          {/* Chat Messages */}
          <div className="flex-1 overflow-hidden pb-[80px]">
            <ScrollArea className="h-full p-4">
              {messages.length === 0 ? (
                <div className="text-center py-8 mt-10">
                  <div className="w-12 h-12 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                    <MessageCircle className="h-6 w-6 text-brand-600 dark:text-brand-400" />
                  </div>
                  <h4 className="font-medium text-brand-500 dark:text-white mb-2">{emptyStateTitle}</h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs mx-auto">
                    {emptyStateDescription}
                  </p>
                  {suggestedQuestions.length > 0 && (
                    <div className="mt-6 text-left max-w-xs mx-auto">
                      <p className="text-xs text-gray-500 text-center mb-2">Suggested questions</p>
                      <div className="space-y-2">
                        {suggestedQuestions.map((question, index) => (
                          <button
                            key={index}
                            onClick={() => {
                              setInputMessage(question);
                              // Optional: auto-send could be implemented here by calling sendMessage() after state update 
                              // But setState is async, better to call a helper that accepts content
                            }}
                            className="w-full text-left text-sm p-2 rounded bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 text-brand-600 dark:text-brand-400 transition-colors"
                          >
                            {question}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-6 pb-4">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${message.role === 'user'
                          ? 'bg-brand-600 text-white rounded-br-none'
                          : message.role === 'system'
                            ? 'bg-red-50 border border-red-200 text-red-800'
                            : 'bg-white border border-gray-200 dark:bg-gray-800 dark:border-gray-700 text-gray-900 dark:text-white rounded-bl-none'
                          }`}
                      >
                        {message.role === 'user' ? (
                          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                        ) : (
                          <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ChatMarkdownRenderer content={message.content} />
                          </div>
                        )}
                        <div
                          className={`text-[10px] mt-1.5 opacity-70 ${message.role === 'user'
                            ? 'text-brand-100'
                            : 'text-gray-500 dark:text-gray-400'
                            }`}
                        >
                          {message.timestamp.toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </div>
                      </div>
                    </div>
                  ))}

                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-white border border-gray-200 dark:bg-gray-800 dark:border-gray-700 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
                        <div className="flex gap-1.5 items-center h-5">
                          <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce"></div>
                          <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </ScrollArea>
          </div>

          {/* Input Area - Absolute Positioned */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-50">
            <div className="flex gap-2">
              <Input
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={placeholder}
                disabled={isLoading}
                className="flex-1  bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 "
                autoFocus
              />
              <Button
                onClick={sendMessage}
                disabled={isLoading || !inputMessage.trim()}
                size="icon"
                className="bg-brand-600 hover:bg-brand-700 shrink-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

});

ChatDrawer.displayName = 'ChatDrawer';

export default ChatDrawer;
