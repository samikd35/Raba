'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, AlertCircle, ArrowLeft, Plus, History, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';

// UI Components
import { Button } from '@/components/ui/button';
import AI_Input_Search from '@/components/AI_Input_Search';

// Chat Components
import ChatMessage from './ChatMessage';
import ChatTypingIndicator from './ChatTypingIndicator';
import ChatFollowUpSuggestions from './ChatFollowUpSuggestions';
import ChatWelcome from './ChatWelcome';
import ProjectChatHistoryDrawer from '@/components/ProjectChatHistoryDrawer';

// API & Types
import {
    createThread,
    listThreads,
    postMessage,
    getMessages,
    generateDefaultThreadTitle,
    ProjectChatAPIError,
} from '@/lib/api/projectChatService';
import { ChatThread, ChatThreadMessage, ProjectChatState, ProjectChatAction, ChatStatus } from '@/types/projectChat';

// Stores
import { useAuthStore } from '@/stores/authStore';

/**
 * ProjectChatView
 * 
 * Main container for the MAV project chat experience.
 * Handles thread management, message history, and AI interaction.
 */

// ============================================
// State Reducer
// ============================================

const initialState: ProjectChatState = {
    status: 'idle',
    threads: [],
    activeThread: null,
    messages: [],
    hasMoreMessages: false,
    messageCursor: null,
    followUpSuggestions: [],
    error: null,
    isHistoryOpen: false,
};

function chatReducer(state: ProjectChatState, action: ProjectChatAction): ProjectChatState {
    switch (action.type) {
        case 'RESET':
            return initialState;
        case 'SET_LOADING':
            return { ...state, status: action.payload, error: null };
        case 'SET_ERROR':
            return { ...state, status: 'error', error: action.payload };
        case 'CLEAR_ERROR':
            return { ...state, error: null };
        case 'SET_THREADS':
            return { ...state, threads: action.payload };
        case 'ADD_THREAD':
            return { ...state, threads: [action.payload, ...state.threads] };
        case 'SET_ACTIVE_THREAD':
            return { ...state, activeThread: action.payload, status: 'ready' };
        case 'REMOVE_THREAD':
            return {
                ...state,
                threads: state.threads.filter(t => t.id !== action.payload),
                activeThread: state.activeThread?.id === action.payload ? null : state.activeThread,
            };
        case 'SET_MESSAGES':
            return {
                ...state,
                messages: action.payload.messages,
                hasMoreMessages: action.payload.hasMore,
                messageCursor: action.payload.cursor,
            };
        case 'PREPEND_MESSAGES':
            return {
                ...state,
                messages: [...action.payload.messages, ...state.messages],
                hasMoreMessages: action.payload.hasMore,
                messageCursor: action.payload.cursor,
            };
        case 'ADD_MESSAGE':
            return { ...state, messages: [...state.messages, action.payload] };
        case 'ADD_ASSISTANT_MESSAGE':
            return {
                ...state,
                messages: [...state.messages, action.payload.assistantMessage],
                followUpSuggestions: action.payload.followUps,
                status: 'ready',
            };
        case 'ADD_MESSAGES':
            return {
                ...state,
                messages: [...state.messages, action.payload.userMessage, action.payload.assistantMessage],
                followUpSuggestions: action.payload.followUps,
                status: 'ready',
            };
        case 'SET_FOLLOW_UPS':
            return { ...state, followUpSuggestions: action.payload };
        case 'TOGGLE_HISTORY':
            return { ...state, isHistoryOpen: action.payload ?? !state.isHistoryOpen };
        case 'SET_READY':
            return { ...state, status: 'ready' };
        default:
            return state;
    }
}

// ============================================
// Animation Variants
// ============================================

const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { type: 'spring' as const, stiffness: 100 } },
    exit: { opacity: 0, transition: { duration: 0.2 } },
};

// ============================================
// Main Component
// ============================================

interface ProjectChatViewProps {
    projectId: string;
    onBack: () => void;
}

export default function ProjectChatView({ projectId, onBack }: ProjectChatViewProps) {
    // Auth Hooks
    const { token, isAuthenticated, isInitialized: authInitialized } = useAuthStore();

    // UI & Business Logic State
    const [state, dispatch] = React.useReducer(chatReducer, initialState);
    const [isPageLoading, setIsPageLoading] = useState(true);

    // Operational Refs
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const hasInitialized = useRef(false);
    const setupAbortControllerRef = useRef<AbortController | null>(null);
    const messageAbortControllerRef = useRef<AbortController | null>(null);

    // ============================================
    // Helpers
    // ============================================

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [state.messages, scrollToBottom]);

    // ============================================
    // Action: Load Messages
    // ============================================

    const fetchThreadMessages = useCallback(async (threadId: string, signal?: AbortSignal) => {
        if (!token) return;

        dispatch({ type: 'SET_LOADING', payload: 'loading_messages' });

        try {
            console.log('[ProjectChat] Loading messages for thread:', threadId);
            const response = await getMessages(threadId, { limit: 50, order: 'desc' }, token, signal);

            // Correct order for chat: oldest first
            const chronologicalMessages = [...response.messages].reverse();

            dispatch({
                type: 'SET_MESSAGES',
                payload: {
                    messages: chronologicalMessages,
                    hasMore: response.has_more,
                    cursor: response.next_cursor,
                },
            });

            // Restore suggestions from latest assistant response
            const lastAssistant = response.messages.find(m => m.role === 'assistant');
            if (lastAssistant?.metadata?.follow_ups) {
                dispatch({
                    type: 'SET_FOLLOW_UPS',
                    payload: lastAssistant.metadata.follow_ups as string[]
                });
            } else {
                dispatch({ type: 'SET_FOLLOW_UPS', payload: [] });
            }
        } catch (error) {
            if (error instanceof ProjectChatAPIError && error.code === 'REQUEST_CANCELLED') return;

            console.error('[ProjectChat] Failed to load messages:', error);
            dispatch({ type: 'SET_ERROR', payload: 'Failed to load conversation history' });
            toast.error('Failed to load conversation history');
        } finally {
            dispatch({ type: 'SET_READY' });
        }
    }, [token]);

    // ============================================
    // Lifecycle: Initial Session Setup
    // ============================================

    useEffect(() => {
        let isCancelled = false;

        const initializeChat = async () => {
            // Guard against redundant runs (Strict Mode)
            if (hasInitialized.current) {
                if (isPageLoading) setIsPageLoading(false);
                return;
            }

            // Guard against missing auth/context
            if (!authInitialized) return;
            if (!isAuthenticated || !token || !projectId) {
                if (!isAuthenticated && authInitialized) setIsPageLoading(false);
                return;
            }

            console.log('[ProjectChat] Initializing session...');

            // Cleanup previous setup attempts
            if (setupAbortControllerRef.current) setupAbortControllerRef.current.abort();
            const controller = new AbortController();
            setupAbortControllerRef.current = controller;

            dispatch({ type: 'SET_LOADING', payload: 'loading_threads' });

            try {
                // Step 1: Check for existing conversation to resume
                const listResponse = await listThreads(
                    projectId,
                    { limit: 5, status: 'active' },
                    token,
                    controller.signal
                );

                if (isCancelled) return;

                if (listResponse.threads && listResponse.threads.length > 0) {
                    const existingThread = listResponse.threads[0];
                    console.log('[ProjectChat] Resuming existing thread:', existingThread.id);

                    dispatch({ type: 'SET_ACTIVE_THREAD', payload: existingThread });
                    await fetchThreadMessages(existingThread.id, controller.signal);

                    if (!isCancelled) hasInitialized.current = true;
                } else {
                    // Step 2: Create a first-time session
                    console.log('[ProjectChat] Creating new session...');
                    dispatch({ type: 'SET_LOADING', payload: 'creating_thread' });

                    const newThread = await createThread(
                        projectId,
                        {
                            title: generateDefaultThreadTitle(),
                            metadata: {},
                        },
                        token,
                        controller.signal
                    );

                    if (isCancelled) return;

                    dispatch({ type: 'ADD_THREAD', payload: newThread });
                    dispatch({ type: 'SET_ACTIVE_THREAD', payload: newThread });

                    if (!isCancelled) {
                        hasInitialized.current = true;
                        toast.success('New chat session started');
                    }
                }
            } catch (error) {
                if (isCancelled) return;

                console.error('[ProjectChat] Setup Error:', error);

                if (error instanceof ProjectChatAPIError && error.code !== 'REQUEST_CANCELLED') {
                    dispatch({ type: 'SET_ERROR', payload: error.message });
                    toast.error('Failed to connect to chat service');
                }

                // Allow user to retry manually via "New Chat" if init fails
                hasInitialized.current = true;
            } finally {
                if (!isCancelled) setIsPageLoading(false);
            }
        };

        initializeChat();

        return () => {
            isCancelled = true;
            if (setupAbortControllerRef.current) setupAbortControllerRef.current.abort();
        };
    }, [authInitialized, isAuthenticated, token, projectId, fetchThreadMessages]);

    // ============================================
    // Handlers
    // ============================================

    const handleNewChat = async () => {
        if (!token || !projectId) return;

        // Abort any ongoing message or setup
        if (messageAbortControllerRef.current) messageAbortControllerRef.current.abort();
        messageAbortControllerRef.current = new AbortController();

        dispatch({ type: 'SET_LOADING', payload: 'creating_thread' });

        try {
            const newThread = await createThread(
                projectId,
                {
                    title: generateDefaultThreadTitle(),
                    metadata: {},
                },
                token,
                messageAbortControllerRef.current.signal
            );

            dispatch({ type: 'ADD_THREAD', payload: newThread });
            dispatch({ type: 'SET_ACTIVE_THREAD', payload: newThread });
            dispatch({ type: 'SET_MESSAGES', payload: { messages: [], hasMore: false, cursor: null } });
            dispatch({ type: 'SET_FOLLOW_UPS', payload: [] });

            toast.success('Started a fresh conversation');
        } catch (error) {
            if (error instanceof ProjectChatAPIError && error.code === 'REQUEST_CANCELLED') return;

            console.error('[ProjectChat] Failed to create new chat:', error);
            toast.error('Failed to start new chat');
            dispatch({ type: 'SET_READY' });
        }
    };

    const handleSelectThread = (thread: ChatThread) => {
        // Stop current message if switching threads
        if (messageAbortControllerRef.current) messageAbortControllerRef.current.abort();

        dispatch({ type: 'SET_ACTIVE_THREAD', payload: thread });
        fetchThreadMessages(thread.id);
    };

    const handleInputSubmit = async (value: string) => {
        const trimmed = value.trim();
        if (!trimmed || !state.activeThread || !token) return;

        // Reset previous message controller for the new request
        if (messageAbortControllerRef.current) messageAbortControllerRef.current.abort();
        messageAbortControllerRef.current = new AbortController();

        const optimisticUserMessage: ChatThreadMessage = {
            id: `temp-${Date.now()}`,
            thread_id: state.activeThread.id,
            role: 'user',
            content: trimmed,
            citations: [],
            created_at: new Date().toISOString(),
            metadata: {},
        };

        dispatch({ type: 'ADD_MESSAGE', payload: optimisticUserMessage });
        dispatch({ type: 'SET_FOLLOW_UPS', payload: [] });
        dispatch({ type: 'SET_LOADING', payload: 'sending' });

        try {
            const response = await postMessage(
                state.activeThread.id,
                {
                    content: trimmed,
                    metadata: {},
                },
                token,
                messageAbortControllerRef.current.signal
            );

            dispatch({
                type: 'ADD_ASSISTANT_MESSAGE',
                payload: {
                    assistantMessage: response.assistant_message,
                    followUps: response.follow_ups || [],
                },
            });
        } catch (error) {
            if (error instanceof ProjectChatAPIError && error.code === 'REQUEST_CANCELLED') return;

            console.error('[ProjectChat] Message send error:', error);
            dispatch({ type: 'SET_ERROR', payload: 'Failed to get response. Please try again.' });
            toast.error('Failed to get AI response');
            dispatch({ type: 'SET_READY' });
        }
    };

    const handleFollowUpClick = (suggestion: string) => {
        handleInputSubmit(suggestion);
    };

    // ============================================
    // Render
    // ============================================

    if (isPageLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                    className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full"
                />
            </div>
        );
    }

    const isInputDisabled =
        state.status === 'creating_thread' ||
        state.status === 'sending' ||
        state.status === 'loading_messages' ||
        !state.activeThread;

    return (
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {/* Header Bar */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="px-2"
            >
                <div className="flex items-center justify-between p-2 bg-brand-25/50 dark:bg-gray-900/60 border border-brand-100 dark:border-gray-800/70 rounded-xl ">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2 px-4 py-2 bg-brand-50/50 dark:bg-gray-800/60 border border-brand-100/50 dark:border-gray-700/50 rounded-lg shadow-inner">
                            <AlertCircle className="w-4 h-4 text-brand-500 dark:text-brand-400" />
                            <p className="text-xs font-semibold text-brand-700 dark:text-brand-300 truncate max-w-[200px] sm:max-w-xs transition-colors">
                                {state.activeThread
                                    ? state.activeThread.title
                                    : 'Initializing chat...'}
                            </p>
                        </div>

                        {(state.status === 'creating_thread' || state.status === 'loading_messages') && (
                            <div className="flex items-center gap-2 text-[11px] text-brand-600 dark:text-brand-400 font-medium animate-pulse">
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                <span>Syncing...</span>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-2 sm:gap-3">
                        <Button
                            variant="outline"
                            size="sm"
                            className="h-9 px-3 border-brand-200 dark:border-gray-700 text-brand-700 dark:text-gray-300 hover:bg-brand-50 dark:hover:bg-gray-800 transition-all font-medium"
                            onClick={onBack}
                        >
                            <ArrowLeft className="w-3.5 h-3.5 mr-2" />
                            <span className="hidden sm:inline">Projects</span>
                        </Button>

                        <Button
                            variant="default"
                            size="sm"
                            className="h-9 px-3 bg-brand-600 hover:bg-brand-700 dark:bg-brand-600 dark:hover:bg-brand-700 hover:shadow-lg transition-all font-medium"
                            onClick={handleNewChat}
                            disabled={state.status === 'creating_thread' || state.status === 'loading_messages'}
                        >
                            <Plus className="w-3.5 h-3.5 mr-2" />
                            <span className="hidden sm:inline">New Chat</span>
                        </Button>

                        <ProjectChatHistoryDrawer
                            projectId={projectId}
                            activeThreadId={state.activeThread?.id}
                            onSelectThread={handleSelectThread}
                            onNewChat={handleNewChat}
                        />
                    </div>
                </div>
            </motion.div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden relative">
                {state.messages.length === 0 && state.status !== 'creating_thread' && state.status !== 'loading_messages' && (
                    <ChatWelcome />
                )}

                <div className="max-w-5xl mx-auto space-y-4 px-4 sm:px-6 md:px-8 py-4">
                    <AnimatePresence mode="popLayout" initial={false}>
                        {state.messages.map((msg) => (
                            <ChatMessage
                                key={msg.id}
                                message={msg}
                                variants={itemVariants}
                            />
                        ))}
                    </AnimatePresence>

                    {state.status === 'sending' && <ChatTypingIndicator />}

                    <ChatFollowUpSuggestions
                        suggestions={state.followUpSuggestions}
                        onSuggestionClick={handleFollowUpClick}
                    />

                    <div ref={messagesEndRef} className="h-4" />
                </div>
            </div>

            {/* Input Area */}
            <motion.div
                className="sticky bottom-0 z-10 flex-shrink-0 bg-white/80 dark:bg-gray-900/80 border-t border-gray-200/60 dark:border-gray-800/60 pt-3 pb-4 backdrop-blur-xl"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
            >
                <div className="max-w-4xl mx-auto px-4 sm:px-6 md:px-8 w-full">
                    <AI_Input_Search
                        placeholder={
                            state.activeThread
                                ? 'Ask a question about your project...'
                                : 'Initializing chat session...'
                        }
                        onSubmit={handleInputSubmit}
                        disabled={isInputDisabled}
                    />
                </div>
            </motion.div>

            {/* Global Error Overlay */}
            {state.error && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="fixed bottom-24 left-1/2 transform -translate-x-1/2 bg-red-50 border border-red-200 text-red-800 px-6 py-3 rounded-xl shadow-xl z-50 flex items-center gap-3 backdrop-blur-md"
                >
                    <AlertCircle className="w-5 h-5 text-red-500" />
                    <p className="text-sm font-medium">{state.error}</p>
                    <Button
                        variant="ghost"
                        size="sm"
                        className="ml-4 h-7 text-red-700 hover:bg-red-100"
                        onClick={() => dispatch({ type: 'CLEAR_ERROR' })}
                    >
                        Dismiss
                    </Button>
                </motion.div>
            )}
        </div>
    );
}
