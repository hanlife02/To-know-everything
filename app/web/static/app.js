const grid = document.getElementById("grid");
const statusNode = document.getElementById("status");
const metaNode = document.getElementById("meta");
const errorPanel = document.getElementById("error-panel");
const apiKeyInput = document.getElementById("api-key");
const categoryFilter = document.getElementById("category-filter");
const limitInput = document.getElementById("limit");
const recentHoursInput = document.getElementById("recent-hours");
const refreshButton = document.getElementById("refresh");

const storageKey = "social-pulse-board-api-key";
apiKeyInput.value = localStorage.getItem(storageKey) || "";

apiKeyInput.addEventListener("change", () => {
  localStorage.setItem(storageKey, apiKeyInput.value.trim());
});

refreshButton.addEventListener("click", () => {
  loadContent();
});

categoryFilter.addEventListener("change", () => {
  loadContent();
});

function collectValues(name) {
  return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((node) => node.value);
}

function updateCategories(categories, currentValue) {
  const options = ['<option value="">全部分类</option>'];
  categories.forEach((category) => {
    const selected = currentValue === category ? "selected" : "";
    options.push(`<option value="${category}" ${selected}>${category}</option>`);
  });
  categoryFilter.innerHTML = options.join("");
}

function renderItems(items) {
  if (!items.length) {
    grid.innerHTML = '<article class="item-card"><p class="item-summary">当前筛选条件下没有返回内容。</p></article>';
    return;
  }

  grid.innerHTML = items
    .map((item) => {
      const tags = (item.tags || []).slice(0, 4).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("");
      const cover = item.cover_url
        ? `<img class="item-cover" src="${escapeHtml(item.cover_url)}" alt="${escapeHtml(item.title)}" loading="lazy" referrerpolicy="no-referrer" />`
        : `<div class="item-cover"></div>`;
      const publishedText = formatPublishedAt(item.published_at);
      const recencyBadge = item.metadata?.recency_state === "unknown"
        ? '<span class="badge">time-unknown</span>'
        : "";

      return `
        <article class="item-card">
          <a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">
            ${cover}
          </a>
          <div class="item-header">
            <span class="badge accent">${escapeHtml(item.platform)}</span>
            <span class="badge">${escapeHtml(item.feed_kind)}</span>
            <span class="badge">${escapeHtml(item.category)}</span>
            ${recencyBadge}
          </div>
          <a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">
            <h2 class="item-title">${escapeHtml(item.title)}</h2>
          </a>
          <p class="item-summary">${escapeHtml(item.summary || "暂无摘要")}</p>
          <div class="meta-list">
            <span>${escapeHtml(item.author || "未知来源")}</span>
            <span>${escapeHtml(item.source_category || item.content_type)}</span>
            <span>${escapeHtml(item.popularity_text || "无热度字段")}</span>
            <span>${escapeHtml(publishedText)}</span>
          </div>
          <div class="tags">${tags}</div>
          <a class="item-link" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">查看原文</a>
        </article>
      `;
    })
    .join("");
}

function renderErrors(errors) {
  if (!errors.length) {
    errorPanel.classList.add("hidden");
    errorPanel.innerHTML = "";
    return;
  }

  errorPanel.classList.remove("hidden");
  errorPanel.innerHTML = errors
    .map((error) => `<div>${escapeHtml(error.platform)} / ${escapeHtml(error.feed_kind)}: ${escapeHtml(error.message)}</div>`)
    .join("");
}

async function loadContent() {
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) {
    statusNode.textContent = "请输入 API Key 后再请求";
    return;
  }

  statusNode.textContent = "抓取中...";
  metaNode.textContent = "";
  refreshButton.disabled = true;

  const params = new URLSearchParams();
  collectValues("platform").forEach((value) => params.append("platforms", value));
  collectValues("feed-kind").forEach((value) => params.append("feed_kinds", value));
  if (categoryFilter.value) {
    params.append("categories", categoryFilter.value);
  }
  params.append("limit", limitInput.value || "12");
  params.append("recent_hours", recentHoursInput.value || "24");

  try {
    const response = await fetch(`/api/content?${params.toString()}`, {
      headers: {
        "X-API-Key": apiKey,
      },
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Request failed with ${response.status}`);
    }

    const payload = await response.json();
    const selectedFeedKinds = collectValues("feed-kind");
    const hotOnly = selectedFeedKinds.length === 1 && selectedFeedKinds[0] === "hot";
    updateCategories(payload.categories || [], categoryFilter.value);
    renderItems(payload.items || []);
    renderErrors(payload.errors || []);
    statusNode.textContent = `已拉取 ${payload.total} 条内容`;
    metaNode.textContent = hotOnly
      ? `更新时间 ${new Date(payload.fetched_at).toLocaleString()} · 优先近 ${recentHoursInput.value} 小时热门，数量不足时补充时间未知的热门内容`
      : `更新时间 ${new Date(payload.fetched_at).toLocaleString()} · 仅保留近 ${recentHoursInput.value} 小时内容`;
  } catch (error) {
    renderItems([]);
    renderErrors([]);
    statusNode.textContent = "请求失败";
    metaNode.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
  }
}

function formatPublishedAt(value) {
  if (!value) {
    return "发布时间未知";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "发布时间未知";
  }
  return `发布时间 ${date.toLocaleString()}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

loadContent();
