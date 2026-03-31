use axum::{
    Json,
    extract::{FromRequestParts, State},
    http::{
        HeaderMap,
        header::{COOKIE, SET_COOKIE},
        request::Parts,
    },
    response::AppendHeaders,
};
use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};
use sha2::{Digest, Sha256};

use crate::{
    app::{
        error::{AppError, AppResult},
        state::SharedState,
    },
    models::auth::{
        AuthSessionResponse, BootstrapStatusResponse, CurrentUser, LoginRequest, SetupRequest,
    },
    security::password,
    services,
};

pub async fn bootstrap_status(
    State(state): State<SharedState>,
) -> AppResult<Json<BootstrapStatusResponse>> {
    let user_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM users")
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)?;

    Ok(Json(BootstrapStatusResponse {
        needs_setup: user_count == 0,
        security_ready: state.crypto.is_some(),
        default_admin_username: state.config.default_admin_username.clone(),
    }))
}

pub async fn setup(
    State(state): State<SharedState>,
    Json(request): Json<SetupRequest>,
) -> AppResult<(
    AppendHeaders<[(axum::http::header::HeaderName, String); 1]>,
    Json<AuthSessionResponse>,
)> {
    validate_credentials(&request.username, &request.password)?;

    let existing_user_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM users")
        .fetch_one(&state.db)
        .await
        .map_err(AppError::internal)?;

    if existing_user_count > 0 {
        return Err(AppError::conflict(
            "The local admin account has already been created.",
        ));
    }

    let user_id = services::random_id(18);
    let now = services::unix_timestamp();
    let password_hash = password::hash_password(&request.password)?;
    let user = CurrentUser {
        id: user_id.clone(),
        username: request.username.trim().to_string(),
        created_at: now,
    };
    let (session_id, session_token, session_hash) = generate_session_material();

    let mut transaction = state.db.begin().await.map_err(AppError::internal)?;

    sqlx::query(
        "INSERT INTO users (id, username, password_hash, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5)",
    )
    .bind(&user.id)
    .bind(&user.username)
    .bind(&password_hash)
    .bind(now)
    .bind(now)
    .execute(&mut *transaction)
    .await
    .map_err(AppError::internal)?;

    sqlx::query(
        "INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at, last_seen_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
    )
    .bind(&session_id)
    .bind(&user.id)
    .bind(&session_hash)
    .bind(now + state.config.session_ttl_seconds())
    .bind(now)
    .bind(now)
    .execute(&mut *transaction)
    .await
    .map_err(AppError::internal)?;

    transaction.commit().await.map_err(AppError::internal)?;

    let cookie = build_session_cookie(
        &state.config.session_cookie_name,
        &session_token,
        state.config.session_ttl_seconds(),
    );

    Ok((
        AppendHeaders([(SET_COOKIE, cookie)]),
        Json(AuthSessionResponse { user }),
    ))
}

pub async fn login(
    State(state): State<SharedState>,
    Json(request): Json<LoginRequest>,
) -> AppResult<(
    AppendHeaders<[(axum::http::header::HeaderName, String); 1]>,
    Json<AuthSessionResponse>,
)> {
    validate_credentials(&request.username, &request.password)?;

    let row = sqlx::query_as::<_, UserLoginRow>(
        "SELECT id, username, password_hash, created_at FROM users WHERE username = ?1",
    )
    .bind(request.username.trim())
    .fetch_optional(&state.db)
    .await
    .map_err(AppError::internal)?;

    let row = row.ok_or_else(|| AppError::unauthorized("Invalid username or password."))?;
    if !password::verify_password(&row.password_hash, &request.password)? {
        return Err(AppError::unauthorized("Invalid username or password."));
    }

    let now = services::unix_timestamp();
    let (session_id, session_token, session_hash) = generate_session_material();

    sqlx::query(
        "INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at, last_seen_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
    )
    .bind(&session_id)
    .bind(&row.id)
    .bind(&session_hash)
    .bind(now + state.config.session_ttl_seconds())
    .bind(now)
    .bind(now)
    .execute(&state.db)
    .await
    .map_err(AppError::internal)?;

    let cookie = build_session_cookie(
        &state.config.session_cookie_name,
        &session_token,
        state.config.session_ttl_seconds(),
    );

    Ok((
        AppendHeaders([(SET_COOKIE, cookie)]),
        Json(AuthSessionResponse {
            user: CurrentUser {
                id: row.id,
                username: row.username,
                created_at: row.created_at,
            },
        }),
    ))
}

pub async fn logout(
    State(state): State<SharedState>,
    headers: HeaderMap,
) -> AppResult<AppendHeaders<[(axum::http::header::HeaderName, String); 1]>> {
    if let Some(token) = read_cookie(&headers, &state.config.session_cookie_name) {
        sqlx::query("DELETE FROM sessions WHERE token_hash = ?1")
            .bind(hash_token(&token))
            .execute(&state.db)
            .await
            .map_err(AppError::internal)?;
    }

    Ok(AppendHeaders([(
        SET_COOKIE,
        clear_session_cookie(&state.config.session_cookie_name),
    )]))
}

pub async fn me(auth: AuthSession) -> Json<AuthSessionResponse> {
    Json(AuthSessionResponse { user: auth.user })
}

pub struct AuthSession {
    pub user: CurrentUser,
}

impl FromRequestParts<SharedState> for AuthSession {
    type Rejection = AppError;

    async fn from_request_parts(parts: &mut Parts, state: &SharedState) -> AppResult<Self> {
        let token = read_cookie(&parts.headers, &state.config.session_cookie_name)
            .ok_or_else(|| AppError::unauthorized("Authentication required."))?;
        let now = services::unix_timestamp();
        let token_hash = hash_token(&token);

        let user = sqlx::query_as::<_, CurrentUser>(
            "SELECT users.id, users.username, users.created_at
             FROM sessions
             INNER JOIN users ON users.id = sessions.user_id
             WHERE sessions.token_hash = ?1 AND sessions.expires_at > ?2",
        )
        .bind(&token_hash)
        .bind(now)
        .fetch_optional(&state.db)
        .await
        .map_err(AppError::internal)?
        .ok_or_else(|| AppError::unauthorized("Authentication required."))?;

        sqlx::query("UPDATE sessions SET last_seen_at = ?1 WHERE token_hash = ?2")
            .bind(now)
            .bind(&token_hash)
            .execute(&state.db)
            .await
            .map_err(AppError::internal)?;

        Ok(Self { user })
    }
}

#[derive(Debug, sqlx::FromRow)]
struct UserLoginRow {
    id: String,
    username: String,
    password_hash: String,
    created_at: i64,
}

fn validate_credentials(username: &str, password: &str) -> AppResult<()> {
    if username.trim().len() < 3 {
        return Err(AppError::bad_request(
            "Username must be at least 3 characters long.",
        ));
    }

    if password.len() < 10 {
        return Err(AppError::bad_request(
            "Password must be at least 10 characters long.",
        ));
    }

    Ok(())
}

fn generate_session_material() -> (String, String, String) {
    let session_id = services::random_id(18);
    let session_token = services::random_token(32);
    let session_hash = hash_token(&session_token);
    (session_id, session_token, session_hash)
}

fn hash_token(token: &str) -> String {
    let digest = Sha256::digest(token.as_bytes());
    URL_SAFE_NO_PAD.encode(digest)
}

fn build_session_cookie(name: &str, value: &str, max_age_seconds: i64) -> String {
    format!("{name}={value}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age_seconds}")
}

fn clear_session_cookie(name: &str) -> String {
    format!("{name}=deleted; Path=/; HttpOnly; SameSite=Strict; Max-Age=0")
}

fn read_cookie(headers: &HeaderMap, cookie_name: &str) -> Option<String> {
    let cookie_header = headers.get(COOKIE)?.to_str().ok()?;
    cookie_header.split(';').find_map(|entry| {
        let (name, value) = entry.trim().split_once('=')?;
        if name == cookie_name {
            Some(value.to_string())
        } else {
            None
        }
    })
}
