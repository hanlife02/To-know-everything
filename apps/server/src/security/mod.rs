pub mod crypto;
pub mod password;

pub fn mask_secret(value: &str) -> String {
    let trimmed = value.trim();
    let char_count = trimmed.chars().count();

    if char_count <= 8 {
        return "********".to_string();
    }

    let prefix = trimmed.chars().take(4).collect::<String>();
    let suffix = trimmed
        .chars()
        .rev()
        .take(4)
        .collect::<String>()
        .chars()
        .rev()
        .collect::<String>();

    format!("{prefix}...{suffix}")
}
