'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Bot, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChatThreadMessage } from '@/types/projectChat';

interface ChatMessageProps {
    message: ChatThreadMessage;
    variants: any;
}

export default function ChatMessage({ message, variants }: ChatMessageProps) {
    return (
        <motion.div
            layout
            initial="hidden"
            animate="visible"
            exit="exit"
            variants={variants}
            className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
            {/* Bot Avatar */}
            {message.role === 'assistant' && (
                <div className="flex-shrink-0 w-8 h-8 bg-brand-100 dark:bg-brand-900/30 rounded-full flex items-center justify-center mt-1">
                    <Bot className="h-4 w-4 text-brand-600 dark:text-brand-400" />
                </div>
            )}

            {/* Message Bubble */}
            <div
                className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-2 shadow-sm overflow-hidden ${message.role === 'user'
                        ? 'bg-brand-600 text-white rounded-br-none'
                        : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-100 dark:border-gray-700 rounded-bl-none'
                    }`}
            >
                {message.role === 'user' ? (
                    <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
                ) : (
                    <div className="text-sm leading-relaxed prose dark:prose-invert max-w-none prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-pre:bg-gray-100 dark:prose-pre:bg-gray-900 prose-pre:p-3 prose-pre:rounded-lg">
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                a: ({ ...props }) => (
                                    <a
                                        {...props}
                                        className="text-brand-600 dark:text-brand-400 hover:underline"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    />
                                ),
                                code: ({ children, ...props }) => {
                                    const isInline = (props as any).inline;
                                    return isInline ? (
                                        <code
                                            {...props}
                                            className="bg-gray-100 dark:bg-gray-900 px-1 py-0.5 rounded text-xs font-mono text-brand-600 dark:text-brand-400"
                                        >
                                            {children}
                                        </code>
                                    ) : (
                                        <code {...props} className="text-xs font-mono tab-size-2">
                                            {children}
                                        </code>
                                    );
                                },
                                ul: ({ ...props }) => <ul {...props} className="list-disc pl-4 space-y-1" />,
                                ol: ({ ...props }) => <ol {...props} className="list-decimal pl-4 space-y-1" />,
                                h1: ({ ...props }) => (
                                    <h1 {...props} className="text-lg font-bold text-gray-900 dark:text-white mt-4 first:mt-0" />
                                ),
                                h2: ({ ...props }) => (
                                    <h2 {...props} className="text-base font-bold text-gray-900 dark:text-white mt-3" />
                                ),
                                h3: ({ ...props }) => <h3 {...props} className="text-sm font-bold text-gray-900 dark:text-white mt-2" />,
                                strong: ({ ...props }) => <strong {...props} className="font-bold text-gray-900 dark:text-white" />,
                                em: ({ ...props }) => <em {...props} className="italic" />,
                                blockquote: ({ ...props }) => (
                                    <blockquote
                                        {...props}
                                        className="border-l-4 border-brand-200 dark:border-brand-800 pl-3 italic text-gray-600 dark:text-gray-400 my-2"
                                    />
                                ),
                            }}
                        >
                            {message.content}
                        </ReactMarkdown>
                    </div>
                )}
                <div
                    className={`text-[10px] opacity-70 flex items-center gap-1 mt-1 ${message.role === 'user' ? 'justify-end text-brand-100' : 'text-gray-400'
                        }`}
                >
                    <span>
                        {new Date(message.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                        })}
                    </span>
                </div>
            </div>

            {/* User Avatar */}
            {message.role === 'user' && (
                <div className="flex-shrink-0 w-8 h-8 bg-brand-600 rounded-full flex items-center justify-center mt-1">
                    <User className="h-4 w-4 text-white" />
                </div>
            )}
        </motion.div>
    );
}
