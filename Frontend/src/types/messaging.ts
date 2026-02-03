// ============================================================================
// MESSAGE TYPES - Based on API Documentation
// ============================================================================

export interface Message {
  id: string;
  thread_id: string;
  sender_id: string;
  recipient_id: string;
  content: string; // Decrypted content from server
  status: 'sent' | 'delivered' | 'read';
  created_at: string;
  delivered_at?: string;
  read_at?: string;
}

export interface Thread {
  id: string;
  other_user_id: string;
  last_message_preview?: string;
  last_message_at?: string;
  unread_count: number;
  created_at: string;
  updated_at: string;
}

export interface SendMessageRequest {
  recipient_id: string;
  content: string;
}

export interface SendMessageResponse {
  success: boolean;
  message_id?: string;
  thread_id?: string;
  error?: string;
  code?: string;
}

export interface GetMessagesRequest {
  thread_id: string;
  page?: number;
  per_page?: number;
  mark_as_read?: boolean;
}

export interface GetMessagesResponse {
  messages: Message[];
}

export interface ThreadsResponse {
  threads: Thread[];
  total: number;
  page: number;
  per_page: number;
}

export interface BlockUserRequest {
  user_id: string;
  mute_only?: boolean;
}

export interface BlockUserResponse {
  success: boolean;
  blocked_user_id?: string;
  is_muted?: boolean;
}

export interface CanContactResponse {
  can_contact: boolean;
  reason?: string;
  rate_limit_expires_at?: string;
  is_matched?: boolean;
}

export interface BlockedUser {
  blocked_id: string;
  is_muted: boolean;
}

export interface BlockedUsersResponse {
  blocked_users: BlockedUser[];
  total: number;
}

export interface OnlineStatusResponse {
  user_id: string;
  is_online: boolean;
}

// ============================================================================
// WEBSOCKET MESSAGE TYPES - Based on WebSocket Documentation
// ============================================================================

// Client → Server Messages
export type WSClientMessage =
  | WSAuthMessage
  | WSSendMessageMessage
  | WSTypingIndicatorMessage
  | WSMessageReadMessage
  | WSPingMessage
  | WSGetOnlineStatusMessage
  | WSSubscribeMessage;

export interface WSAuthMessage {
  type: 'auth';
  token: string;
}

export interface WSSendMessageMessage {
  type: 'send_message';
  recipient_id: string;
  content: string;
}

export interface WSTypingIndicatorMessage {
  type: 'typing_indicator' | 'typing';
  recipient_id?: string;
  thread_id?: string;
  is_typing: boolean;
}

export interface WSMessageReadMessage {
  type: 'message_read' | 'read_receipt';
  message_id?: string;
  message_ids?: string[];
  thread_id: string;
  sender_id?: string;
}

export interface WSPingMessage {
  type: 'ping';
}

export interface WSGetOnlineStatusMessage {
  type: 'get_online_status';
  user_ids: string[];
}

export interface WSSubscribeMessage {
  type: 'subscribe';
  thread_id: string;
}

// Server → Client Messages
export type WSServerMessage =
  | WSConnectedMessage
  | WSNewMessageMessage
  | WSMessageSentMessage
  | WSTypingMessage
  | WSMessageReadNotification
  | WSPongMessage
  | WSOnlineStatusMessage
  | WSPresenceMessage
  | WSDeliveredMessage
  | WSSubscribedMessage
  | WSErrorMessage;

export interface WSConnectedMessage {
  type: 'connected';
  message: string;
  user_id: string;
}

export interface WSNewMessageMessage {
  type: 'new_message' | 'message';
  message: Message;
  sender_id: string;
  timestamp: string;
}

export interface WSMessageSentMessage {
  type: 'message_sent';
  message: Message;
  success: boolean;
}

export interface WSTypingMessage {
  type: 'typing_indicator' | 'typing';
  sender_id?: string;
  user_id?: string;
  thread_id?: string;
  is_typing: boolean;
  timestamp?: string;
  at?: string;
}

export interface WSMessageReadNotification {
  type: 'message_read' | 'read_receipt';
  message_id?: string;
  message_ids?: string[];
  thread_id: string;
  reader_id: string;
  read_at?: string;
  timestamp?: string;
}

export interface WSPongMessage {
  type: 'pong';
  timestamp?: string;
  at?: string;
}

export interface WSOnlineStatusMessage {
  type: 'online_status_response';
  statuses: Record<string, boolean>;
  timestamp: string;
}

export interface WSPresenceMessage {
  type: 'presence';
  user_id: string;
  status: 'online' | 'offline';
  at?: string;
  timestamp?: string;
}

export interface WSDeliveredMessage {
  type: 'delivered';
  message_id: string;
  at?: string;
  timestamp?: string;
}

export interface WSSubscribedMessage {
  type: 'subscribed';
  thread_id: string;
}

export interface WSErrorMessage {
  type: 'error';
  error: string;
  code?: string;
}

// ============================================================================
// ERROR CODES
// ============================================================================

export type MessageErrorCode =
  | 'auth_timeout'
  | 'auth_required'
  | 'token_missing'
  | 'auth_failed'
  | 'rate_limit_exceeded'
  | 'content_too_long'
  | 'send_failed'
  | 'message_not_found'
  | 'unauthorized'
  | 'user_blocked';

// ============================================================================
// CONSTANTS
// ============================================================================

export const MESSAGE_CONSTANTS = {
  MAX_MESSAGE_LENGTH: 5000,
  RATE_LIMIT_MESSAGES: 30,
  RATE_LIMIT_WINDOW_SECONDS: 60,
  NEW_CONVERSATION_COOLDOWN_HOURS: 72,
  HEARTBEAT_INTERVAL_MS: 30000,
  AUTH_TIMEOUT_MS: 10000,
} as const;
