export interface TokenResponse {
  access_token: string;
  token_type: string;
  admin_name: string;
  admin_phone: string;
}

export interface AdminUser {
  username: string;
  name: string;
  phone: string;
  token: string;
}

export interface ToolCallData {
  id: number;
  tool_name: string;
  tool_input: Record<string, unknown>;
  tool_result: Record<string, unknown> | null;
  duration_ms: number | null;
  status: string;
  created_at: string;
}

export interface MessageData {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  message_type: string;
  created_at: string;
  tool_calls: ToolCallData[];
}

export interface ConversationListItem {
  id: number;
  phone: string;
  contact_type: string | null;
  patient_name: string | null;
  status: string;
  last_message_preview: string | null;
  last_message_at: string | null;
  message_count: number;
}

export interface ConversationDetail {
  id: number;
  phone: string;
  contact_type: string | null;
  patient_id: string | null;
  patient_name: string | null;
  lead_id: string | null;
  is_active: boolean;
  status: string;
  labels: string[];
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SimulateResponse {
  response_text: string | null;
  conversation_id: number;
  tool_calls: ToolCallData[];
}

export interface WsEvent {
  type: "new_message" | "tool_call" | "state_changed" | "pong";
  conversation_id?: number;
  message?: {
    id: number;
    role: string;
    content: string;
    created_at: string;
  };
  tool_call?: ToolCallData;
  status?: string;
}
