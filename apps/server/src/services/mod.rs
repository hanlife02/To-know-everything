use base64::{Engine as _, engine::general_purpose::URL_SAFE_NO_PAD};
use std::time::{SystemTime, UNIX_EPOCH};

pub mod openai;
pub mod telegram;
pub mod xiaohongshu;

pub fn unix_timestamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs() as i64)
        .unwrap_or_default()
}

pub fn random_id(byte_len: usize) -> String {
    random_token(byte_len)
}

pub fn random_token(byte_len: usize) -> String {
    let mut bytes = vec![0_u8; byte_len];
    rand::fill(bytes.as_mut_slice());
    URL_SAFE_NO_PAD.encode(bytes)
}
