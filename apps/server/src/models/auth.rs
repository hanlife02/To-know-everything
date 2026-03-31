use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize)]
pub struct BootstrapStatusResponse {
    pub needs_setup: bool,
    pub security_ready: bool,
    pub default_admin_username: String,
}

#[derive(Debug, Deserialize)]
pub struct SetupRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Clone, Serialize, sqlx::FromRow)]
pub struct CurrentUser {
    pub id: String,
    pub username: String,
    pub created_at: i64,
}

#[derive(Debug, Serialize)]
pub struct AuthSessionResponse {
    pub user: CurrentUser,
}
