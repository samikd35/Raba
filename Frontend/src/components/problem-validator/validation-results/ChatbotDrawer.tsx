"use client";

import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageCircle, RefreshCw, X, Send } from "lucide-react";
import { useToken } from "@/stores/authStore";
import toast from "react-hot-toast";
import { ChatMessage, ChatResponse } from "./types";

// Chat Markdown Renderer Component
const ChatMarkdownRenderer = React.memo(({ content }: { content: string }) => {
    const processedContent = useMemo(() => content, [content]);

    return (
        <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:mt-2 prose-headings:mb-2 prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    h1: ({ node, ...props }) => <h3 className="text-base font-semibold mt-3 mb-2 text-gray-900 dark:text-white" {...props} />,
                    h2: ({ node, ...props }) => <h4 className="text-sm font-medium mt-2 mb-1 text-gray-900 dark:text-white" {...props} />,
                    h3: ({ node, ...props }) => <h5 className="text-sm font-medium mt-2 mb-1 text-gray-900 dark:text-white" {...props} />,
                    p: ({ node, ...props }) => <p className="my-1 text-sm leading-relaxed" {...props} />,
                    ul: ({ node, ...props }) => <ul className="list-disc list-outside pl-4 my-1 space-y-0.5" {...props} />,
                    ol: ({ node, ...props }) => <ol className="list-decimal list-outside pl-4 my-1 space-y-0.5" {...props} />,
                    li: ({ node, ...props }) => <li className="my-0.5 text-sm" {...props} />,
                    a: ({ node, href, ...props }) => (
                        <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-500 hover:text-blue-600 underline text-sm"
                            {...props}
                        />
                    ),
                    strong: ({ node, ...props }) => <strong className="font-semibold text-gray-900 dark:text-white" {...props} />,
                    em: ({ node, ...props }) => <em className="italic" {...props} />,
                    code: ({ node, ...props }) => {
                        const isInline = !props.className?.includes('language-');
                        return isInline ? (
                            <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs font-mono" {...props} />
                        ) : (
                            <pre className="bg-gray-100 dark:bg-gray-700 p-2 rounded my-2 overflow-x-auto">
                                <code className="text-xs font-mono" {...props} />
                            </pre>
                        );
                    },
                    blockquote: ({ node, ...props }) => (
                        <blockquote className="border-l-3 border-gray-300 dark:border-gray-600 pl-3 italic my-2 text-sm text-gray-600 dark:text-gray-300" {...props} />
                    ),
                    table: ({ node, ...props }) => (
                        <div className="overflow-x-auto my-2">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-sm" {...props} />
                        </div>
                    ),
                    thead: ({ node, ...props }) => <thead className="bg-gray-50 dark:bg-gray-800" {...props} />,
                    tbody: ({ node, ...props }) => <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props} />,
                    th: ({ node, ...props }) => <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider" {...props} />,
                    td: ({ node, ...props }) => <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300" {...props} />,
                    hr: ({ node, ...props }) => <hr className="my-2 border-gray-200 dark:border-gray-700" {...props} />,
                }}
            >
                {processedContent}
            </ReactMarkdown>
        </div>
    );
});

ChatMarkdownRenderer.displayName = 'ChatMarkdownRenderer';

interface ChatbotDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    reportId: string | null;
}

export const ChatbotDrawer = React.memo(({
    isOpen,
    onClose,
    reportId
}: ChatbotDrawerProps) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [chatSessionId] = useState(() => `chat_session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const token = useToken();

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
    }, [messages, scrollToBottom]);

    const sendMessage = useCallback(async () => {
        if (!inputMessage.trim() || !reportId || !token) return;

        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        const userMessage: ChatMessage = {
            id: `user_${Date.now()}`,
            role: 'user',
            content: inputMessage.trim(),
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMessage]);
        setInputMessage('');
        setIsLoading(true);

        try {
            abortControllerRef.current = new AbortController();

            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    report_id: reportId,
                    content: inputMessage.trim(),
                    web_search_enabled: false,
                    chat_session_id: chatSessionId
                }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data: ChatResponse = await response.json();

            if (data.success) {
                const assistantMessage: ChatMessage = {
                    id: data.id || `assistant_${Date.now()}`,
                    role: 'assistant',
                    content: data.content,
                    timestamp: new Date()
                };
                setMessages(prev => [...prev, assistantMessage]);
            } else {
                throw new Error(data.error || 'Failed to get response from AI');
            }
        } catch (error: unknown) {
            if (error instanceof Error && error.name === 'AbortError') return;

            console.error('Chat API error:', error);
            const errorMessage: ChatMessage = {
                id: `error_${Date.now()}`,
                role: 'assistant',
                content: error instanceof Error && error.message.includes('Network')
                    ? '**Network Error**: Failed to connect to AI service. Please try again.'
                    : `**Error**: ${error instanceof Error ? error.message : 'Failed to get response from AI'}`,
                timestamp: new Date()
            };
            setMessages(prev => [...prev, errorMessage]);
            toast.error(error instanceof Error ? error.message : 'Failed to get AI response');
        } finally {
            setIsLoading(false);
            abortControllerRef.current = null;
        }
    }, [inputMessage, reportId, chatSessionId, token]);

    const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }, [sendMessage]);

    const clearChat = useCallback(() => {
        setMessages([]);
    }, []);

    const messageList = useMemo(() =>
        messages.map((message) => (
            <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
                <div
                    className={`max-w-[85%] rounded-lg px-3 py-2 ${message.role === 'user'
                        ? 'bg-brand-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                        }`}
                >
                    {message.role === 'user' ? (
                        <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                    ) : (
                        <ChatMarkdownRenderer content={message.content} />
                    )}
                    <div
                        className={`text-xs mt-1 ${message.role === 'user'
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
        )), [messages]
    );

    return (
        <div className={`fixed inset-0 z-50 ${isOpen ? 'block' : 'hidden'}`}>
            <div
                className="absolute inset-0 bg-brand-500/80 opacity-25"
                onClick={onClose}
            />

            <div className={`absolute right-0 top-0 h-full w-96 bg-white dark:bg-gray-800 shadow-2xl transform transition-transform duration-300 ease-in-out ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}>
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-brand-500 rounded-full flex items-center justify-center">
                            <MessageCircle className="h-4 w-4 text-white" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-900 dark:text-white">Chat with Report</h3>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={clearChat}
                            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                            disabled={messages.length === 0}
                        >
                            <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onClose}
                            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                <div className="flex-1 h-[calc(100%-8rem)] overflow-hidden">
                    <ScrollArea className="h-full p-4">
                        {messages.length === 0 ? (
                            <div className="text-center py-8">
                                <MessageCircle className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                                <h4 className="font-medium text-gray-900 dark:text-white mb-2">Start a conversation</h4>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    Ask questions about your validation report and get AI-powered insights.
                                </p>
                                <div className="mt-4 text-xs text-gray-400 dark:text-gray-500">
                                    <p>Try asking:</p>
                                    <ul className="mt-2 space-y-1">
                                        <li>• &quot;Summarize the key findings&quot;</li>
                                        <li>• &quot;What are the main recommendations?&quot;</li>
                                        <li>• &quot;Explain the market challenges&quot;</li>
                                    </ul>
                                </div>
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
                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </ScrollArea>
                </div>

                <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                    <div className="flex gap-2">
                        <Input
                            value={inputMessage}
                            onChange={(e) => setInputMessage(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Type your message..."
                            disabled={isLoading || !reportId}
                            className="flex-1"
                        />
                        <Button
                            onClick={sendMessage}
                            disabled={isLoading || !inputMessage.trim() || !reportId}
                            size="sm"
                            className="bg-brand-500 hover:bg-brand-600"
                        >
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                    {!reportId && (
                        <p className="text-xs text-red-500 mt-2">Report ID is required for chat</p>
                    )}
                </div>
            </div>
        </div>
    );
});

ChatbotDrawer.displayName = 'ChatbotDrawer';
