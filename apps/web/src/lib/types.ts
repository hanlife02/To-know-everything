export interface BootstrapStatusResponse {
  needs_setup: boolean
  security_ready: boolean
  default_admin_username: string
}

export interface CurrentUser {
  id: string
  username: string
  created_at: number
}

export interface AuthSessionResponse {
  user: CurrentUser
}

export interface DashboardOverviewResponse {
  app_name: string
  user: CurrentUser
  security_ready: boolean
  tracked_accounts: number
  cookie_profiles: number
  model_providers: number
  contents: number
  push_logs: number
}

export interface TrackedAccountRecord {
  id: string
  platform: string
  display_name: string
  account_handle: string
  profile_url: string | null
  notes: string | null
  is_active: boolean
  created_at: number
  updated_at: number
}

export interface CookieProfileRecord {
  id: string
  label: string
  platform: string
  cookie_preview: string
  is_active: boolean
  created_at: number
  updated_at: number
}

export interface ModelProviderRecord {
  id: string
  name: string
  base_url: string
  api_key_preview: string
  summary_model: string | null
  translation_model: string | null
  ocr_model: string | null
  transcription_model: string | null
  understanding_model: string | null
  is_default: boolean
  created_at: number
  updated_at: number
}

export interface BarkConfigRecord {
  id: string
  label: string
  server_url: string
  device_key_preview: string
  is_enabled: boolean
  created_at: number
  updated_at: number
}

export interface OptionalBarkConfigResponse {
  data: BarkConfigRecord | null
}

export interface TelegramConfigRecord {
  id: string
  label: string
  api_base_url: string
  chat_id: string
  bot_token_preview: string
  is_enabled: boolean
  created_at: number
  updated_at: number
}

export interface OptionalTelegramConfigResponse {
  data: TelegramConfigRecord | null
}

export interface SetupPayload {
  username: string
  password: string
}

export interface LoginPayload {
  username: string
  password: string
}

export interface CreateTrackedAccountPayload {
  display_name: string
  account_handle: string
  profile_url?: string
  notes?: string
  is_active?: boolean
}

export interface CreateCookieProfilePayload {
  label: string
  cookie_value: string
  is_active?: boolean
}

export interface CreateModelProviderPayload {
  name: string
  base_url: string
  api_key: string
  summary_model?: string
  translation_model?: string
  ocr_model?: string
  transcription_model?: string
  understanding_model?: string
  is_default?: boolean
}

export interface UpsertBarkConfigPayload {
  label?: string
  server_url?: string
  device_key: string
  is_enabled?: boolean
}

export interface UpsertTelegramConfigPayload {
  label?: string
  api_base_url?: string
  chat_id: string
  bot_token: string
  is_enabled?: boolean
}

export interface DiscoverModelsPayload {
  base_url: string
  api_key: string
}

export interface DiscoverModelsResponse {
  models: string[]
}

export interface ManualSyncReadiness {
  security_ready: boolean
  has_account: boolean
  has_cookie_profile: boolean
  has_model_provider: boolean
  bark_enabled: boolean
  telegram_enabled: boolean
  push_channel_ready: boolean
  collector_status: string
  can_run: boolean
  message: string
}

export interface ManualSyncResponse {
  job_run_id: string
  status: string
  readiness: ManualSyncReadiness
}

export interface JobRunRecord {
  id: string
  job_name: string
  status: string
  started_at: number
  finished_at: number | null
  error_message: string | null
}

export interface TestTelegramPushResponse {
  channel: string
  status: string
  message_preview: string
  delivered_at: number
}

export interface CollectorDiagnosticsPayload {
  target_url: string
  cookie_profile_id?: string
}

export interface CollectorDiagnosticsResponse {
  target_url: string
  final_url: string
  status: number
  content_type: string | null
  title: string | null
  page_type: string
  meta_title: string | null
  meta_description: string | null
  canonical_url: string | null
  canonical_note_id: string | null
  canonical_user_id: string | null
  initial_state_blocks: number
  json_ld_blocks: number
  page_signals: CollectorPageSignals
  title_candidates: string[]
  description_candidates: string[]
  author_candidates: string[]
  marker_hits: string[]
  note_cards: NoteCardCandidate[]
  note_link_candidates: string[]
  user_link_candidates: string[]
  note_id_candidates: string[]
  user_id_candidates: string[]
  note_preview: CollectorNotePreview | null
  profile_preview: CollectorProfilePreview | null
  html_excerpt: string
  cookie_profile_used: string | null
}

export interface NoteCardCandidate {
  url: string
  note_id: string | null
  title_hint: string | null
  description_hint: string | null
  author_hint: string | null
  xsec_token_present: boolean
}

export interface CollectorPageSignals {
  has_initial_state: boolean
  has_json_ld: boolean
  has_note_cards: boolean
  has_xsec_token: boolean
  looks_like_video: boolean
  looks_like_image_gallery: boolean
  auth_wall_detected: boolean
  challenge_detected: boolean
}

export interface CollectorNotePreview {
  note_id: string | null
  title: string | null
  description: string | null
  author: string | null
  publish_time_candidates: string[]
  image_count_hint: number | null
  has_video: boolean
}

export interface CollectorProfilePreview {
  user_id: string | null
  profile_url: string | null
  nickname: string | null
  recent_note_count: number
}

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
  }
}
