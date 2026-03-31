use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
pub struct DiscoverModelsRequest {
    pub base_url: String,
    pub api_key: String,
}

#[derive(Debug, Serialize)]
pub struct DiscoverModelsResponse {
    pub models: Vec<String>,
}

#[derive(Debug, Deserialize)]
pub struct CollectorDiagnosticsRequest {
    pub target_url: String,
    pub cookie_profile_id: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct CollectorDiagnosticsResponse {
    pub target_url: String,
    pub final_url: String,
    pub status: u16,
    pub content_type: Option<String>,
    pub title: Option<String>,
    pub page_type: String,
    pub meta_title: Option<String>,
    pub meta_description: Option<String>,
    pub canonical_url: Option<String>,
    pub canonical_note_id: Option<String>,
    pub canonical_user_id: Option<String>,
    pub initial_state_blocks: usize,
    pub json_ld_blocks: usize,
    pub page_signals: CollectorPageSignals,
    pub title_candidates: Vec<String>,
    pub description_candidates: Vec<String>,
    pub author_candidates: Vec<String>,
    pub marker_hits: Vec<String>,
    pub note_cards: Vec<NoteCardCandidate>,
    pub note_link_candidates: Vec<String>,
    pub user_link_candidates: Vec<String>,
    pub note_id_candidates: Vec<String>,
    pub user_id_candidates: Vec<String>,
    pub note_preview: Option<CollectorNotePreview>,
    pub profile_preview: Option<CollectorProfilePreview>,
    pub html_excerpt: String,
    pub cookie_profile_used: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct NoteCardCandidate {
    pub url: String,
    pub note_id: Option<String>,
    pub title_hint: Option<String>,
    pub description_hint: Option<String>,
    pub author_hint: Option<String>,
    pub xsec_token_present: bool,
}

#[derive(Debug, Serialize)]
pub struct CollectorPageSignals {
    pub has_initial_state: bool,
    pub has_json_ld: bool,
    pub has_note_cards: bool,
    pub has_xsec_token: bool,
    pub looks_like_video: bool,
    pub looks_like_image_gallery: bool,
    pub auth_wall_detected: bool,
    pub challenge_detected: bool,
}

#[derive(Debug, Serialize)]
pub struct CollectorNotePreview {
    pub note_id: Option<String>,
    pub title: Option<String>,
    pub description: Option<String>,
    pub author: Option<String>,
    pub publish_time_candidates: Vec<String>,
    pub image_count_hint: Option<usize>,
    pub has_video: bool,
}

#[derive(Debug, Serialize)]
pub struct CollectorProfilePreview {
    pub user_id: Option<String>,
    pub profile_url: Option<String>,
    pub nickname: Option<String>,
    pub recent_note_count: usize,
}

#[derive(Debug, Serialize)]
pub struct ManualSyncReadiness {
    pub security_ready: bool,
    pub has_account: bool,
    pub has_cookie_profile: bool,
    pub has_model_provider: bool,
    pub bark_enabled: bool,
    pub telegram_enabled: bool,
    pub push_channel_ready: bool,
    pub collector_status: &'static str,
    pub can_run: bool,
    pub message: String,
}

#[derive(Debug, Serialize)]
pub struct ManualSyncResponse {
    pub job_run_id: String,
    pub status: String,
    pub readiness: ManualSyncReadiness,
}

#[derive(Debug, Serialize, sqlx::FromRow)]
pub struct JobRunRecord {
    pub id: String,
    pub job_name: String,
    pub status: String,
    pub started_at: i64,
    pub finished_at: Option<i64>,
    pub error_message: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct TestTelegramPushResponse {
    pub channel: &'static str,
    pub status: &'static str,
    pub message_preview: String,
    pub delivered_at: i64,
}
