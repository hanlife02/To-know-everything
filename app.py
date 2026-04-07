from __future__ import annotations

import os
from datetime import datetime, timedelta
from secrets import compare_digest
from urllib.parse import urlparse

from automation import (
    AutomationSettings,
    automation_scheduler,
    clamp_int,
    get_automation_status,
    load_automation_settings,
    parse_bool,
    run_automation_job,
    save_automation_settings,
    serialize_automation_settings,
)
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from bilibili.web import load_page_data as load_bilibili_page_data
from bilibili.web import refresh_page_data as refresh_bilibili_page_data
from content_filters import filter_dashboard_for_summary, get_today, parse_item_date
from daily_job import refresh_dashboard_data, run_all as run_full_pipeline
from daily_report import (
    build_ai_daily_report_messages,
    build_ai_daily_reports,
    load_cached_ai_daily_reports,
    save_ai_daily_reports,
    serialize_ai_daily_reports,
)
from llm import (
    LLMSettings,
    fetch_models,
    get_llm_status,
    load_llm_settings,
    load_models_cache,
    save_llm_settings,
    save_models_cache,
    serialize_llm_settings,
)
from notifications import (
    NotificationSettings,
    build_combined_digest,
    build_platform_digest,
    get_notification_status,
    load_notification_settings,
    save_notification_settings,
    send_bark_notification,
    send_notification,
    send_telegram_messages,
    serialize_notification_settings,
)
from materials_notice.web import load_page_data as load_materials_notices_page_data
from materials_notice.web import refresh_page_data as refresh_materials_notices_page_data
from runtime_config import get_host, get_port, load_local_env, parse_env_bool
from xhs.web import load_page_data as load_xhs_page_data
from xhs.web import refresh_page_data as refresh_xhs_page_data
from delivery_state import set_delivery_signature

ACCESS_KEY_ENV = "APP_ACCESS_KEY"
ACCESS_SESSION_KEY = "access_granted"
ALLOWED_ANON_ENDPOINTS = {"login", "static"}


load_local_env()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "content-digest-dashboard-dev-secret")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=parse_env_bool(os.getenv("SESSION_COOKIE_SECURE", ""), False),
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
)


def ensure_automation_scheduler() -> None:
    automation_scheduler.start()


def get_access_key() -> str:
    return os.getenv(ACCESS_KEY_ENV, "").strip()


def has_valid_access_key(candidate: str) -> bool:
    configured_key = get_access_key()
    submitted_key = candidate.strip()
    return bool(configured_key and submitted_key) and compare_digest(submitted_key, configured_key)


def request_has_valid_access_key() -> bool:
    return has_valid_access_key(request.headers.get("X-API-Key", ""))


def is_authenticated() -> bool:
    return bool(session.get(ACCESS_SESSION_KEY))


def resolve_redirect_target(target: str, default_endpoint: str = "index") -> str:
    candidate = target.strip()
    if candidate:
        parsed = urlparse(candidate)
        if (not parsed.netloc or parsed.netloc == request.host) and parsed.scheme in ("", "http", "https"):
            return candidate
    return url_for(default_endpoint)


@app.before_request
def ensure_automation_scheduler_before_request():
    ensure_automation_scheduler()

    if request.endpoint in ALLOWED_ANON_ENDPOINTS or request.path == "/favicon.ico":
        return None
    if request_has_valid_access_key() or is_authenticated():
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Unauthorized"}), 401

    next_target = request.full_path if request.query_string else request.path
    return redirect(url_for("login", next=next_target))


def load_dashboard_data() -> dict:
    return {
        "bilibili": load_bilibili_page_data(),
        "materials_notices": load_materials_notices_page_data(),
        "xhs": load_xhs_page_data(),
    }


def build_notify_payload(target: str, dashboard: dict) -> tuple[str, str, dict[str, str]]:
    filtered_dashboard = filter_dashboard_for_summary(dashboard)
    state_updates: dict[str, str] = {}

    if target == "bilibili":
        bilibili = filtered_dashboard["bilibili"]
        return (*build_platform_digest("Bilibili", bilibili["overview"], bilibili["videos"]), state_updates)
    if target == "materials_notices":
        materials_notices = filtered_dashboard["materials_notices"]
        return (*build_platform_digest(
            "材料学院通知",
            materials_notices["overview"],
            materials_notices["notices"],
        ), state_updates)
    if target == "xhs":
        xhs = filtered_dashboard["xhs"]
        if xhs.get("notes") and xhs.get("content_signature"):
            state_updates["xhs"] = str(xhs["content_signature"]).strip()
        return (*build_platform_digest("小红书", xhs["overview"], xhs["notes"]), state_updates)
    if target == "all":
        xhs = filtered_dashboard["xhs"]
        if xhs.get("notes") and xhs.get("content_signature"):
            state_updates["xhs"] = str(xhs["content_signature"]).strip()
        return (
            *build_combined_digest(
                filtered_dashboard["bilibili"],
                filtered_dashboard["materials_notices"],
                filtered_dashboard["xhs"],
            ),
            state_updates,
        )
    raise ValueError(f"Unsupported notification target: {target}")


def redirect_back(default_endpoint: str):
    target = request.form.get("next", "").strip() or request.referrer or ""
    return redirect(resolve_redirect_target(target, default_endpoint))


@app.route("/login", methods=["GET", "POST"])
def login():
    next_target = request.form.get("next", "").strip() or request.args.get("next", "").strip()

    if not get_access_key():
        if request.method == "POST":
            flash("APP_ACCESS_KEY 未配置，无法启用访问保护。", "error")
        return render_template(
            "login.html",
            active_page="login",
            next_target=next_target,
            access_key_configured=False,
        )

    if is_authenticated():
        return redirect(resolve_redirect_target(next_target, "index"))

    if request.method == "POST":
        submitted_key = request.form.get("api_key", "")
        if has_valid_access_key(submitted_key):
            session.clear()
            session.permanent = True
            session[ACCESS_SESSION_KEY] = True
            flash("访问验证通过。", "success")
            return redirect(resolve_redirect_target(next_target, "index"))
        flash("API key 不正确。", "error")

    return render_template(
        "login.html",
        active_page="login",
        next_target=next_target,
        access_key_configured=True,
    )


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("已退出访问。", "success")
    return redirect(url_for("login"))


@app.route("/")
def index():
    dashboard = load_dashboard_data()
    notification_settings = load_notification_settings()
    llm_settings = load_llm_settings()
    ai_daily_reports = load_cached_ai_daily_reports()
    return render_template(
        "index.html",
        bilibili=dashboard["bilibili"],
        materials_notices=dashboard["materials_notices"],
        xhs=dashboard["xhs"],
        notification_settings=serialize_notification_settings(notification_settings),
        notification_status=get_notification_status(notification_settings),
        llm_settings=serialize_llm_settings(llm_settings),
        llm_status=get_llm_status(llm_settings),
        ai_daily_reports=serialize_ai_daily_reports(ai_daily_reports),
        active_page="home",
    )


@app.route("/notifications")
def notifications_page():
    notification_settings = load_notification_settings()
    automation_settings = load_automation_settings()
    dashboard = load_dashboard_data()
    return render_template(
        "notifications.html",
        notification_settings=serialize_notification_settings(notification_settings),
        notification_status=get_notification_status(notification_settings),
        automation_settings=serialize_automation_settings(automation_settings),
        automation_status=get_automation_status(automation_settings),
        scheduler_running=automation_scheduler.is_running(),
        bilibili=dashboard["bilibili"],
        materials_notices=dashboard["materials_notices"],
        xhs=dashboard["xhs"],
        ai_daily_reports=serialize_ai_daily_reports(load_cached_ai_daily_reports()),
        active_page="notifications",
    )


@app.route("/llm")
def llm_page():
    llm_settings = load_llm_settings()
    return render_template(
        "llm.html",
        llm_settings=serialize_llm_settings(llm_settings),
        llm_status=get_llm_status(llm_settings),
        llm_models=load_models_cache(),
        active_page="llm",
    )


@app.route("/debug")
def debug_page():
    dashboard = load_dashboard_data()
    return render_template(
        "debug.html",
        bilibili=dashboard["bilibili"],
        materials_notices=dashboard["materials_notices"],
        xhs=dashboard["xhs"],
        ai_daily_reports=serialize_ai_daily_reports(load_cached_ai_daily_reports()),
        active_page="debug",
    )


@app.route("/bilibili")
def bilibili_page():
    return render_template(
        "bilibili.html",
        bilibili=load_bilibili_page_data(),
        active_page="bilibili",
    )


@app.route("/xhs")
def xhs_page():
    return render_template(
        "xhs.html",
        xhs=load_xhs_page_data(),
        active_page="xhs",
    )


@app.route("/materials-notices")
def materials_notices_page():
    return render_template(
        "materials_notices.html",
        materials_notices=load_materials_notices_page_data(),
        active_page="materials_notices",
    )


@app.route("/bilibili/refresh", methods=["POST"])
def refresh_bilibili():
    page_data = refresh_bilibili_page_data()
    if page_data["error"]:
        flash(page_data["error"], "error")
    else:
        flash("Bilibili 已更新。", "success")
    return redirect_back("bilibili_page")


@app.route("/xhs/refresh", methods=["POST"])
def refresh_xhs():
    page_data = refresh_xhs_page_data()
    if page_data["error"]:
        flash(page_data["error"], "error")
    else:
        flash("小红书已更新。", "success")
    return redirect_back("xhs_page")


@app.route("/materials-notices/refresh", methods=["POST"])
def refresh_materials_notices():
    page_data = refresh_materials_notices_page_data()
    if page_data["error"]:
        flash(page_data["error"], "error")
    else:
        flash("材料学院通知已更新。", "success")
    return redirect_back("materials_notices_page")


@app.route("/api/bilibili")
def bilibili_api():
    return jsonify(load_bilibili_page_data())


@app.route("/api/xhs")
def xhs_api():
    return jsonify(load_xhs_page_data())


@app.route("/api/materials-notices")
def materials_notices_api():
    return jsonify(load_materials_notices_page_data())


@app.route("/api/all")
def all_api():
    return jsonify(
        {
            "bilibili": load_bilibili_page_data(),
            "materials_notices": load_materials_notices_page_data(),
            "xhs": load_xhs_page_data(),
        }
    )


@app.route("/api/program/status")
def program_status_api():
    dashboard = load_dashboard_data()
    automation_settings = load_automation_settings()
    reports = serialize_ai_daily_reports(load_cached_ai_daily_reports())
    return jsonify(
        {
            "scheduler_running": automation_scheduler.is_running(),
            "automation": {
                "settings": serialize_automation_settings(automation_settings),
                "status": get_automation_status(automation_settings),
            },
            "bilibili": {
                "updated_at": dashboard["bilibili"]["updated_at"],
                "count": len(dashboard["bilibili"]["videos"]),
                "error": dashboard["bilibili"]["error"],
            },
            "materials_notices": {
                "updated_at": dashboard["materials_notices"]["updated_at"],
                "count": len(dashboard["materials_notices"]["notices"]),
                "error": dashboard["materials_notices"]["error"],
            },
            "xhs": {
                "updated_at": dashboard["xhs"]["updated_at"],
                "count": len(dashboard["xhs"]["notes"]),
                "error": dashboard["xhs"]["error"],
            },
            "ai_daily_reports": {
                "generated_at": reports["generated_at"],
                "count": reports["count"],
                "available": reports["available"],
            },
        }
    )


@app.route("/api/settings/notifications")
def notification_settings_api():
    settings = load_notification_settings()
    return jsonify(
        {
            "settings": serialize_notification_settings(settings),
            "status": get_notification_status(settings),
        }
    )


@app.route("/api/settings/automation")
def automation_settings_api():
    settings = load_automation_settings()
    return jsonify(
        {
            "settings": serialize_automation_settings(settings),
            "status": get_automation_status(settings),
            "scheduler_running": automation_scheduler.is_running(),
        }
    )


@app.route("/api/settings/llm")
def llm_settings_api():
    settings = load_llm_settings()
    return jsonify(
        {
            "settings": serialize_llm_settings(settings),
            "status": get_llm_status(settings),
            "models": load_models_cache(),
        }
    )


@app.route("/api/ai-daily-reports")
def ai_daily_reports_api():
    return jsonify(serialize_ai_daily_reports(load_cached_ai_daily_reports()))


@app.route("/settings/notifications", methods=["POST"])
def save_notifications():
    settings = NotificationSettings(
        bark_key=request.form.get("bark_key", "").strip(),
        telegram_bot_token=request.form.get("telegram_bot_token", "").strip(),
        telegram_chat_id=request.form.get("telegram_chat_id", "").strip(),
    )
    save_notification_settings(settings)
    flash("通知配置已保存。", "success")
    return redirect_back("notifications_page")


@app.route("/settings/automation", methods=["POST"])
def save_automation():
    current = load_automation_settings()
    settings = AutomationSettings(
        enabled=parse_bool(request.form.get("enabled"), False),
        hour=clamp_int(request.form.get("hour"), minimum=0, maximum=23, default=9),
        minute=clamp_int(request.form.get("minute"), minimum=0, maximum=59, default=0),
        push_summary_too=parse_bool(request.form.get("push_summary_too"), False),
        summary_channel=request.form.get("summary_channel", "all").strip(),
        summary_target=request.form.get("summary_target", "all").strip(),
        bark_completion=parse_bool(request.form.get("bark_completion"), False),
        last_attempt_at=current.last_attempt_at,
        last_success_at=current.last_success_at,
        last_status=current.last_status,
        last_error=current.last_error,
    )
    save_automation_settings(settings)
    automation_scheduler.start()
    flash("自动化配置已保存。", "success")
    return redirect_back("notifications_page")


@app.route("/dashboard/refresh-all", methods=["POST"])
def refresh_all_dashboard():
    try:
        dashboard = refresh_dashboard_data()
    except Exception as exc:  # noqa: BLE001
        flash(f"全量刷新失败：{exc}", "error")
    else:
        flash(
            (
                "全量刷新完成。"
                f" Bilibili {len(dashboard['bilibili']['videos'])} 条，"
                f"材料学院通知 {len(dashboard['materials_notices']['notices'])} 条，"
                f"小红书 {len(dashboard['xhs']['notes'])} 条。"
            ),
            "success",
        )
    return redirect_back("notifications_page")


@app.route("/settings/llm", methods=["POST"])
def save_llm():
    settings = LLMSettings(
        api_format=request.form.get("api_format", "openai").strip().lower() or "openai",
        base_url=request.form.get("base_url", "").strip(),
        api_key=request.form.get("api_key", "").strip(),
        model=request.form.get("model", "").strip(),
    )
    save_llm_settings(settings)
    flash("模型配置已保存。", "success")
    return redirect_back("llm_page")


@app.route("/llm/models/refresh", methods=["POST"])
def refresh_llm_models():
    settings = load_llm_settings()

    try:
        models = fetch_models(settings)
        save_models_cache(models)
    except Exception as exc:  # noqa: BLE001
        flash(f"获取模型列表失败：{exc}", "error")
    else:
        flash(f"模型列表刷新成功，共获取 {len(models)} 个模型。", "success")

    return redirect_back("llm_page")


@app.route("/llm/model/select", methods=["POST"])
def select_llm_model():
    selected_model = request.form.get("selected_model", "").strip()
    settings = load_llm_settings()

    if not selected_model:
        flash("请选择一个模型。", "error")
        return redirect_back("llm_page")

    settings.model = selected_model
    save_llm_settings(settings)
    flash(f"当前使用模型已更新为 {selected_model}。", "success")
    return redirect_back("llm_page")


@app.route("/notify/test", methods=["POST"])
def notify_test():
    channel = request.form.get("channel", "all").strip()
    settings = load_notification_settings()
    title = "内容摘要看板测试通知"
    body = f"通知测试成功，发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    try:
        results = send_notification(settings, channel, title, body)
    except Exception as exc:  # noqa: BLE001
        flash(f"测试通知失败：{exc}", "error")
    else:
        flash(" ".join(results), "success")

    return redirect_back("notifications_page")


@app.route("/notify/send", methods=["POST"])
def notify_send():
    channel = request.form.get("channel", "all").strip()
    target = request.form.get("target", "all").strip()
    settings = load_notification_settings()
    dashboard = load_dashboard_data()

    try:
        title, body, state_updates = build_notify_payload(target, dashboard)
        results = send_notification(settings, channel, title, body)
    except Exception as exc:  # noqa: BLE001
        flash(f"推送失败：{exc}", "error")
    else:
        for platform, signature in state_updates.items():
            if signature:
                set_delivery_signature("summary", platform, signature)
        flash(" ".join(results), "success")

    return redirect_back("notifications_page")


@app.route("/ai-daily-reports/generate", methods=["POST"])
def generate_ai_daily_report():
    llm_settings = load_llm_settings()
    dashboard = load_dashboard_data()

    try:
        if not llm_settings.base_url or not llm_settings.api_key or not llm_settings.model:
            raise ValueError("LLM base URL、API key 或 model 未配置完整。")

        reports = build_ai_daily_reports(llm_settings, dashboard)
        save_ai_daily_reports(reports)
    except Exception as exc:  # noqa: BLE001
        flash(f"AI 日报生成失败：{exc}", "error")
    else:
        flash(f"AI 日报生成完成，已缓存 {len(reports)} 份日报。", "success")

    return redirect_back("notifications_page")


@app.route("/ai-daily-reports/push", methods=["POST"])
def push_ai_daily_report():
    notification_settings = load_notification_settings()
    cache = load_cached_ai_daily_reports()
    if parse_item_date(cache.get("generated_at")) != get_today():
        flash("当前缓存的 AI 日报不是今天生成的，请先重新生成。", "error")
        return redirect_back("notifications_page")
    messages = build_ai_daily_report_messages(cache.get("reports", []))

    try:
        if not notification_settings.telegram_bot_token or not notification_settings.telegram_chat_id:
            raise ValueError("Telegram bot token or chat id is not configured.")
        if not messages:
            raise ValueError("还没有已生成的 AI 日报，请先执行生成。")

        results = send_telegram_messages(notification_settings, messages)
    except Exception as exc:  # noqa: BLE001
        flash(f"AI 日报推送失败：{exc}", "error")
    else:
        for message in cache.get("reports", []):
            if (
                str(message.get("platform_name", "")).strip() == "小红书"
                and str(message.get("content_signature", "")).strip()
            ):
                set_delivery_signature("report", "xhs", str(message["content_signature"]).strip())
        if notification_settings.bark_key:
            try:
                bark_result = send_bark_notification(
                    notification_settings,
                    "AI 日报推送完成",
                    (
                        f"已通过 Telegram 推送 {len(messages)} 份日报，"
                        f"完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                flash(f"{' '.join(results)} Bark 完成通知发送失败：{exc}", "error")
            else:
                results.append(bark_result)
                flash(" ".join(results), "success")
        else:
            flash(" ".join(results), "success")

    return redirect_back("notifications_page")


@app.route("/automation/run", methods=["POST"])
def run_automation_now():
    try:
        result = run_automation_job()
    except Exception as exc:  # noqa: BLE001
        flash(f"自动任务执行失败：{exc}", "error")
    else:
        flash(
            (
                "自动任务执行完成。"
                f" Bilibili {result['bilibili_count']} 条，"
                f"材料学院通知 {result['materials_count']} 条，"
                f"小红书 {result['xhs_count']} 条，"
                f"日报 {result['report_count']} 份。"
            ),
            "success",
        )
    return redirect_back("notifications_page")


@app.route("/pipeline/run", methods=["POST"])
def run_pipeline_now():
    try:
        result = run_full_pipeline(
            push_summary_too=False,
            summary_channel="all",
            summary_target="all",
            bark_completion=True,
        )
    except Exception as exc:  # noqa: BLE001
        flash(f"完整流程执行失败：{exc}", "error")
    else:
        flash(
            (
                "完整流程执行完成。"
                f" Bilibili {result['bilibili_count']} 条，"
                f"材料学院通知 {result['materials_count']} 条，"
                f"小红书 {result['xhs_count']} 条，"
                f"日报 {result['report_count']} 份，"
                f"已推送 {result['pushed_report_count']} 份日报。"
            ),
            "success",
        )
    return redirect_back("notifications_page")


if __name__ == "__main__":
    debug = True
    if not debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        ensure_automation_scheduler()
    app.run(
        debug=debug,
        host=get_host("APP_HOST", "127.0.0.1"),
        port=get_port("APP_PORT", 8000),
    )
