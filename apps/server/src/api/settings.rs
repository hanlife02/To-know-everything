use axum::{Json, extract::State};

use crate::{
    api::auth::AuthSession,
    app::{
        error::{AppError, AppResult},
        state::SharedState,
    },
    models::settings::{
        BarkConfigRecord, CookieProfileRecord, CreateCookieProfileRequest,
        CreateModelProviderRequest, CreateTrackedAccountRequest, ModelProviderRecord,
        OptionalBarkConfigResponse, OptionalTelegramConfigResponse, TelegramConfigRecord,
        TrackedAccountRecord, UpsertBarkConfigRequest, UpsertTelegramConfigRequest,
    },
    security::mask_secret,
    services,
};

pub async fn list_accounts(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<Vec<TrackedAccountRecord>>> {
    let records = sqlx::query_as::<_, TrackedAccountRecord>(
        "SELECT id, platform, display_name, account_handle, profile_url, notes, is_active, created_at, updated_at
         FROM tracked_accounts
         ORDER BY updated_at DESC",
    )
    .fetch_all(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(records))
}

pub async fn create_account(
    _auth: AuthSession,
    State(state): State<SharedState>,
    Json(request): Json<CreateTrackedAccountRequest>,
) -> AppResult<Json<TrackedAccountRecord>> {
    let display_name = request.display_name.trim();
    let account_handle = request.account_handle.trim();

    if display_name.is_empty() || account_handle.is_empty() {
        return Err(AppError::bad_request(
            "Display name and account handle are required.",
        ));
    }

    let now = services::unix_timestamp();
    let record = TrackedAccountRecord {
        id: services::random_id(16),
        platform: "xiaohongshu".to_string(),
        display_name: display_name.to_string(),
        account_handle: account_handle.to_string(),
        profile_url: normalize_optional(request.profile_url),
        notes: normalize_optional(request.notes),
        is_active: request.is_active.unwrap_or(true),
        created_at: now,
        updated_at: now,
    };

    sqlx::query(
        "INSERT INTO tracked_accounts (
            id, platform, display_name, account_handle, profile_url, notes, is_active, created_at, updated_at
         ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
    )
    .bind(&record.id)
    .bind(&record.platform)
    .bind(&record.display_name)
    .bind(&record.account_handle)
    .bind(&record.profile_url)
    .bind(&record.notes)
    .bind(record.is_active)
    .bind(record.created_at)
    .bind(record.updated_at)
    .execute(&state.db)
    .await
    .map_err(|err| match err {
        sqlx::Error::Database(database_error)
            if database_error.message().contains("UNIQUE constraint failed") =>
        {
            AppError::conflict("This account is already being tracked.")
        }
        other => AppError::internal(other),
    })?;

    Ok(Json(record))
}

pub async fn list_cookie_profiles(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<Vec<CookieProfileRecord>>> {
    let records = sqlx::query_as::<_, CookieProfileRecord>(
        "SELECT id, label, platform, cookie_preview, is_active, created_at, updated_at
         FROM cookie_profiles
         ORDER BY updated_at DESC",
    )
    .fetch_all(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(records))
}

pub async fn create_cookie_profile(
    _auth: AuthSession,
    State(state): State<SharedState>,
    Json(request): Json<CreateCookieProfileRequest>,
) -> AppResult<Json<CookieProfileRecord>> {
    let crypto = state.crypto.as_ref().ok_or_else(|| {
        AppError::bad_request(
            "Sensitive storage is disabled. Set TKE_MASTER_PASSWORD before saving cookies.",
        )
    })?;

    if request.label.trim().is_empty() || request.cookie_value.trim().is_empty() {
        return Err(AppError::bad_request(
            "Label and cookie value are required.",
        ));
    }

    let now = services::unix_timestamp();
    let encrypted_cookie = crypto.encrypt(&request.cookie_value)?;

    let record = CookieProfileRecord {
        id: services::random_id(16),
        label: request.label.trim().to_string(),
        platform: "xiaohongshu".to_string(),
        cookie_preview: mask_secret(&request.cookie_value),
        is_active: request.is_active.unwrap_or(true),
        created_at: now,
        updated_at: now,
    };

    sqlx::query(
        "INSERT INTO cookie_profiles (
            id, label, platform, encrypted_cookie, cookie_preview, is_active, created_at, updated_at
         ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
    )
    .bind(&record.id)
    .bind(&record.label)
    .bind(&record.platform)
    .bind(&encrypted_cookie)
    .bind(&record.cookie_preview)
    .bind(record.is_active)
    .bind(record.created_at)
    .bind(record.updated_at)
    .execute(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(record))
}

pub async fn list_model_providers(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<Vec<ModelProviderRecord>>> {
    let records = sqlx::query_as::<_, ModelProviderRecord>(
        "SELECT id, name, base_url, api_key_preview, summary_model, translation_model, ocr_model,
                transcription_model, understanding_model, is_default, created_at, updated_at
         FROM model_providers
         ORDER BY is_default DESC, updated_at DESC",
    )
    .fetch_all(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(records))
}

pub async fn create_model_provider(
    _auth: AuthSession,
    State(state): State<SharedState>,
    Json(request): Json<CreateModelProviderRequest>,
) -> AppResult<Json<ModelProviderRecord>> {
    let crypto = state.crypto.as_ref().ok_or_else(|| {
        AppError::bad_request(
            "Sensitive storage is disabled. Set TKE_MASTER_PASSWORD before saving API keys.",
        )
    })?;

    if request.name.trim().is_empty()
        || request.base_url.trim().is_empty()
        || request.api_key.trim().is_empty()
    {
        return Err(AppError::bad_request(
            "Provider name, base URL, and API key are required.",
        ));
    }

    let now = services::unix_timestamp();
    let encrypted_api_key = crypto.encrypt(&request.api_key)?;
    let record = ModelProviderRecord {
        id: services::random_id(16),
        name: request.name.trim().to_string(),
        base_url: request.base_url.trim().to_string(),
        api_key_preview: mask_secret(&request.api_key),
        summary_model: normalize_optional(request.summary_model),
        translation_model: normalize_optional(request.translation_model),
        ocr_model: normalize_optional(request.ocr_model),
        transcription_model: normalize_optional(request.transcription_model),
        understanding_model: normalize_optional(request.understanding_model),
        is_default: request.is_default.unwrap_or(false),
        created_at: now,
        updated_at: now,
    };

    if record.is_default {
        sqlx::query("UPDATE model_providers SET is_default = 0")
            .execute(&state.db)
            .await
            .map_err(AppError::internal)?;
    }

    sqlx::query(
        "INSERT INTO model_providers (
            id, name, base_url, encrypted_api_key, api_key_preview, summary_model, translation_model,
            ocr_model, transcription_model, understanding_model, is_default, created_at, updated_at
         ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13)",
    )
    .bind(&record.id)
    .bind(&record.name)
    .bind(&record.base_url)
    .bind(&encrypted_api_key)
    .bind(&record.api_key_preview)
    .bind(&record.summary_model)
    .bind(&record.translation_model)
    .bind(&record.ocr_model)
    .bind(&record.transcription_model)
    .bind(&record.understanding_model)
    .bind(record.is_default)
    .bind(record.created_at)
    .bind(record.updated_at)
    .execute(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(record))
}

pub async fn get_bark_config(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<OptionalBarkConfigResponse>> {
    let record = sqlx::query_as::<_, BarkConfigRecord>(
        "SELECT id, label, server_url, device_key_preview, is_enabled, created_at, updated_at
         FROM bark_configs
         ORDER BY updated_at DESC
         LIMIT 1",
    )
    .fetch_optional(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(OptionalBarkConfigResponse { data: record }))
}

pub async fn upsert_bark_config(
    _auth: AuthSession,
    State(state): State<SharedState>,
    Json(request): Json<UpsertBarkConfigRequest>,
) -> AppResult<Json<BarkConfigRecord>> {
    let crypto = state.crypto.as_ref().ok_or_else(|| {
        AppError::bad_request(
            "Sensitive storage is disabled. Set TKE_MASTER_PASSWORD before saving Bark credentials.",
        )
    })?;

    if request.device_key.trim().is_empty() {
        return Err(AppError::bad_request("Bark device key is required."));
    }

    let now = services::unix_timestamp();
    let existing_id: Option<String> =
        sqlx::query_scalar("SELECT id FROM bark_configs ORDER BY updated_at DESC LIMIT 1")
            .fetch_optional(&state.db)
            .await
            .map_err(AppError::internal)?;

    let record = BarkConfigRecord {
        id: existing_id
            .clone()
            .unwrap_or_else(|| services::random_id(16)),
        label: request
            .label
            .as_deref()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or("Primary Bark")
            .to_string(),
        server_url: request
            .server_url
            .as_deref()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or("https://api.day.app")
            .to_string(),
        device_key_preview: mask_secret(&request.device_key),
        is_enabled: request.is_enabled.unwrap_or(true),
        created_at: now,
        updated_at: now,
    };

    let encrypted_device_key = crypto.encrypt(&request.device_key)?;

    if existing_id.is_some() {
        sqlx::query(
            "UPDATE bark_configs
             SET label = ?1, server_url = ?2, encrypted_device_key = ?3, device_key_preview = ?4,
                 is_enabled = ?5, updated_at = ?6
             WHERE id = ?7",
        )
        .bind(&record.label)
        .bind(&record.server_url)
        .bind(&encrypted_device_key)
        .bind(&record.device_key_preview)
        .bind(record.is_enabled)
        .bind(record.updated_at)
        .bind(&record.id)
        .execute(&state.db)
        .await
        .map_err(AppError::internal)?;
    } else {
        sqlx::query(
            "INSERT INTO bark_configs (
                id, label, server_url, encrypted_device_key, device_key_preview, is_enabled, created_at, updated_at
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
        )
        .bind(&record.id)
        .bind(&record.label)
        .bind(&record.server_url)
        .bind(&encrypted_device_key)
        .bind(&record.device_key_preview)
        .bind(record.is_enabled)
        .bind(record.created_at)
        .bind(record.updated_at)
        .execute(&state.db)
        .await
        .map_err(AppError::internal)?;
    }

    Ok(Json(record))
}

pub async fn get_telegram_config(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<OptionalTelegramConfigResponse>> {
    let record = sqlx::query_as::<_, TelegramConfigRecord>(
        "SELECT id, label, api_base_url, chat_id, bot_token_preview, is_enabled, created_at, updated_at
         FROM telegram_configs
         ORDER BY updated_at DESC
         LIMIT 1",
    )
    .fetch_optional(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(OptionalTelegramConfigResponse { data: record }))
}

pub async fn upsert_telegram_config(
    _auth: AuthSession,
    State(state): State<SharedState>,
    Json(request): Json<UpsertTelegramConfigRequest>,
) -> AppResult<Json<TelegramConfigRecord>> {
    let crypto = state.crypto.as_ref().ok_or_else(|| {
        AppError::bad_request(
            "Sensitive storage is disabled. Set TKE_MASTER_PASSWORD before saving Telegram credentials.",
        )
    })?;

    if request.chat_id.trim().is_empty() {
        return Err(AppError::bad_request("Telegram chat ID is required."));
    }
    if request.bot_token.trim().is_empty() {
        return Err(AppError::bad_request("Telegram bot token is required."));
    }

    let now = services::unix_timestamp();
    let existing_id: Option<String> =
        sqlx::query_scalar("SELECT id FROM telegram_configs ORDER BY updated_at DESC LIMIT 1")
            .fetch_optional(&state.db)
            .await
            .map_err(AppError::internal)?;

    let record = TelegramConfigRecord {
        id: existing_id
            .clone()
            .unwrap_or_else(|| services::random_id(16)),
        label: request
            .label
            .as_deref()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or("Primary Telegram")
            .to_string(),
        api_base_url: request
            .api_base_url
            .as_deref()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or("https://api.telegram.org")
            .to_string(),
        chat_id: request.chat_id.trim().to_string(),
        bot_token_preview: mask_secret(&request.bot_token),
        is_enabled: request.is_enabled.unwrap_or(true),
        created_at: now,
        updated_at: now,
    };

    let encrypted_bot_token = crypto.encrypt(&request.bot_token)?;

    if existing_id.is_some() {
        sqlx::query(
            "UPDATE telegram_configs
             SET label = ?1, api_base_url = ?2, chat_id = ?3, encrypted_bot_token = ?4,
                 bot_token_preview = ?5, is_enabled = ?6, updated_at = ?7
             WHERE id = ?8",
        )
        .bind(&record.label)
        .bind(&record.api_base_url)
        .bind(&record.chat_id)
        .bind(&encrypted_bot_token)
        .bind(&record.bot_token_preview)
        .bind(record.is_enabled)
        .bind(record.updated_at)
        .bind(&record.id)
        .execute(&state.db)
        .await
        .map_err(AppError::internal)?;
    } else {
        sqlx::query(
            "INSERT INTO telegram_configs (
                id, label, api_base_url, chat_id, encrypted_bot_token, bot_token_preview, is_enabled, created_at, updated_at
             ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)",
        )
        .bind(&record.id)
        .bind(&record.label)
        .bind(&record.api_base_url)
        .bind(&record.chat_id)
        .bind(&encrypted_bot_token)
        .bind(&record.bot_token_preview)
        .bind(record.is_enabled)
        .bind(record.created_at)
        .bind(record.updated_at)
        .execute(&state.db)
        .await
        .map_err(AppError::internal)?;
    }

    Ok(Json(record))
}

fn normalize_optional(value: Option<String>) -> Option<String> {
    value
        .map(|entry| entry.trim().to_string())
        .filter(|entry| !entry.is_empty())
}
