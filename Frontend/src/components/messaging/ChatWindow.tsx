'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageCircle,
  X,
  Minimize2,
  Maximize2,
  Send,
  Bold,
  Italic,
  Link as LinkIcon,
  List,
  AlertCircle,
  Flag,
} from 'lucide-react';
import { toast } from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useWebSocket } from '@/hooks/useWebSocket';
import { messagingAPI } from '@/lib/api/messagingService';
import { cofounderAPI } from '@/lib/api/cofounderService';
import type {
  Message,
  Thread,
  WSServerMessage,
} from '@/types/messaging';
import { MESSAGE_CONSTANTS } from '@/types/messaging';
import UserAvatar from '@/components/ui/avatar/UserAvatar';
import { useAuthStore } from '@/stores/authStore';
import { useReportModal } from '@/hooks/useReportModal';
import ReportModal from '@/components/cofounder/reports/ReportModal';
import MessageErrorModal from './MessageErrorModal';
import { parseMessagingError, type MessagingError } from '@/types/messagingErrors';

interface ChatWindowProps {
  userId?: string;
}

export default function ChatWindow({ userId: userIdProp }: ChatWindowProps) {
  // Get userId from auth store if not provided
  const getUserId = useAuthStore((state) => state.getUserId);
  const userId = userIdProp || getUserId() || '';

  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messageInput, setMessageInput] = useState('');
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [onlineUsers, setOnlineUsers] = useState<Set<string>>(new Set());
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const [participantMetadata, setParticipantMetadata] = useState<Record<string, { name: string; avatar?: string }>>({});
  const [showReportTooltip, setShowReportTooltip] = useState(false);
  const [messagingError, setMessagingError] = useState<MessagingError | null>(null);
  const [showErrorModal, setShowErrorModal] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const reportModal = useReportModal();

  // Don't render if no userId available
  if (!userId) {
    return null;
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  /**
   * Fetch user name for a given user_id
   */
  const fetchUserName = useCallback(async (userId: string): Promise<{ name: string; avatar?: string } | null> => {
    try {
      // Try to get cofounder profile directory - this should have user info
      const searchResponse = await cofounderAPI.profiles.searchDirectory({}, 1, 100);
      const userProfile = searchResponse.items.find((profile: any) => profile.user_id === userId);

      if (userProfile) {
        const fullName = userProfile.full_name || `${userProfile.first_name} ${userProfile.last_name}`;
        return {
          name: fullName,
          avatar: userProfile.profile_picture_url,
        };
      }
      return null;
    } catch (error) {
      console.error(`[ChatWindow] Failed to fetch user name for ${userId}:`, error);
      return null;
    }
  }, []);

  /**
   * Load threads from API
   */
  const loadThreads = useCallback(async () => {
    try {
      const response = await messagingAPI.getThreads(1, 20);
      setThreads(response.threads);
      setThreadsError(null);

      // Fetch participant metadata for all threads
      const userIds = response.threads.map((thread) => thread.other_user_id);
      const uniqueUserIds = [...new Set(userIds)];

      // Fetch names for all participants
      for (const userId of uniqueUserIds) {
        const userInfo = await fetchUserName(userId);
        if (userInfo) {
          setParticipantMetadata((prev) => ({
            ...prev,
            [userId]: userInfo,
          }));
        }
      }
    } catch (error: any) {
      console.error('[ChatWindow] Failed to load threads:', error);
      // Don't throw - just log the error and continue with empty threads
      // The WebSocket can still be used to send new messages even if threads fail to load
      setThreads([]);

      const errorMsg = error.details?.detail || error.message || 'Unknown error';
      setThreadsError(`Unable to load conversations: ${errorMsg}. You can still send new messages!`);
    }
  }, [fetchUserName]);

  /**
   * Load messages for a thread
   */
  const loadMessages = useCallback(async (threadId: string) => {
    try {
      const response = await messagingAPI.getMessages({
        thread_id: threadId,
        page: 1,
        per_page: 50,
        mark_as_read: true,
      });
      setMessages(response.messages);
      scrollToBottom();
    } catch (error) {
      console.error('[ChatWindow] Failed to load messages:', error);
    }
  }, []);

  /**
   * Handle authenticated connection
   */
  const handleAuthenticated = useCallback((authenticatedUserId: string) => {
    console.log('[ChatWindow] Authenticated as:', authenticatedUserId);
    loadThreads();
  }, [loadThreads]);

  /**
   * Handle incoming WebSocket messages
   */
  const handleWebSocketMessage = useCallback((data: WSServerMessage) => {
    switch (data.type) {
      case 'new_message':
      case 'message':
        // Handle new incoming message
        if (selectedThread && data.message.thread_id === selectedThread.id) {
          setMessages((prev) => {
            if (prev.some((m) => m.id === data.message.id)) return prev;
            return [...prev, data.message];
          });

          if (isOpen) {
            sendReadReceipt(data.message.thread_id, [data.message.id]);
          }

          scrollToBottom();
        }
        loadThreads();
        break;

      case 'message_sent':
        // Handle message sent confirmation
        console.log('[ChatWindow] message_sent received:', data);

        // Update thread ID if it was temporary
        if (selectedThread?.id.startsWith('temp-') && data.message.thread_id) {
          console.log('[ChatWindow] Updating thread ID from', selectedThread.id, 'to', data.message.thread_id);
          setSelectedThread((prev) => prev ? { ...prev, id: data.message.thread_id } : null);
        }

        // Replace optimistic message with real one or add new message
        if (selectedThread && (data.message.thread_id === selectedThread.id || selectedThread.id.startsWith('temp-'))) {
          setMessages((prev) => {
            // Check if this is a real message ID (not temp)
            const hasRealMessage = prev.some((m) => m.id === data.message.id && !m.id.startsWith('temp-'));
            if (hasRealMessage) {
              console.log('[ChatWindow] Message already exists, skipping');
              return prev;
            }

            // Remove any optimistic messages (temp IDs) and add the real message
            const withoutOptimistic = prev.filter((m) => !m.id.startsWith('temp-'));
            console.log('[ChatWindow] Replacing optimistic message with real message');
            return [...withoutOptimistic, data.message];
          });
          scrollToBottom();
        }
        loadThreads();
        break;

      case 'typing_indicator':
      case 'typing':
        // Handle typing indicator
        const typingSenderId = (data as any).sender_id || (data as any).user_id;
        const isTyping = (data as any).is_typing;

        setTypingUsers((prev) => {
          const next = new Set(prev);
          if (isTyping) {
            next.add(typingSenderId);
          } else {
            next.delete(typingSenderId);
          }
          return next;
        });
        break;

      case 'message_read':
      case 'read_receipt':
        // Handle read receipt
        const messageIds = (data as any).message_ids || ((data as any).message_id ? [(data as any).message_id] : []);

        setMessages((prev) =>
          prev.map((msg) =>
            messageIds.includes(msg.id) ? { ...msg, status: 'read' as const } : msg
          )
        );
        break;

      case 'presence':
        // Handle presence update
        const presenceIsOnline = (data as any).status === 'online';

        setOnlineUsers((prev) => {
          const next = new Set(prev);
          if (presenceIsOnline) {
            next.add((data as any).user_id);
          } else {
            next.delete((data as any).user_id);
          }
          return next;
        });
        break;

      case 'online_status_response':
        // Handle online status response
        setOnlineUsers(new Set(
          Object.entries((data as any).statuses)
            .filter(([_, isOnline]) => isOnline)
            .map(([userId]) => userId)
        ));
        break;

      case 'pong':
        // Handle heartbeat pong - no action needed
        break;

      case 'error':
        console.error('[ChatWindow] Server error:', data.error, data.code);
        break;

      default:
        // Silently ignore unknown message types - all important types are handled above
        break;
    }
  }, [selectedThread, isOpen, loadThreads]);

  // WebSocket connection using secure message-based authentication
  const {
    isConnected,
    isAuthenticated,
    error: wsError,
    sendMessage: sendWSMessage,
    sendTypingIndicator,
    sendReadReceipt,
  } = useWebSocket(messagingAPI.getWebSocketUrl(), {
    token: messagingAPI.getAuthToken(), // Send token in first message
    onMessage: handleWebSocketMessage,
    onAuthenticated: handleAuthenticated,
    onError: (error) => {
      console.error('[ChatWindow] WebSocket error:', error);
    },
  });

  /**
   * Select a thread and load its messages
   */
  const selectThread = useCallback((thread: Thread) => {
    setSelectedThread(thread);
    loadMessages(thread.id);

    setThreads((prev) =>
      prev.map((t) => (t.id === thread.id ? { ...t, unread_count: 0 } : t))
    );
  }, [loadMessages]);

  /**
   * Send a message
   */
  const handleSendMessage = useCallback(async () => {
    if (!messageInput.trim() || !selectedThread || !isAuthenticated) {
      return;
    }

    if (messageInput.length > MESSAGE_CONSTANTS.MAX_MESSAGE_LENGTH) {
      toast.error(`Message too long. Maximum ${MESSAGE_CONSTANTS.MAX_MESSAGE_LENGTH} characters.`);
      return;
    }

    const content = messageInput.trim();
    setMessageInput('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    // Optimistic UI: Add message immediately with temporary ID
    const optimisticMessage: Message = {
      id: `temp-${Date.now()}`,
      thread_id: selectedThread.id,
      sender_id: userId,
      recipient_id: selectedThread.other_user_id,
      content,
      status: 'sent',
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticMessage]);
    scrollToBottom();

    try {
      sendWSMessage({
        type: 'send_message',
        recipient_id: selectedThread.other_user_id,
        content,
      });
    } catch (error) {
      console.error('[ChatWindow] Send failed:', error);
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== optimisticMessage.id));
      setMessageInput(content);

      // Parse and display error gracefully
      const parsedError = parseMessagingError(error);
      setMessagingError(parsedError);
      setShowErrorModal(true);
    }
  }, [messageInput, selectedThread, isAuthenticated, isConnected, sendWSMessage, userId]);

  /**
   * Handle typing in message input
   */
  const handleTyping = useCallback(() => {
    if (!selectedThread || !isAuthenticated) return;

    sendTypingIndicator(selectedThread.other_user_id, true);

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      sendTypingIndicator(selectedThread.other_user_id, false);
    }, 3000);
  }, [selectedThread, isAuthenticated, sendTypingIndicator]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const insertMarkdown = (syntax: string, type: 'bold' | 'italic' | 'link' | 'list') => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = messageInput.substring(start, end);
    let newText = messageInput;
    let cursorPos = start;

    switch (type) {
      case 'bold':
        newText = messageInput.substring(0, start) + `**${selectedText || 'bold text'}**` + messageInput.substring(end);
        cursorPos = start + 2;
        break;
      case 'italic':
        newText = messageInput.substring(0, start) + `*${selectedText || 'italic text'}*` + messageInput.substring(end);
        cursorPos = start + 1;
        break;
      case 'link':
        newText = messageInput.substring(0, start) + `[${selectedText || 'link text'}](url)` + messageInput.substring(end);
        cursorPos = start + 1;
        break;
      case 'list':
        newText = messageInput.substring(0, start) + `\n- ${selectedText || 'list item'}` + messageInput.substring(end);
        cursorPos = start + 3;
        break;
    }

    setMessageInput(newText);
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(cursorPos, cursorPos);
    }, 0);
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessageInput(e.target.value);
    handleTyping();

    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  // Listen for custom events to open chat with specific user
  useEffect(() => {
    const handleOpenChat = async (event: CustomEvent) => {
      const { participantId, participantName, participantAvatar } = event.detail;

      if (!participantId) {
        console.error('[ChatWindow] No participantId in event');
        return;
      }

      // Store participant metadata
      if (participantName) {
        setParticipantMetadata((prev) => ({
          ...prev,
          [participantId]: {
            name: participantName,
            avatar: participantAvatar,
          },
        }));
      }

      setIsOpen(true);

      try {
        const existingThread = threads.find((t) => t.other_user_id === participantId);

        if (existingThread) {
          selectThread(existingThread);
        } else {
          const newThread: Thread = {
            id: `temp-${participantId}`,
            other_user_id: participantId,
            unread_count: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          };
          setSelectedThread(newThread);
          setMessages([]); // Clear messages for new thread
        }
      } catch (error) {
        console.error('[ChatWindow] Failed to open chat:', error);
        toast.error('Unable to open chat. Please try again later.');
        setIsOpen(false);
      }
    };

    window.addEventListener('openChat' as any, handleOpenChat);
    return () => {
      window.removeEventListener('openChat' as any, handleOpenChat);
    };
  }, [threads, selectThread, isOpen, selectedThread]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const totalUnread = threads.reduce((sum, thread) => sum + thread.unread_count, 0);

  return (
    <>
      {/* Chat Toggle Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 w-14 h-14 bg-brand-500 dark:bg-brand-400 text-white rounded-full shadow-lg hover:bg-brand-600 dark:hover:bg-brand-500 transition-colors flex items-center justify-center z-50"
          >
            <MessageCircle className="w-6 h-6" />
            {totalUnread > 0 && (
              <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-semibold">
                {totalUnread > 9 ? '9+' : totalUnread}
              </span>
            )}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className={`fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-2xl flex flex-col ${
              isExpanded
                ? 'inset-4 md:inset-8'
                : 'bottom-6 right-6 w-96 h-[600px]'
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-brand-500 dark:text-brand-400" />
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  {selectedThread ? (
                    <span>
                      {participantMetadata[selectedThread.other_user_id]?.name || selectedThread.other_user_id.slice(0, 8) + '...'}
                      {selectedThread.id.startsWith('temp-') && (
                        <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">(New)</span>
                      )}
                    </span>
                  ) : (
                    'Messages'
                  )}
                </h3>
                {isConnected && (
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isAuthenticated ? 'bg-green-500' : 'bg-yellow-500'
                    }`}
                    title={isAuthenticated ? 'Connected' : 'Connecting...'}
                  ></span>
                )}
                {wsError && (
                  <div title={wsError}>
                    <AlertCircle className="w-4 h-4 text-red-500" />
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                {selectedThread && (
                  <div className="relative">
                    <button
                      onClick={() => {
                        const participantName = participantMetadata[selectedThread.other_user_id]?.name || selectedThread.other_user_id;
                        reportModal.openReportModal({
                          type: 'profile',
                          id: selectedThread.other_user_id,
                          name: participantName,
                        });
                      }}
                      onMouseEnter={() => setShowReportTooltip(true)}
                      onMouseLeave={() => setShowReportTooltip(false)}
                      className="p-2 text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    >
                      <Flag className="w-4 h-4" />
                    </button>
                    {showReportTooltip && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded whitespace-nowrap z-10">
                        Report
                      </div>
                    )}
                  </div>
                )}
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => {
                    setIsOpen(false);
                    setSelectedThread(null);
                  }}
                  className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 flex overflow-hidden">
              {/* Threads List */}
              {!selectedThread && (
                <div className="flex-1 overflow-y-auto">
                  {threadsError && (
                    <div className="p-4 m-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-yellow-700 dark:text-yellow-300">
                          {threadsError}
                        </div>
                      </div>
                    </div>
                  )}
                  {threads.length === 0 && !threadsError ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
                      <MessageCircle className="w-12 h-12 mb-2 opacity-50" />
                      <p className="text-sm">No conversations yet</p>
                      {!isAuthenticated && (
                        <p className="text-xs mt-2">Connecting...</p>
                      )}
                      <p className="text-xs mt-4 text-center px-4">Click the Message button on a profile to start a conversation</p>
                    </div>
                  ) : threads.length > 0 ? (
                    <div className="divide-y divide-gray-200 dark:divide-gray-700">
                      {threads.map((thread) => {
                        const participantName = participantMetadata[thread.other_user_id]?.name;
                        return (
                          <button
                            key={thread.id}
                            onClick={() => selectThread(thread)}
                            className="w-full p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-left"
                          >
                            <div className="flex items-start gap-3">
                              <div className="relative">
                                <UserAvatar
                                  name={participantName || thread.other_user_id}
                                  size="medium"
                                />
                                {onlineUsers.has(thread.other_user_id) && (
                                  <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white dark:border-gray-800"></span>
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-1">
                                  <h4 className="font-medium text-gray-900 dark:text-white truncate">
                                    {participantName || thread.other_user_id.slice(0, 8) + '...'}
                                  </h4>
                                  {thread.unread_count > 0 && (
                                    <span className="ml-2 px-2 py-0.5 bg-brand-500 text-white text-xs rounded-full">
                                      {thread.unread_count}
                                    </span>
                                  )}
                                </div>
                                {thread.last_message_preview && (
                                  <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                                    {thread.last_message_preview}
                                  </p>
                                )}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400 px-4">
                      <MessageCircle className="w-12 h-12 mb-2 opacity-50" />
                      <p className="text-sm">No conversations loaded</p>
                      <p className="text-xs mt-4 text-center">Click the Message button on a profile to start a new conversation</p>
                    </div>
                  )}
                </div>
              )}

              {/* Messages View */}
              {selectedThread && (
                <div className="flex-1 flex flex-col">
                  {/* Back button - visible on all screen sizes */}
                  <button
                    onClick={() => setSelectedThread(null)}
                    className="flex items-center gap-2 p-3 text-sm font-medium text-brand-600 dark:text-brand-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-200 dark:border-gray-700"
                  >
                    <span className="text-lg">←</span> Back to conversations
                  </button>

                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.length === 0 ? (
                      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400 text-sm">
                        No messages yet. Start the conversation!
                      </div>
                    ) : (
                      messages.map((message) => {
                        const isOwn = message.sender_id === userId;
                        return (
                          <div
                            key={message.id}
                            className={`flex gap-2 ${isOwn ? 'flex-row-reverse' : 'flex-row'}`}
                          >
                            {!isOwn && (
                              <UserAvatar
                                name={participantMetadata[selectedThread.other_user_id]?.name || message.sender_id}
                                size="small"
                              />
                            )}
                            <div
                              className={`max-w-[75%] rounded-lg p-3 ${
                                isOwn
                                  ? 'bg-brand-500 text-white'
                                  : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                              }`}
                            >
                              <div className={`text-sm break-words prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 ${
                                isOwn
                                  ? 'prose-invert prose-a:text-white prose-a:underline prose-strong:text-white'
                                  : 'dark:prose-invert prose-a:text-brand-600 dark:prose-a:text-brand-400'
                              }`}>
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                  {message.content}
                                </ReactMarkdown>
                              </div>
                              <div
                                className={`text-xs mt-1 flex items-center gap-1 ${
                                  isOwn ? 'text-brand-100' : 'text-gray-500 dark:text-gray-400'
                                }`}
                              >
                                {new Date(message.created_at).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                                {isOwn && message.status === 'read' && ' · Read'}
                                {isOwn && message.status === 'delivered' && ' · Delivered'}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}

                    {/* Typing indicator */}
                    {Array.from(typingUsers).some(id => id !== userId && id === selectedThread.other_user_id) && (
                      <div className="flex gap-2">
                        <UserAvatar
                          name={participantMetadata[selectedThread.other_user_id]?.name || selectedThread.other_user_id}
                          size="small"
                        />
                        <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
                          <div className="flex gap-1">
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                          </div>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </div>

                  {/* Message Input */}
                  <div className="border-t border-gray-200 dark:border-gray-700 p-4">
                    {/* Markdown Toolbar */}
                    <div className="flex items-center gap-1 mb-2 pb-2 border-b border-gray-200 dark:border-gray-700">
                      <button
                        onClick={() => insertMarkdown('**', 'bold')}
                        className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                        title="Bold"
                      >
                        <Bold className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => insertMarkdown('*', 'italic')}
                        className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                        title="Italic"
                      >
                        <Italic className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => insertMarkdown('[]', 'link')}
                        className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                        title="Link"
                      >
                        <LinkIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => insertMarkdown('- ', 'list')}
                        className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                        title="List"
                      >
                        <List className="w-4 h-4" />
                      </button>
                      <div className="flex-1"></div>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {messageInput.length}/{MESSAGE_CONSTANTS.MAX_MESSAGE_LENGTH}
                      </span>
                    </div>

                    {/* Input Field */}
                    <div className="flex items-end gap-2">
                      <textarea
                        ref={textareaRef}
                        value={messageInput}
                        onChange={handleTextareaChange}
                        onKeyPress={handleKeyPress}
                        placeholder={
                          isAuthenticated
                            ? "Type a message..."
                            : "Connecting..."
                        }
                        rows={1}
                        disabled={!isAuthenticated}
                        className="flex-1 px-4 py-2 bg-gray-100 dark:bg-gray-700 border-none rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-brand-500 resize-none disabled:opacity-50"
                      />
                      <button
                        onClick={handleSendMessage}
                        disabled={!messageInput.trim() || !isAuthenticated}
                        className="p-3 bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <Send className="w-5 h-5" />
                      </button>
                    </div>
                    {/* Show error message */}
                    {wsError && (
                      <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-700 dark:text-red-300">
                        {wsError}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Report Modal */}
      {reportModal.isOpen && reportModal.targetId && reportModal.reportType && (
        <ReportModal
          isOpen={reportModal.isOpen}
          onClose={reportModal.closeReportModal}
          reportType={reportModal.reportType}
          targetId={reportModal.targetId}
          targetName={reportModal.targetName || undefined}
        />
      )}

      {/* Messaging Error Modal */}
      <MessageErrorModal
        error={messagingError}
        isOpen={showErrorModal}
        onClose={() => {
          setShowErrorModal(false);
          setMessagingError(null);
        }}
        onRetry={() => {
          // Retry sending the message
          handleSendMessage();
        }}
      />
    </>
  );
}
