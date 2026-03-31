use std::{env, path::PathBuf};

#[derive(Clone, Debug)]
pub struct AppConfig {
    pub app_name: String,
    pub server_addr: String,
    pub database_path: PathBuf,
    pub web_origins: Vec<String>,
    pub default_admin_username: String,
    pub session_cookie_name: String,
    pub session_ttl_hours: i64,
    pub master_password: Option<String>,
}

impl AppConfig {
    pub fn from_env() -> Result<Self, String> {
        let app_name = env_or_default("TKE_APP_NAME", "To Know Everything");
        let server_addr = env_or_default("TKE_SERVER_ADDR", "127.0.0.1:8787");
        let database_path = PathBuf::from(env_or_default("TKE_DATABASE_PATH", "./data/app.db"));
        let default_admin_username = env_or_default("TKE_DEFAULT_ADMIN_USERNAME", "admin");
        let session_cookie_name = env_or_default("TKE_SESSION_COOKIE_NAME", "tke_session");
        let session_ttl_hours = env::var("TKE_SESSION_TTL_HOURS")
            .ok()
            .map(|value| {
                value
                    .parse::<i64>()
                    .map_err(|_| "TKE_SESSION_TTL_HOURS must be an integer".to_string())
            })
            .transpose()?
            .unwrap_or(24 * 30);
        let web_origins = env::var("TKE_WEB_ORIGINS")
            .unwrap_or_else(|_| "http://127.0.0.1:5173,http://localhost:5173".to_string())
            .split(',')
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(ToString::to_string)
            .collect::<Vec<_>>();
        let master_password = env::var("TKE_MASTER_PASSWORD")
            .ok()
            .map(|value| value.trim().to_string())
            .filter(|value| !value.is_empty());

        Ok(Self {
            app_name,
            server_addr,
            database_path,
            web_origins,
            default_admin_username,
            session_cookie_name,
            session_ttl_hours,
            master_password,
        })
    }

    pub fn database_url(&self) -> String {
        let normalized_path = self.database_path.to_string_lossy().replace('\\', "/");
        format!("sqlite://{normalized_path}")
    }

    pub fn session_ttl_seconds(&self) -> i64 {
        self.session_ttl_hours * 60 * 60
    }
}

fn env_or_default(name: &str, default: &str) -> String {
    env::var(name)
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .unwrap_or_else(|| default.to_string())
}
