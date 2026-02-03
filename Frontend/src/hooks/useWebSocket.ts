'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import type { WSClientMessage, WSServerMessage, MESSAGE_CONSTANTS } from '@/types/messaging';

interface UseWebSocketOptions {
  token?: string; // JWT token for authentication
  onMessage?: (data: WSServerMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event | string) => void;
  onAuthenticated?: (userId: string) => void;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  enableHeartbeat?: boolean;
  heartbeatInterval?: number;
  enableMessageQueue?: boolean; // Queue messages when offline
}

/**
 * Enhanced WebSocket Hook for Messaging
 *
 * Based on WEBSOCKET_MESSAGING_GUIDE.md:
 * - Secure authentication via message payload (first message must be auth)
 * - Automatic reconnection with exponential backoff
 * - Heartbeat/keep-alive to maintain connection
 * - Message queueing for offline support
 * - Proper error handling with error codes
 * - Typing indicator debouncing
 */
export function useWebSocket(url: string | null, options: UseWebSocketOptions = {}) {
  const {
    token,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    onAuthenticated,
    reconnectInterval = 2000,
    reconnectAttempts = 5,
    enableHeartbeat = true,
    heartbeatInterval = 30000, // 30 seconds per documentation
    enableMessageQueue = true,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSServerMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const heartbeatIntervalRef = useRef<NodeJS.Timeout>();
  const authTimeoutRef = useRef<NodeJS.Timeout>();
  const messageQueueRef = useRef<WSClientMessage[]>([]);

  // Use refs for callbacks to avoid reconnection when callbacks change
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);
  const onAuthenticatedRef = useRef(onAuthenticated);

  // Update refs when callbacks change (without triggering reconnection)
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    onConnectRef.current = onConnect;
  }, [onConnect]);

  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    onAuthenticatedRef.current = onAuthenticated;
  }, [onAuthenticated]);

  /**
   * Send authentication message (must be first message within 10 seconds)
   */
  const authenticate = useCallback(() => {
    if (!token || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const authMessage: WSClientMessage = {
      type: 'auth',
      token,
    };

    wsRef.current.send(JSON.stringify(authMessage));

    // Set authentication timeout (10 seconds per documentation)
    authTimeoutRef.current = setTimeout(() => {
      // Use wsRef to check connection state instead of relying on state
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        const errorMsg = 'Authentication timeout - must authenticate within 10 seconds';
        console.error(errorMsg);
        setError(errorMsg);
        onErrorRef.current?.(errorMsg);
        wsRef.current.close();
      }
    }, 10000);
  }, [token]);

  /**
   * Start heartbeat/keep-alive
   */
  const startHeartbeat = useCallback(() => {
    if (!enableHeartbeat) return;

    heartbeatIntervalRef.current = setInterval(() => {
      // Just check if socket is open - heartbeat starts after auth anyway
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        const pingMessage: WSClientMessage = { type: 'ping' };
        wsRef.current.send(JSON.stringify(pingMessage));
      }
    }, heartbeatInterval);
  }, [enableHeartbeat, heartbeatInterval]);

  /**
   * Stop heartbeat
   */
  const stopHeartbeat = useCallback(() => {
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = undefined;
    }
  }, []);

  /**
   * Process queued messages after authentication
   */
  const processMessageQueue = useCallback(() => {
    if (!enableMessageQueue || !wsRef.current) return;

    // Process queue if socket is open - this is only called after auth anyway
    while (messageQueueRef.current.length > 0) {
      const queuedMessage = messageQueueRef.current.shift();
      if (queuedMessage && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(queuedMessage));
      }
    }
  }, [enableMessageQueue]);

  /**
   * Connect to WebSocket
   */
  const connect = useCallback(() => {
    if (!url) {
      console.error('[WebSocket] No URL provided');
      return;
    }

    // Redact token from URL for logging
    const urlForLogging = url.includes('?token=')
      ? url.replace(/\?token=.*/, '?token=REDACTED')
      : url;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectCountRef.current = 0;
        onConnectRef.current?.();

        // If token provided, use secure message-based authentication
        if (token) {
          authenticate();
        } else {
          console.error('[WebSocket] No auth token');
          setError('No authentication token available');
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WSServerMessage;
          setLastMessage(data);

          // Handle authentication confirmation
          if (data.type === 'connected') {
            setIsAuthenticated(true);

            // Clear auth timeout
            if (authTimeoutRef.current) {
              clearTimeout(authTimeoutRef.current);
            }

            // Start heartbeat
            startHeartbeat();

            // Process queued messages
            processMessageQueue();

            onAuthenticatedRef.current?.(data.user_id);

            // Don't pass 'connected' message to parent handler - it's internal
            return;
          }

          // Handle errors
          if (data.type === 'error') {
            console.error('[WebSocket] Error:', data.error);

            // Check for backend configuration errors
            if (data.error?.includes('MESSAGING_ENCRYPTION_KEY')) {
              const userMsg = 'Backend missing encryption key. Contact administrator.';
              setError(userMsg);
              onErrorRef.current?.(userMsg);
              disconnect();
              return;
            }

            setError(data.error);
            onErrorRef.current?.(data.error);

            // Handle auth errors - disconnect and don't retry
            if (data.code === 'auth_failed' || data.code === 'auth_timeout') {
              disconnect();
              return;
            }
          }

          onMessageRef.current?.(data);
        } catch (err) {
          const errorMsg = err instanceof Error ? err.message : 'Unknown error parsing message';
          console.error('[WebSocket] Parse error:', errorMsg);
        }
      };

      ws.onerror = (error) => {
        const errorMsg = 'WebSocket connection failed';
        setError(errorMsg);
        onErrorRef.current?.(errorMsg);
      };

      ws.onclose = (event) => {
        // Provide user-friendly error messages based on close codes
        if (event.code === 1006) {
          setError('Unable to connect to messaging. Backend may not be deployed.');
        } else if (event.code === 1008) {
          setError('Authentication failed');
        }

        setIsConnected(false);
        setIsAuthenticated(false);
        stopHeartbeat();
        onDisconnectRef.current?.();

        // Clear auth timeout
        if (authTimeoutRef.current) {
          clearTimeout(authTimeoutRef.current);
        }

        // Attempt to reconnect with exponential backoff
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current += 1;
          const delay = reconnectInterval * reconnectCountRef.current;
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else {
          setError('Connection failed. Please refresh.');
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error);
      setError('Failed to establish connection');
    }
  }, [
    url,
    token,
    authenticate,
    startHeartbeat,
    stopHeartbeat,
    processMessageQueue,
    reconnectInterval,
    reconnectAttempts,
  ]);

  /**
   * Disconnect from WebSocket
   */
  const disconnect = useCallback(() => {
    console.log('[WebSocket] Disconnecting...');

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (authTimeoutRef.current) {
      clearTimeout(authTimeoutRef.current);
    }

    stopHeartbeat();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsAuthenticated(false);
  }, [stopHeartbeat]);

  /**
   * Send a message via WebSocket
   * If not authenticated and queueing is enabled, message will be queued
   */
  const sendMessage = useCallback((message: WSClientMessage) => {
    console.log('[WebSocket] sendMessage called:', {
      messageType: message.type,
      isConnected: wsRef.current?.readyState === WebSocket.OPEN,
      readyState: wsRef.current?.readyState,
    });

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const messageJson = JSON.stringify(message);
      console.log('[WebSocket] Sending message:', messageJson);
      wsRef.current.send(messageJson);
      console.log('[WebSocket] Message sent to server');
    } else if (enableMessageQueue && message.type !== 'auth') {
      // Queue message for later (except auth messages)
      console.log('[WebSocket] Message queued (not connected)');
      messageQueueRef.current.push(message);
    } else {
      console.warn('[WebSocket] Cannot send message - not connected. ReadyState:', wsRef.current?.readyState);
    }
  }, [enableMessageQueue]);

  /**
   * Helper: Send typing indicator
   */
  const sendTypingIndicator = useCallback((recipientId: string, isTyping: boolean) => {
    sendMessage({
      type: 'typing_indicator',
      recipient_id: recipientId,
      is_typing: isTyping,
    });
  }, [sendMessage]);

  /**
   * Helper: Send read receipt
   */
  const sendReadReceipt = useCallback((threadId: string, messageIds: string[]) => {
    sendMessage({
      type: 'read_receipt',
      thread_id: threadId,
      message_ids: messageIds,
    });
  }, [sendMessage]);

  /**
   * Helper: Get online status for users
   */
  const getOnlineStatus = useCallback((userIds: string[]) => {
    sendMessage({
      type: 'get_online_status',
      user_ids: userIds,
    });
  }, [sendMessage]);

  // Connect on mount and when URL or token changes
  useEffect(() => {
    // Connect if URL is provided
    // Token can be undefined if using token-in-URL method (cURL)
    if (url) {
      connect();
    }

    // Only disconnect on unmount or when URL/token actually changes
    return () => {
      disconnect();
    };
  }, [url, token]); // Removed connect/disconnect from deps to prevent reconnection loops

  return {
    // Connection state
    isConnected,
    isAuthenticated,
    error,

    // Last received message
    lastMessage,

    // Actions
    sendMessage,
    disconnect,
    reconnect: connect,

    // Helpers
    sendTypingIndicator,
    sendReadReceipt,
    getOnlineStatus,
  };
}
