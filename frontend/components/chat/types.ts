export type Player = {
  user_id: string | null;
  display_name: string;
  avatar: string;
  can_send?: boolean;
};
export type ChatMessage = {
  id: number;
  mine: boolean;
  body: string;
  created_at: string;
  is_read: boolean | null;
  client_id: string | null;
};
export type Conversation = {
  id: number;
  other: Player;
  online: boolean | null;
  can_send: boolean;
  blocked_by_me: boolean;
  language_filter_enabled: boolean;
  read_receipts_visible: boolean;
  unread_count: number;
  last_message: ChatMessage | null;
  updated_at: string;
};
export type Results<T> = { results: T[]; has_more: boolean };
export type ChatPreferences = {
  who_can_message: "EVERYONE" | "FRIENDS" | "NOBODY";
  show_online_status: boolean;
  send_read_receipts: boolean;
  message_notifications: boolean;
  allow_friend_requests: boolean;
  mature_language_filter: boolean;
};
export type ChatSummary = {
  user_id: string;
  unread_count: number;
  message_notifications: boolean;
};
