use serde::{Deserialize, Serialize};

use crate::models::auth::CurrentUser;

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct TrackedAccountRecord {
    pub id: String,
    pub platform: String,
    pub display_name: String,
    pub account_handle: String,
    pub profile_url: Option<String>,
    pub notes: Option<String>,
    pub is_active: bool,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct CreateTrackedAccountRequest {
    pub display_name: String,
    pub account_handle: String,
    pub profile_url: Option<String>,
    pub notes: Option<String>,
    pub is_active: Option<bool>,
}

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct CookieProfileRecord {
    pub id: String,
    pub label: String,
    pub platform: String,
    pub cookie_preview: String,
    pub is_active: bool,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct CreateCookieProfileRequest {
    pub label: String,
    pub cookie_value: String,
    pub is_active: Option<bool>,
}

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct ModelProviderRecord {
    pub id: String,
    pub name: String,
    pub base_url: String,
    pub api_key_preview: String,
    pub summary_model: Option<String>,
    pub translation_model: Option<String>,
    pub ocr_model: Option<String>,
    pub transcription_model: Option<String>,
    pub understanding_model: Option<String>,
    pub is_default: bool,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct CreateModelProviderRequest {
    pub name: String,
    pub base_url: String,
    pub api_key: String,
    pub summary_model: Option<String>,
    pub translation_model: Option<String>,
    pub ocr_model: Option<String>,
    pub transcription_model: Option<String>,
    pub understanding_model: Option<String>,
    pub is_default: Option<bool>,
}

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct BarkConfigRecord {
    pub id: String,
    pub label: String,
    pub server_url: String,
    pub device_key_preview: String,
    pub is_enabled: bool,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct UpsertBarkConfigRequest {
    pub label: Option<String>,
    pub server_url: Option<String>,
    pub device_key: String,
    pub is_enabled: Option<bool>,
}

#[derive(Debug, Serialize)]
pub struct OptionalBarkConfigResponse {
    pub data: Option<BarkConfigRecord>,
}

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct TelegramConfigRecord {
    pub id: String,
    pub label: String,
    pub api_base_url: String,
    pub chat_id: String,
    pub bot_token_preview: String,
    pub is_enabled: bool,
    pub created_at: i64,
    pub updated_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct UpsertTelegramConfigRequest {
    pub label: Option<String>,
    pub api_base_url: Option<String>,
    pub chat_id: String,
    pub bot_token: String,
    pub is_enabled: Option<bool>,
}

#[derive(Debug, Serialize)]
pub struct OptionalTelegramConfigResponse {
    pub data: Option<TelegramConfigRecord>,
}

#[derive(Debug, Serialize)]
pub struct DashboardOverviewResponse {
    pub app_name: String,
    pub user: CurrentUser,
    pub security_ready: bool,
    pub tracked_accounts: i64,
    pub cookie_profiles: i64,
    pub model_providers: i64,
    pub contents: i64,
    pub push_logs: i64,
}
