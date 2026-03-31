use axum::{Json, extract::State};

use crate::{
    api::auth::AuthSession,
    app::{
        error::{AppError, AppResult},
        state::SharedState,
    },
    collectors::XIAOHONGSHU_COLLECTOR_STATUS,
    models::tasks::{
        CollectorDiagnosticsRequest, CollectorDiagnosticsResponse, DiscoverModelsRequest,
        DiscoverModelsResponse, JobRunRecord, ManualSyncReadiness, ManualSyncResponse,
        TestTelegramPushResponse,
    },
    services,
};

pub async fn discover_models(
    _auth: AuthSession,
    Json(request): Json<DiscoverModelsRequest>,
) -> AppResult<Json<DiscoverModelsResponse>> {
    let models = services::openai::discover_models(&request.base_url, &request.api_key).await?;
    Ok(Json(DiscoverModelsResponse { models }))
}

pub async fn collector_diagnostics(
    _auth: AuthSession,
    State(state): State<SharedState>,
    Json(request): Json<CollectorDiagnosticsRequest>,
) -> AppResult<Json<CollectorDiagnosticsResponse>> {
    let cookie_profile = if let Some(cookie_profile_id) = request.cookie_profile_id.as_deref() {
        let row = sqlx::query_as::<_, CookieProfileSecretRow>(
            "SELECT label, cookie_preview, encrypted_cookie
             FROM cookie_profiles
             WHERE id = ?1",
        )
        .bind(cookie_profile_id)
        .fetch_optional(&state.db)
        .await
        .map_err(AppError::internal)?
        .ok_or_else(|| AppError::bad_request("The selected cookie profile does not exist."))?;

        let crypto = state.crypto.as_ref().ok_or_else(|| {
            AppError::bad_request(
                "Sensitive storage is disabled. Set TKE_MASTER_PASSWORD before using stored cookies.",
            )
        })?;

        Some((
            format!("{} ({})", row.label, row.cookie_preview),
            crypto.decrypt(&row.encrypted_cookie)?,
        ))
    } else {
        None
    };

    let probe = services::xiaohongshu::probe_public_page(
        &request.target_url,
        cookie_profile.as_ref().map(|(_, cookie)| cookie.as_str()),
    )
    .await?;

    Ok(Json(CollectorDiagnosticsResponse {
        target_url: request.target_url.trim().to_string(),
        final_url: probe.final_url,
        status: probe.status,
        content_type: probe.content_type,
        title: probe.title,
        page_type: probe.page_type,
        meta_title: probe.meta_title,
        meta_description: probe.meta_description,
        canonical_url: probe.canonical_url,
        canonical_note_id: probe.canonical_note_id,
        canonical_user_id: probe.canonical_user_id,
        initial_state_blocks: probe.initial_state_blocks,
        json_ld_blocks: probe.json_ld_blocks,
        page_signals: probe.page_signals,
        title_candidates: probe.title_candidates,
        description_candidates: probe.description_candidates,
        author_candidates: probe.author_candidates,
        marker_hits: probe.marker_hits,
        note_cards: probe.note_cards,
        note_link_candidates: probe.note_link_candidates,
        user_link_candidates: probe.user_link_candidates,
        note_id_candidates: probe.note_id_candidates,
        user_id_candidates: probe.user_id_candidates,
        note_preview: probe.note_preview,
        profile_preview: probe.profile_preview,
        html_excerpt: probe.html_excerpt,
        cookie_profile_used: cookie_profile.map(|(label, _)| label),
    }))
}

pub async fn manual_sync(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<ManualSyncResponse>> {
    let has_account = count_rows(&state, "tracked_accounts").await? > 0;
    let has_cookie_profile = count_rows(&state, "cookie_profiles").await? > 0;
    let has_model_provider = count_rows(&state, "model_providers").await? > 0;
    let bark_enabled: i64 =
        sqlx::query_scalar("SELECT COUNT(*) FROM bark_configs WHERE is_enabled = 1")
            .fetch_one(&state.db)
            .await
            .map_err(AppError::internal)?;
    let telegram_enabled: i64 =
        sqlx::query_scalar("SELECT COUNT(*) FROM telegram_configs WHERE is_enabled = 1")
            .fetch_one(&state.db)
            .await
            .map_err(AppError::internal)?;

    let bark_enabled = bark_enabled > 0;
    let telegram_enabled = telegram_enabled > 0;
    let push_channel_ready = bark_enabled || telegram_enabled;
    let security_ready = state.crypto.is_some();
    let collector_ready = XIAOHONGSHU_COLLECTOR_STATUS == "ready";
    let can_run = security_ready
        && has_account
        && has_cookie_profile
        && has_model_provider
        && push_channel_ready
        && collector_ready;

    let readiness = ManualSyncReadiness {
        security_ready,
        has_account,
        has_cookie_profile,
        has_model_provider,
        bark_enabled,
        telegram_enabled,
        push_channel_ready,
        collector_status: XIAOHONGSHU_COLLECTOR_STATUS,
        can_run,
        message: if can_run {
            "Manual sync is ready to be executed.".to_string()
        } else if !collector_ready {
            format!(
                "The Xiaohongshu collector is currently in {status} mode, so manual sync remains blocked until the full incremental pipeline is implemented.",
                status = XIAOHONGSHU_COLLECTOR_STATUS
            )
        } else {
            "Manual sync prerequisites are incomplete. Fill in the missing local configuration first."
                .to_string()
        },
    };

    let job_id = ensure_manual_job(&state).await?;
    let run_id = services::random_id(16);
    let now = services::unix_timestamp();
    let status = if can_run { "queued" } else { "blocked" };
    let error_message = (!can_run).then(|| readiness.message.clone());

    sqlx::query(
        "INSERT INTO job_runs (id, job_id, status, started_at, finished_at, error_message)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
    )
    .bind(&run_id)
    .bind(&job_id)
    .bind(status)
    .bind(now)
    .bind(now)
    .bind(error_message)
    .execute(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(ManualSyncResponse {
        job_run_id: run_id,
        status: status.to_string(),
        readiness,
    }))
}

pub async fn list_runs(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<Vec<JobRunRecord>>> {
    let records = sqlx::query_as::<_, JobRunRecord>(
        "SELECT job_runs.id, jobs.name AS job_name, job_runs.status, job_runs.started_at,
                job_runs.finished_at, job_runs.error_message
         FROM job_runs
         INNER JOIN jobs ON jobs.id = job_runs.job_id
         ORDER BY job_runs.started_at DESC
         LIMIT 20",
    )
    .fetch_all(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(Json(records))
}

pub async fn test_telegram_push(
    _auth: AuthSession,
    State(state): State<SharedState>,
) -> AppResult<Json<TestTelegramPushResponse>> {
    let row = sqlx::query_as::<_, TelegramConfigSecretRow>(
        "SELECT label, api_base_url, chat_id, encrypted_bot_token
         FROM telegram_configs
         ORDER BY updated_at DESC
         LIMIT 1",
    )
    .fetch_optional(&state.db)
    .await
    .map_err(AppError::internal)?
    .ok_or_else(|| AppError::bad_request("Save a Telegram configuration before sending a test message."))?;

    let crypto = state.crypto.as_ref().ok_or_else(|| {
        AppError::bad_request(
            "Sensitive storage is disabled. Set TKE_MASTER_PASSWORD before using stored Telegram credentials.",
        )
    })?;

    let bot_token = crypto.decrypt(&row.encrypted_bot_token)?;
    let now = services::unix_timestamp();
    let message = format!(
        "To Know Everything\nTelegram test push\nConfig: {}\nTime: {}",
        row.label, now
    );
    let message_preview = preview_message(&message);

    if let Err(error) = services::telegram::send_message(
        &row.api_base_url,
        &bot_token,
        &row.chat_id,
        &message,
    )
    .await
    {
        insert_push_log(&state, "telegram", "failed", &message_preview, Some(&error.to_string()), now)
            .await?;
        return Err(error);
    }

    insert_push_log(&state, "telegram", "sent", &message_preview, None, now).await?;

    Ok(Json(TestTelegramPushResponse {
        channel: "telegram",
        status: "sent",
        message_preview,
        delivered_at: now,
    }))
}

async fn count_rows(state: &SharedState, table_name: &str) -> AppResult<i64> {
    let query = format!("SELECT COUNT(*) FROM {table_name}");
    sqlx::query_scalar::<_, i64>(&query)
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)
}

async fn ensure_manual_job(state: &SharedState) -> AppResult<String> {
    if let Some(existing_id) =
        sqlx::query_scalar::<_, String>("SELECT id FROM jobs WHERE name = 'manual-sync' LIMIT 1")
            .fetch_optional(&state.db)
            .await
            .map_err(AppError::internal)?
    {
        return Ok(existing_id);
    }

    let job_id = services::random_id(16);
    let now = services::unix_timestamp();

    sqlx::query(
        "INSERT INTO jobs (id, name, cron_expression, is_enabled, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
    )
    .bind(&job_id)
    .bind("manual-sync")
    .bind(Option::<String>::None)
    .bind(true)
    .bind(now)
    .bind(now)
    .execute(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(job_id)
}

async fn insert_push_log(
    state: &SharedState,
    channel: &str,
    status: &str,
    message_preview: &str,
    error_message: Option<&str>,
    pushed_at: i64,
) -> AppResult<()> {
    sqlx::query(
        "INSERT INTO push_logs (id, content_row_id, channel, status, message_preview, error_message, pushed_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
    )
    .bind(services::random_id(16))
    .bind(Option::<String>::None)
    .bind(channel)
    .bind(status)
    .bind(message_preview)
    .bind(error_message)
    .bind(pushed_at)
    .execute(&state.db)
    .await
    .map_err(AppError::internal)?;

    Ok(())
}

fn preview_message(value: &str) -> String {
    const LIMIT: usize = 120;

    let preview = value.chars().take(LIMIT).collect::<String>();
    if value.chars().count() > LIMIT {
        format!("{preview}...")
    } else {
        preview
    }
}

#[derive(Debug, sqlx::FromRow)]
struct CookieProfileSecretRow {
    label: String,
    cookie_preview: String,
    encrypted_cookie: String,
}

#[derive(Debug, sqlx::FromRow)]
struct TelegramConfigSecretRow {
    label: String,
    api_base_url: String,
    chat_id: String,
    encrypted_bot_token: String,
}
