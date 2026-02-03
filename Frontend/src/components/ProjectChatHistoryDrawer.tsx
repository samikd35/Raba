"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  History,
  MessageSquare,
  Calendar,
  Loader2,
  AlertCircle,
  RefreshCw,
  Plus
} from "lucide-react";
import { ChatThread } from "@/types/projectChat";
import { listThreads } from "@/lib/api/projectChatService";

interface ProjectChatHistoryDrawerProps {
  projectId: string;
  trigger?: React.ReactNode;
  onSelectThread: (thread: ChatThread) => void;
  onNewChat: () => void;
  activeThreadId?: string;
}

export default function ProjectChatHistoryDrawer({
  projectId,
  trigger,
  onSelectThread,
  onNewChat,
  activeThreadId
}: ProjectChatHistoryDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { token, isAuthenticated } = useAuthStore();

  // Fetch function
  const fetchThreadsData = useCallback(async () => {
    if (!token || !projectId || !isAuthenticated) return;

    setLoading(true);
    setError(null);

    try {
      const response = await listThreads(projectId, { limit: 50 }, token);

      // Sort threads from most recent to least recent
      const sortedThreads = (response.threads || []).sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setThreads(sortedThreads);
    } catch (err) {
      console.error('Error fetching chat history:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch chat history');
    } finally {
      setLoading(false);
    }
  }, [token, projectId, isAuthenticated]);

  // Fetch threads when drawer opens
  useEffect(() => {
    if (isOpen) {
      fetchThreadsData();
    }
  }, [isOpen, fetchThreadsData]);

  // Handle thread click
  const handleThreadClick = (thread: ChatThread) => {
    onSelectThread(thread);
    setIsOpen(false);
  };

  const handleNewChatClick = () => {
    onNewChat();
    setIsOpen(false);
  };

  // Format date helper
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

      if (diffInHours < 24) {
        if (date.toDateString() === now.toDateString()) {
          return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        return 'Yesterday';
      } else {
        const days = Math.floor(diffInHours / 24);
        if (days < 7) return `${days}d ago`;
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
      }
    } catch {
      return 'Unknown date';
    }
  };

  // Default trigger button
  const defaultTrigger = (
    <Button variant="outline" className="border-brand-300 dark:border-brand-600 text-brand-700 dark:text-brand-200 hover:bg-brand-50 dark:hover:bg-brand-800">
      <History className="h-4 w-4 mr-2" />
      History
    </Button>
  );

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        {trigger || defaultTrigger}
      </SheetTrigger>

      <SheetContent side="right" className="w-[350px] sm:w-[450px] h-full flex flex-col p-0 bg-background dark:bg-gray-900 border-l border-border dark:border-gray-800">
        <div className="flex flex-col h-full">
          <SheetHeader className="p-4 border-b shrink-0 border-border dark:border-gray-800 bg-white dark:bg-gray-900 pr-12">
            <div className="flex items-center justify-between">
              <SheetTitle className="flex items-center gap-2 text-lg font-semibold text-brand-600 dark:text-brand-300">
                <div className="flex items-center gap-2">
                  <History className="h-5 w-5 text-gray-400" />
                  <span>Chat History</span>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={fetchThreadsData}
                  className="h-8 w-8 text-gray-400 hover:text-brand-600 hover:bg-brand-50"
                  disabled={loading}
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                </Button>
              </SheetTitle>
            </div>
          </SheetHeader>

          <div className="p-3">
            <Button
              onClick={handleNewChatClick}
              className="w-full bg-brand-600 hover:bg-brand-700 text-white gap-2"
            >
              <Plus className="h-4 w-4" />
              Start New Chat
            </Button>
          </div>

          <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex-1 overflow-hidden px-2">
              {loading && threads.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 gap-3">
                  <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
                  <p className="text-sm text-muted-foreground">Loading history...</p>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center h-40 space-y-3 px-4 text-center">
                  <AlertCircle className="h-6 w-6 text-red-500" />
                  <p className="text-sm text-red-600">{error}</p>
                  <Button variant="outline" size="sm" onClick={fetchThreadsData}>Try Again</Button>
                </div>
              ) : threads.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-40 space-y-2 text-center text-muted-foreground">
                  <MessageSquare className="h-8 w-8 opacity-20" />
                  <p className="text-sm">No previous chats found</p>
                </div>
              ) : (
                <ScrollArea className="h-full">
                  <div className="space-y-2 pb-4">
                    {threads.map((thread) => (
                      <button
                        key={thread.id}
                        className={`w-full text-left group relative rounded-lg border p-3 transition-all duration-200 
                            ${activeThreadId === thread.id
                            ? 'bg-brand-50 border-brand-200 dark:bg-brand-900/20 dark:border-brand-800'
                            : 'bg-transparent border-transparent hover:bg-gray-50 dark:hover:bg-gray-800/50 hover:border-gray-200 dark:hover:border-gray-700'
                          }`}
                        onClick={() => handleThreadClick(thread)}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`mt-0.5 rounded-full p-1.5 
                              ${activeThreadId === thread.id
                              ? 'bg-brand-100 text-brand-600'
                              : 'bg-gray-100 text-gray-500 group-hover:bg-white group-hover:text-brand-500'
                            }`}>
                            <MessageSquare className="h-3.5 w-3.5" />
                          </div>

                          <div className="flex-1 min-w-0">
                            <h4 className={`text-sm font-medium truncate 
                                ${activeThreadId === thread.id ? 'text-brand-700 dark:text-brand-300' : 'text-gray-700 dark:text-gray-300'}`}>
                              {thread.title || 'Untitled Chat'}
                            </h4>
                            <div className="flex items-center gap-3 mt-1 text-[11px] text-gray-500 dark:text-gray-400">
                              <span className="flex items-center gap-1">
                                <Calendar className="h-3 w-3" />
                                {formatDate(thread.created_at)}
                              </span>
                              {thread.message_count !== null && (
                                <span>{thread.message_count} messages</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}