use reqwest::header::{
    ACCEPT, ACCEPT_LANGUAGE, CACHE_CONTROL, CONTENT_TYPE, COOKIE, HeaderMap, HeaderValue, REFERER,
    USER_AGENT,
};
use serde_json::Value;

use crate::{
    app::error::AppError,
    models::tasks::{
        CollectorNotePreview, CollectorPageSignals, CollectorProfilePreview, NoteCardCandidate,
    },
};

pub struct PageProbeResult {
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
}

pub async fn probe_public_page(
    target_url: &str,
    cookie: Option<&str>,
) -> Result<PageProbeResult, AppError> {
    if target_url.trim().is_empty() {
        return Err(AppError::bad_request("Target URL is required."));
    }

    let mut headers = HeaderMap::new();
    headers.insert(
        USER_AGENT,
        HeaderValue::from_static(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
        ),
    );
    headers.insert(
        ACCEPT,
        HeaderValue::from_static("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    );
    headers.insert(
        ACCEPT_LANGUAGE,
        HeaderValue::from_static("zh-CN,zh;q=0.9,en;q=0.7"),
    );
    headers.insert(CACHE_CONTROL, HeaderValue::from_static("no-cache"));
    headers.insert(
        REFERER,
        HeaderValue::from_static("https://www.xiaohongshu.com/"),
    );

    if let Some(raw_cookie) = cookie {
        let cookie_value = HeaderValue::from_str(raw_cookie.trim())
            .map_err(|_| AppError::bad_request("Cookie header contains invalid characters."))?;
        headers.insert(COOKIE, cookie_value);
    }

    let client = reqwest::Client::builder()
        .default_headers(headers)
        .redirect(reqwest::redirect::Policy::limited(5))
        .build()
        .map_err(AppError::internal)?;

    let response = client
        .get(target_url.trim())
        .send()
        .await
        .map_err(AppError::internal)?;

    let status = response.status().as_u16();
    let final_url = response.url().to_string();
    let content_type = response
        .headers()
        .get(CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .map(ToString::to_string);
    let body = response.text().await.map_err(AppError::internal)?;

    let marker_hits = detect_markers(&body);
    let initial_state_payloads = extract_initial_state_payloads(&body, 4);
    let json_ld_blocks = extract_json_ld_blocks(&body, 4);
    let initial_state_values = parse_json_values(&initial_state_payloads);
    let json_ld_values = parse_json_values(&json_ld_blocks);

    let note_link_candidates =
        extract_candidate_links_for_needles(&body, &["/explore/", "\\/explore\\/"], 24);
    let user_link_candidates =
        extract_candidate_links_for_needles(&body, &["/user/profile/", "\\/user\\/profile\\/"], 24);

    let mut note_id_candidates = extract_json_string_values(&body, &["noteId", "note_id"], 20);
    let mut user_id_candidates = extract_json_string_values(&body, &["userId", "user_id"], 20);
    let mut title_candidates = extract_json_string_values(
        &body,
        &[
            "displayTitle",
            "title",
            "noteTitle",
            "note_title",
            "headline",
        ],
        12,
    );
    let mut description_candidates =
        extract_json_string_values(&body, &["desc", "description", "noteDesc"], 12);
    let mut author_candidates =
        extract_json_string_values(&body, &["nickname", "userName", "authorName"], 12);

    collect_json_string_fields(
        &initial_state_values,
        &["noteId", "note_id"],
        &mut note_id_candidates,
        20,
    );
    collect_json_string_fields(
        &initial_state_values,
        &["userId", "user_id"],
        &mut user_id_candidates,
        20,
    );
    collect_json_string_fields(
        &initial_state_values,
        &[
            "displayTitle",
            "title",
            "noteTitle",
            "note_title",
            "headline",
        ],
        &mut title_candidates,
        12,
    );
    collect_json_string_fields(
        &initial_state_values,
        &["desc", "description", "noteDesc"],
        &mut description_candidates,
        12,
    );
    collect_json_string_fields(
        &initial_state_values,
        &["nickname", "userName", "authorName"],
        &mut author_candidates,
        12,
    );

    collect_json_string_fields(
        &json_ld_values,
        &["headline", "name"],
        &mut title_candidates,
        12,
    );
    collect_json_string_fields(
        &json_ld_values,
        &["description"],
        &mut description_candidates,
        12,
    );
    collect_json_author_names(&json_ld_values, &mut author_candidates, 12);

    let title = extract_title(&body);
    let meta_title =
        extract_meta_content(&body, "og:title").or_else(|| extract_meta_content(&body, "title"));
    let meta_description = extract_meta_content(&body, "og:description")
        .or_else(|| extract_meta_content(&body, "description"));
    let canonical_url = extract_canonical_url(&body)
        .or_else(|| extract_meta_content(&body, "og:url"))
        .or_else(|| first_json_field(&json_ld_values, &["url", "mainEntityOfPage"]));

    let canonical_note_id = extract_note_id_from_link(&final_url)
        .or_else(|| canonical_url.as_deref().and_then(extract_note_id_from_link))
        .or_else(|| note_id_candidates.first().cloned())
        .or_else(|| {
            note_link_candidates
                .iter()
                .find_map(|url| extract_note_id_from_link(url))
        });

    let canonical_user_id = extract_user_id_from_link(&final_url)
        .or_else(|| canonical_url.as_deref().and_then(extract_user_id_from_link))
        .or_else(|| user_id_candidates.first().cloned())
        .or_else(|| {
            user_link_candidates
                .iter()
                .find_map(|url| extract_user_id_from_link(url))
        });

    let note_cards = build_note_cards(&body, &note_link_candidates, &note_id_candidates, 16);
    let page_signals = build_page_signals(
        &body,
        initial_state_payloads.len(),
        json_ld_blocks.len(),
        !note_cards.is_empty(),
    );
    let note_preview = build_note_preview(
        &body,
        &meta_title,
        &meta_description,
        canonical_note_id.clone(),
        &title_candidates,
        &description_candidates,
        &author_candidates,
        &json_ld_values,
        &page_signals,
        &note_cards,
    );
    let profile_preview = build_profile_preview(
        &final_url,
        &meta_title,
        &title,
        canonical_user_id.clone(),
        &user_link_candidates,
        &author_candidates,
        &note_cards,
    );

    let page_type = detect_page_type(
        &final_url,
        &page_signals,
        canonical_note_id.is_some(),
        canonical_user_id.is_some(),
        !note_link_candidates.is_empty(),
    );

    Ok(PageProbeResult {
        final_url,
        status,
        content_type,
        title,
        page_type,
        meta_title,
        meta_description,
        canonical_url,
        canonical_note_id,
        canonical_user_id,
        initial_state_blocks: initial_state_payloads.len(),
        json_ld_blocks: json_ld_blocks.len(),
        page_signals,
        title_candidates,
        description_candidates,
        author_candidates,
        marker_hits,
        note_cards,
        note_link_candidates,
        user_link_candidates,
        note_id_candidates,
        user_id_candidates,
        note_preview,
        profile_preview,
        html_excerpt: normalize_excerpt(&body, 800),
    })
}

fn extract_title(body: &str) -> Option<String> {
    let lower = body.to_ascii_lowercase();
    let start = lower.find("<title>")?;
    let end = lower[start + 7..].find("</title>")?;
    let raw = &body[start + 7..start + 7 + end];
    clean_text(raw)
}

fn detect_markers(body: &str) -> Vec<String> {
    let markers = [
        "__INITIAL_STATE__",
        "window.__INITIAL_STATE__",
        "xsec_token",
        "noteId",
        "userId",
        "captcha",
        "\u{9A8C}\u{8BC1}",
        "\u{767B}\u{5F55}",
    ];

    markers
        .iter()
        .filter(|marker| body.contains(**marker))
        .map(|marker| (*marker).to_string())
        .collect()
}

fn normalize_excerpt(body: &str, max_chars: usize) -> String {
    body.chars()
        .map(|ch| match ch {
            '\n' | '\r' | '\t' => ' ',
            other => other,
        })
        .collect::<String>()
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .chars()
        .take(max_chars)
        .collect()
}

fn extract_meta_content(body: &str, property_or_name: &str) -> Option<String> {
    for tag in extract_start_tags(body, "meta", 80) {
        let property_matches = tag_attribute_matches(tag, "property", property_or_name);
        let name_matches = tag_attribute_matches(tag, "name", property_or_name);
        if property_matches || name_matches {
            if let Some(content) = extract_html_attribute(tag, "content") {
                return clean_text(&content);
            }
        }
    }

    None
}

fn extract_canonical_url(body: &str) -> Option<String> {
    for tag in extract_start_tags(body, "link", 40) {
        if tag_attribute_matches(tag, "rel", "canonical") {
            if let Some(href) = extract_html_attribute(tag, "href") {
                return Some(normalize_xiaohongshu_link(&href));
            }
        }
    }

    None
}

fn extract_start_tags<'a>(body: &'a str, tag_name: &str, limit: usize) -> Vec<&'a str> {
    let lower = body.to_ascii_lowercase();
    let needle = format!("<{tag_name}");
    let mut tags = Vec::new();
    let mut cursor = 0;

    while let Some(relative_index) = lower[cursor..].find(&needle) {
        let start = cursor + relative_index;
        let Some(end_relative) = body[start..].find('>') else {
            break;
        };
        let end = start + end_relative + 1;
        tags.push(&body[start..end]);
        cursor = end;

        if tags.len() >= limit {
            break;
        }
    }

    tags
}

fn tag_attribute_matches(tag: &str, attribute: &str, expected_value: &str) -> bool {
    extract_html_attribute(tag, attribute)
        .map(|value| value.eq_ignore_ascii_case(expected_value))
        .unwrap_or(false)
}

fn extract_html_attribute(tag: &str, attribute: &str) -> Option<String> {
    let lower_tag = tag.to_ascii_lowercase();
    let attribute = attribute.to_ascii_lowercase();

    for quote in ['"', '\''] {
        let pattern = format!("{attribute}={quote}");
        if let Some(start) = lower_tag.find(&pattern) {
            let value_start = start + pattern.len();
            let value_end = tag[value_start..].find(quote)?;
            let value = &tag[value_start..value_start + value_end];
            return Some(html_unescape(value).trim().to_string());
        }
    }

    let pattern = format!("{attribute}=");
    if let Some(start) = lower_tag.find(&pattern) {
        let value_start = start + pattern.len();
        let value_end = tag[value_start..]
            .find(|ch: char| ch.is_whitespace() || ch == '>')
            .unwrap_or(tag.len() - value_start);
        let value = &tag[value_start..value_start + value_end];
        return Some(
            html_unescape(value)
                .trim_matches('"')
                .trim_matches('\'')
                .to_string(),
        );
    }

    None
}

fn extract_candidate_links_for_needles(body: &str, needles: &[&str], limit: usize) -> Vec<String> {
    let mut candidates = Vec::new();

    for needle in needles {
        let mut cursor = 0;

        while let Some(relative_index) = body[cursor..].find(needle) {
            let start = cursor + relative_index;
            let token_start = find_token_start(body, start);
            let token_end = find_token_end(body, start + needle.len());
            let raw = body[token_start..token_end].trim();
            let normalized = normalize_xiaohongshu_link(raw);

            if normalized.contains("/explore/") || normalized.contains("/user/profile/") {
                push_unique(&mut candidates, normalized, limit);
            }

            cursor = start + needle.len();
            if cursor >= body.len() || candidates.len() >= limit {
                break;
            }
        }
    }

    candidates
}

fn find_token_start(body: &str, index: usize) -> usize {
    let bytes = body.as_bytes();
    let mut start = index;

    while start > 0 {
        let ch = bytes[start - 1] as char;
        if is_link_boundary(ch) {
            break;
        }
        start -= 1;
    }

    start
}

fn find_token_end(body: &str, index: usize) -> usize {
    let bytes = body.as_bytes();
    let mut end = index;

    while end < bytes.len() {
        let ch = bytes[end] as char;
        if is_link_boundary(ch) {
            break;
        }
        end += 1;
    }

    end
}

fn is_link_boundary(ch: char) -> bool {
    ch.is_whitespace()
        || matches!(
            ch,
            '"' | '\'' | '<' | '>' | '(' | ')' | '[' | ']' | '{' | '}' | ','
        )
}

fn normalize_xiaohongshu_link(raw: &str) -> String {
    let normalized = html_unescape(raw)
        .replace("\\u002F", "/")
        .replace("\\u0026", "&")
        .replace("\\/", "/")
        .replace("&amp;", "&")
        .trim_matches(|ch: char| {
            ch.is_whitespace() || matches!(ch, '"' | '\'' | ',' | ';' | ')' | ']')
        })
        .to_string();

    if normalized.starts_with("https://www.xiaohongshu.com")
        || normalized.starts_with("https://xiaohongshu.com")
        || normalized.starts_with("http://www.xiaohongshu.com")
        || normalized.starts_with("http://xiaohongshu.com")
    {
        normalized
    } else if normalized.starts_with("//www.xiaohongshu.com")
        || normalized.starts_with("//xiaohongshu.com")
    {
        format!("https:{normalized}")
    } else if normalized.starts_with("www.xiaohongshu.com")
        || normalized.starts_with("xiaohongshu.com")
    {
        format!("https://{normalized}")
    } else if normalized.starts_with('/') {
        format!("https://www.xiaohongshu.com{normalized}")
    } else {
        normalized
    }
}

fn extract_json_string_values(body: &str, keys: &[&str], limit: usize) -> Vec<String> {
    let mut values = Vec::new();

    for key in keys {
        for key_pattern in [format!("\"{key}\""), format!("'{key}'")] {
            let mut cursor = 0;

            while let Some(relative_index) = body[cursor..].find(&key_pattern) {
                let key_index = cursor + relative_index;
                let after_key = key_index + key_pattern.len();
                let Some(colon_relative) = body[after_key..].find(':') else {
                    break;
                };
                let colon_index = after_key + colon_relative;

                if let Some((quote, value_start)) = find_opening_quote(body, colon_index + 1) {
                    if let Some((value, next_index)) = read_quoted_value(body, value_start, quote) {
                        if let Some(cleaned) = clean_text(&value) {
                            push_unique(&mut values, cleaned, limit);
                        }
                        cursor = next_index;
                    } else {
                        cursor = value_start;
                    }
                } else {
                    cursor = after_key;
                }

                if values.len() >= limit {
                    return values;
                }
            }
        }
    }

    values
}

fn extract_json_number_values(body: &str, keys: &[&str], limit: usize) -> Vec<String> {
    let mut values = Vec::new();

    for key in keys {
        let pattern = format!("\"{key}\"");
        let mut cursor = 0;

        while let Some(relative_index) = body[cursor..].find(&pattern) {
            let key_index = cursor + relative_index;
            let after_key = key_index + pattern.len();
            let Some(colon_relative) = body[after_key..].find(':') else {
                break;
            };
            let mut value_index = after_key + colon_relative + 1;

            while let Some(ch) = body[value_index..].chars().next() {
                if ch.is_whitespace() {
                    value_index += ch.len_utf8();
                } else {
                    break;
                }
            }

            let number_len = body[value_index..]
                .chars()
                .take_while(|ch| ch.is_ascii_digit())
                .map(char::len_utf8)
                .sum::<usize>();

            if number_len > 0 {
                let number = &body[value_index..value_index + number_len];
                push_unique(&mut values, number.to_string(), limit);
            }

            cursor = value_index.saturating_add(number_len);
            if cursor >= body.len() || values.len() >= limit {
                break;
            }
        }
    }

    values
}

fn find_opening_quote(body: &str, start: usize) -> Option<(char, usize)> {
    let mut index = start;

    while index < body.len() {
        let ch = body[index..].chars().next()?;
        if ch.is_whitespace() {
            index += ch.len_utf8();
            continue;
        }

        if ch == '"' || ch == '\'' {
            return Some((ch, index + ch.len_utf8()));
        }

        return None;
    }

    None
}

fn read_quoted_value(body: &str, start: usize, quote: char) -> Option<(String, usize)> {
    let mut escaped = false;
    let mut value = String::new();
    let mut index = start;

    while index < body.len() {
        let ch = body[index..].chars().next()?;
        index += ch.len_utf8();

        if escaped {
            value.push(ch);
            escaped = false;
            continue;
        }

        if ch == '\\' {
            escaped = true;
            continue;
        }

        if ch == quote {
            return Some((value, index));
        }

        value.push(ch);
    }

    None
}

fn extract_initial_state_payloads(body: &str, limit: usize) -> Vec<String> {
    let mut payloads = Vec::new();
    let mut cursor = 0;

    while let Some(relative_index) = body[cursor..].find("__INITIAL_STATE__") {
        let marker_index = cursor + relative_index;
        let Some(brace_relative) = body[marker_index..].find('{') else {
            break;
        };
        let brace_index = marker_index + brace_relative;

        if let Some(payload) = extract_balanced_json_object(body, brace_index) {
            push_unique(&mut payloads, payload.to_string(), limit);
            cursor = brace_index + payload.len();
        } else {
            cursor = marker_index + "__INITIAL_STATE__".len();
        }

        if payloads.len() >= limit || cursor >= body.len() {
            break;
        }
    }

    payloads
}

fn extract_balanced_json_object(body: &str, start: usize) -> Option<&str> {
    let bytes = body.as_bytes();
    if *bytes.get(start)? != b'{' {
        return None;
    }

    let mut depth = 0_usize;
    let mut in_string = false;
    let mut escaped = false;

    for index in start..bytes.len() {
        let byte = bytes[index];

        if in_string {
            if escaped {
                escaped = false;
                continue;
            }

            match byte {
                b'\\' => escaped = true,
                b'"' => in_string = false,
                _ => {}
            }
            continue;
        }

        match byte {
            b'"' => in_string = true,
            b'{' => depth += 1,
            b'}' => {
                depth = depth.saturating_sub(1);
                if depth == 0 {
                    return Some(&body[start..=index]);
                }
            }
            _ => {}
        }
    }

    None
}

fn extract_json_ld_blocks(body: &str, limit: usize) -> Vec<String> {
    let lower = body.to_ascii_lowercase();
    let mut blocks = Vec::new();
    let mut cursor = 0;

    while let Some(relative_index) = lower[cursor..].find("<script") {
        let start = cursor + relative_index;
        let Some(tag_end_relative) = lower[start..].find('>') else {
            break;
        };
        let tag_end = start + tag_end_relative + 1;
        let tag = &body[start..tag_end];

        let is_json_ld = extract_html_attribute(tag, "type")
            .map(|value| value.eq_ignore_ascii_case("application/ld+json"))
            .unwrap_or(false);

        let Some(close_relative) = lower[tag_end..].find("</script>") else {
            break;
        };
        let close_index = tag_end + close_relative;

        if is_json_ld {
            let raw = body[tag_end..close_index].trim();
            if !raw.is_empty() {
                push_unique(&mut blocks, raw.to_string(), limit);
            }
        }

        cursor = close_index + "</script>".len();
        if blocks.len() >= limit || cursor >= body.len() {
            break;
        }
    }

    blocks
}

fn parse_json_values(payloads: &[String]) -> Vec<Value> {
    payloads
        .iter()
        .filter_map(|payload| serde_json::from_str::<Value>(payload).ok())
        .collect()
}

fn collect_json_string_fields(
    values: &[Value],
    keys: &[&str],
    output: &mut Vec<String>,
    limit: usize,
) {
    for value in values {
        collect_json_string_fields_from_value(value, keys, output, limit);
        if output.len() >= limit {
            break;
        }
    }
}

fn collect_json_string_fields_from_value(
    value: &Value,
    keys: &[&str],
    output: &mut Vec<String>,
    limit: usize,
) {
    if output.len() >= limit {
        return;
    }

    match value {
        Value::Object(map) => {
            for (key, nested) in map {
                if keys.iter().any(|candidate| key == candidate) {
                    match nested {
                        Value::String(text) => {
                            if let Some(cleaned) = clean_text(text) {
                                push_unique(output, cleaned, limit);
                            }
                        }
                        Value::Number(number) => {
                            push_unique(output, number.to_string(), limit);
                        }
                        _ => {}
                    }
                }

                collect_json_string_fields_from_value(nested, keys, output, limit);
                if output.len() >= limit {
                    return;
                }
            }
        }
        Value::Array(items) => {
            for item in items {
                collect_json_string_fields_from_value(item, keys, output, limit);
                if output.len() >= limit {
                    return;
                }
            }
        }
        _ => {}
    }
}

fn collect_json_author_names(values: &[Value], output: &mut Vec<String>, limit: usize) {
    for value in values {
        collect_json_author_names_from_value(value, output, limit);
        if output.len() >= limit {
            break;
        }
    }
}

fn collect_json_author_names_from_value(value: &Value, output: &mut Vec<String>, limit: usize) {
    if output.len() >= limit {
        return;
    }

    match value {
        Value::Object(map) => {
            if let Some(author) = map.get("author") {
                collect_name_like(author, output, limit);
            }

            for nested in map.values() {
                collect_json_author_names_from_value(nested, output, limit);
                if output.len() >= limit {
                    return;
                }
            }
        }
        Value::Array(items) => {
            for item in items {
                collect_json_author_names_from_value(item, output, limit);
                if output.len() >= limit {
                    return;
                }
            }
        }
        _ => {}
    }
}

fn collect_name_like(value: &Value, output: &mut Vec<String>, limit: usize) {
    if output.len() >= limit {
        return;
    }

    match value {
        Value::String(text) => {
            if let Some(cleaned) = clean_text(text) {
                push_unique(output, cleaned, limit);
            }
        }
        Value::Object(map) => {
            if let Some(Value::String(name)) = map.get("name") {
                if let Some(cleaned) = clean_text(name) {
                    push_unique(output, cleaned, limit);
                }
            }
        }
        Value::Array(items) => {
            for item in items {
                collect_name_like(item, output, limit);
                if output.len() >= limit {
                    return;
                }
            }
        }
        _ => {}
    }
}

fn first_json_field(values: &[Value], keys: &[&str]) -> Option<String> {
    let mut items = Vec::new();
    collect_json_string_fields(values, keys, &mut items, 1);
    items.into_iter().next()
}

fn build_note_cards(
    body: &str,
    note_links: &[String],
    note_ids: &[String],
    limit: usize,
) -> Vec<NoteCardCandidate> {
    let mut cards = Vec::new();

    for url in note_links {
        let note_id = extract_note_id_from_link(url);
        let context = note_context(body, url, note_id.as_deref());
        let title_hint = context
            .and_then(|snippet| first_text_value(snippet, &["displayTitle", "title", "noteTitle"]));
        let description_hint = context
            .and_then(|snippet| first_text_value(snippet, &["desc", "description", "noteDesc"]));
        let author_hint = context
            .and_then(|snippet| first_text_value(snippet, &["nickname", "userName", "authorName"]));
        let xsec_token_present = url.contains("xsec_token=")
            || context
                .map(|snippet| snippet.contains("xsec_token"))
                .unwrap_or(false);

        cards.push(NoteCardCandidate {
            url: url.clone(),
            note_id,
            title_hint,
            description_hint,
            author_hint,
            xsec_token_present,
        });

        if cards.len() >= limit {
            return cards;
        }
    }

    for note_id in note_ids {
        let url = format!("https://www.xiaohongshu.com/explore/{note_id}");
        if cards.iter().any(|card| card.url == url) {
            continue;
        }

        cards.push(NoteCardCandidate {
            url,
            note_id: Some(note_id.clone()),
            title_hint: None,
            description_hint: None,
            author_hint: None,
            xsec_token_present: false,
        });

        if cards.len() >= limit {
            break;
        }
    }

    cards
}

fn note_context<'a>(body: &'a str, url: &str, note_id: Option<&str>) -> Option<&'a str> {
    if let Some(index) = body.find(url) {
        return Some(slice_around(body, index, url.len(), 800, 1600));
    }

    if let Some(note_id) = note_id {
        if let Some(index) = body.find(note_id) {
            return Some(slice_around(body, index, note_id.len(), 800, 1600));
        }
    }

    None
}

fn slice_around(body: &str, start: usize, marker_len: usize, before: usize, after: usize) -> &str {
    let from = start.saturating_sub(before);
    let to = (start + marker_len + after).min(body.len());
    &body[from..to]
}

fn first_text_value(body: &str, keys: &[&str]) -> Option<String> {
    extract_json_string_values(body, keys, 1).into_iter().next()
}

fn build_page_signals(
    body: &str,
    initial_state_blocks: usize,
    json_ld_blocks: usize,
    has_note_cards: bool,
) -> CollectorPageSignals {
    let lower = body.to_ascii_lowercase();
    let challenge_detected =
        lower.contains("captcha") || lower.contains("verify") || body.contains("\u{9A8C}\u{8BC1}");
    let auth_wall_detected = lower.contains("login")
        || lower.contains("sign in")
        || body.contains("\u{767B}\u{5F55}")
        || body.contains("\u{767B}\u{9646}");
    let looks_like_video = lower.contains("\"type\":\"video\"")
        || lower.contains("video/mp4")
        || lower.contains("originvideokey")
        || lower.contains("\"videokey\"");
    let looks_like_image_gallery =
        lower.contains("\"imagelist\"") || lower.contains("\"imageslist\"");

    CollectorPageSignals {
        has_initial_state: initial_state_blocks > 0,
        has_json_ld: json_ld_blocks > 0,
        has_note_cards,
        has_xsec_token: body.contains("xsec_token"),
        looks_like_video,
        looks_like_image_gallery,
        auth_wall_detected,
        challenge_detected,
    }
}

fn build_note_preview(
    body: &str,
    meta_title: &Option<String>,
    meta_description: &Option<String>,
    canonical_note_id: Option<String>,
    title_candidates: &[String],
    description_candidates: &[String],
    author_candidates: &[String],
    json_ld_values: &[Value],
    page_signals: &CollectorPageSignals,
    note_cards: &[NoteCardCandidate],
) -> Option<CollectorNotePreview> {
    let note_id =
        canonical_note_id.or_else(|| note_cards.iter().find_map(|card| card.note_id.clone()));
    let title = first_non_generic_text([
        meta_title.clone(),
        title_candidates.first().cloned(),
        first_json_field(json_ld_values, &["headline", "name"]),
        note_cards.iter().find_map(|card| card.title_hint.clone()),
    ]);
    let description = first_non_empty([
        meta_description.clone(),
        description_candidates.first().cloned(),
        first_json_field(json_ld_values, &["description"]),
        note_cards
            .iter()
            .find_map(|card| card.description_hint.clone()),
    ]);
    let author = first_non_empty([
        note_cards.iter().find_map(|card| card.author_hint.clone()),
        author_candidates.first().cloned(),
        first_json_field(json_ld_values, &["authorName"]),
    ]);
    let mut publish_time_candidates =
        extract_json_string_values(body, &["publishTime", "publish_time", "datePublished"], 6);
    let numeric_times = extract_json_number_values(body, &["publishTime", "publish_time"], 6);
    for item in numeric_times {
        push_unique(&mut publish_time_candidates, item, 6);
    }

    if let Some(json_ld_time) = first_json_field(json_ld_values, &["datePublished", "dateModified"])
    {
        push_unique(&mut publish_time_candidates, json_ld_time, 6);
    }

    let image_count_hint = estimate_image_count(body);
    let has_video = page_signals.looks_like_video;

    if note_id.is_none()
        && title.is_none()
        && description.is_none()
        && author.is_none()
        && !has_video
    {
        return None;
    }

    Some(CollectorNotePreview {
        note_id,
        title,
        description,
        author,
        publish_time_candidates,
        image_count_hint,
        has_video,
    })
}

fn build_profile_preview(
    final_url: &str,
    meta_title: &Option<String>,
    page_title: &Option<String>,
    canonical_user_id: Option<String>,
    user_link_candidates: &[String],
    author_candidates: &[String],
    note_cards: &[NoteCardCandidate],
) -> Option<CollectorProfilePreview> {
    let profile_url = if final_url.contains("/user/profile/") {
        Some(final_url.to_string())
    } else {
        user_link_candidates.first().cloned()
    };
    let nickname = extract_profile_nickname(meta_title, page_title)
        .or_else(|| author_candidates.first().cloned());

    if canonical_user_id.is_none()
        && profile_url.is_none()
        && nickname.is_none()
        && note_cards.is_empty()
    {
        return None;
    }

    Some(CollectorProfilePreview {
        user_id: canonical_user_id,
        profile_url,
        nickname,
        recent_note_count: note_cards.len(),
    })
}

fn estimate_image_count(body: &str) -> Option<usize> {
    let mut count = 0_usize;
    let mut cursor = 0;
    let pattern = "\"imageScene\"";

    while let Some(relative_index) = body[cursor..].find(pattern) {
        count += 1;
        cursor += relative_index + pattern.len();
        if count >= 32 || cursor >= body.len() {
            break;
        }
    }

    (count > 0).then_some(count)
}

fn extract_profile_nickname(
    meta_title: &Option<String>,
    page_title: &Option<String>,
) -> Option<String> {
    for candidate in [meta_title.as_deref(), page_title.as_deref()]
        .into_iter()
        .flatten()
    {
        for suffix in [
            "\u{7684}\u{5C0F}\u{7EA2}\u{4E66}\u{4E3B}\u{9875}",
            "\u{7684}\u{7B14}\u{8BB0}",
            " - \u{5C0F}\u{7EA2}\u{4E66}",
            " | \u{5C0F}\u{7EA2}\u{4E66}",
        ] {
            if let Some(prefix) = candidate.split(suffix).next() {
                if prefix != candidate {
                    if let Some(cleaned) = clean_text(prefix) {
                        if !looks_generic_title(&cleaned) {
                            return Some(cleaned);
                        }
                    }
                }
            }
        }
    }

    None
}

fn detect_page_type(
    final_url: &str,
    page_signals: &CollectorPageSignals,
    has_note_id: bool,
    has_user_id: bool,
    has_note_links: bool,
) -> String {
    let lower_url = final_url.to_ascii_lowercase();

    if page_signals.challenge_detected {
        return "captcha_or_challenge".to_string();
    }

    if page_signals.auth_wall_detected && !has_note_links && !has_note_id {
        return "login_gate_or_auth_wall".to_string();
    }

    if lower_url.contains("/explore/") || has_note_id {
        return "note_detail".to_string();
    }

    if lower_url.contains("/user/profile/") || has_user_id {
        return "user_profile".to_string();
    }

    if has_note_links || page_signals.has_note_cards {
        return "note_feed_or_listing".to_string();
    }

    "unknown".to_string()
}

fn extract_note_id_from_link(url: &str) -> Option<String> {
    extract_path_id(url, "/explore/")
}

fn extract_user_id_from_link(url: &str) -> Option<String> {
    extract_path_id(url, "/user/profile/")
}

fn extract_path_id(url: &str, marker: &str) -> Option<String> {
    let start = url.find(marker)? + marker.len();
    let tail = &url[start..];
    let end = tail.find(['?', '#', '/', '&']).unwrap_or(tail.len());
    let candidate = tail[..end].trim();
    if candidate.is_empty() {
        None
    } else {
        Some(candidate.to_string())
    }
}

fn clean_text(raw: &str) -> Option<String> {
    let cleaned = html_unescape(raw)
        .replace("\\n", " ")
        .replace("\\r", " ")
        .replace("\\t", " ")
        .replace('\n', " ")
        .replace('\r', " ")
        .replace('\t', " ")
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .trim()
        .to_string();

    if cleaned.is_empty() || cleaned.len() > 400 {
        return None;
    }

    Some(cleaned)
}

fn looks_generic_title(text: &str) -> bool {
    let lower = text.to_ascii_lowercase();
    lower == "xiaohongshu"
        || text == "\u{5C0F}\u{7EA2}\u{4E66}"
        || text.contains("\u{5C0F}\u{7EA2}\u{4E66} - ")
        || text.contains("\u{5C0F}\u{7EA2}\u{4E66}\u{4F60}\u{7684}\u{751F}\u{6D3B}\u{6307}\u{5357}")
}

fn first_non_generic_text<T>(items: T) -> Option<String>
where
    T: IntoIterator<Item = Option<String>>,
{
    items
        .into_iter()
        .flatten()
        .find(|item| !looks_generic_title(item))
}

fn first_non_empty<T>(items: T) -> Option<String>
where
    T: IntoIterator<Item = Option<String>>,
{
    items.into_iter().flatten().next()
}

fn push_unique(values: &mut Vec<String>, candidate: String, limit: usize) {
    if values.len() >= limit || values.iter().any(|existing| existing == &candidate) {
        return;
    }

    values.push(candidate);
}

fn html_unescape(input: &str) -> String {
    input
        .replace("&quot;", "\"")
        .replace("&#34;", "\"")
        .replace("&apos;", "'")
        .replace("&#39;", "'")
        .replace("&#x27;", "'")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
}
