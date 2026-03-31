use serde::{Deserialize, Serialize};

use crate::app::error::AppError;

pub async fn send_message(
    api_base_url: &str,
    bot_token: &str,
    chat_id: &str,
    text: &str,
) -> Result<(), AppError> {
    let normalized_base = api_base_url.trim().trim_end_matches('/');
    if normalized_base.is_empty() {
        return Err(AppError::bad_request("Telegram API base URL is required."));
    }
    if bot_token.trim().is_empty() {
        return Err(AppError::bad_request("Telegram bot token is required."));
    }
    if chat_id.trim().is_empty() {
        return Err(AppError::bad_request("Telegram chat ID is required."));
    }
    if text.trim().is_empty() {
        return Err(AppError::bad_request("Telegram message text is required."));
    }

    let endpoint = format!("{normalized_base}/bot{}/sendMessage", bot_token.trim());
    let response = reqwest::Client::new()
        .post(endpoint)
        .header(reqwest::header::USER_AGENT, "tke-local/0.1")
        .json(&SendMessageRequest {
            chat_id: chat_id.trim(),
            text,
        })
        .send()
        .await
        .map_err(AppError::internal)?;

    let status = response.status();
    let body = response.text().await.map_err(AppError::internal)?;
    if !status.is_success() {
        let detail = if body.trim().is_empty() {
            format!("Telegram push failed with status {status}.")
        } else {
            format!("Telegram push failed with status {status}: {body}")
        };
        return Err(AppError::bad_request(detail));
    }

    let payload: TelegramEnvelope = serde_json::from_str(&body).map_err(AppError::internal)?;
    if payload.ok {
        return Ok(());
    }

    Err(AppError::bad_request(
        payload
            .description
            .unwrap_or_else(|| "Telegram returned an unsuccessful response.".to_string()),
    ))
}

#[derive(Debug, Serialize)]
struct SendMessageRequest<'a> {
    chat_id: &'a str,
    text: &'a str,
}

#[derive(Debug, Deserialize)]
struct TelegramEnvelope {
    ok: bool,
    description: Option<String>,
}
