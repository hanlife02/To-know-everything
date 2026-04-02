from __future__ import annotations

from datetime import datetime

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from bilibili.web import load_page_data as load_bilibili_page_data
from notifications import (
    NotificationSettings,
    build_combined_digest,
    build_platform_digest,
    get_notification_status,
    load_notification_settings,
    save_notification_settings,
    send_notification,
    serialize_notification_settings,
)
from xhs.web import load_page_data as load_xhs_page_data

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "content-digest-dashboard"


def load_dashboard_data() -> dict:
    return {
        "bilibili": load_bilibili_page_data(),
        "xhs": load_xhs_page_data(),
    }


def build_notify_payload(target: str, dashboard: dict) -> tuple[str, str]:
    if target == "bilibili":
        bilibili = dashboard["bilibili"]
        return build_platform_digest("Bilibili", bilibili["overview"], bilibili["videos"])
    if target == "xhs":
        xhs = dashboard["xhs"]
        return build_platform_digest("小红书", xhs["overview"], xhs["notes"])
    if target == "all":
        return build_combined_digest(dashboard["bilibili"], dashboard["xhs"])
    raise ValueError(f"Unsupported notification target: {target}")


@app.route("/")
def index():
    dashboard = load_dashboard_data()
    settings = load_notification_settings()
    return render_template(
        "index.html",
        bilibili=dashboard["bilibili"],
        xhs=dashboard["xhs"],
        notification_settings=serialize_notification_settings(settings),
        notification_status=get_notification_status(settings),
    )


@app.route("/api/bilibili")
def bilibili_api():
    return jsonify(load_bilibili_page_data())


@app.route("/api/xhs")
def xhs_api():
    return jsonify(load_xhs_page_data())


@app.route("/api/all")
def all_api():
    return jsonify(
        {
            "bilibili": load_bilibili_page_data(),
            "xhs": load_xhs_page_data(),
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


@app.route("/settings/notifications", methods=["POST"])
def save_notifications():
    settings = NotificationSettings(
        bark_key=request.form.get("bark_key", "").strip(),
        telegram_bot_token=request.form.get("telegram_bot_token", "").strip(),
        telegram_chat_id=request.form.get("telegram_chat_id", "").strip(),
    )
    save_notification_settings(settings)
    flash("通知配置已保存。", "success")
    return redirect(url_for("index"))


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

    return redirect(url_for("index"))


@app.route("/notify/send", methods=["POST"])
def notify_send():
    channel = request.form.get("channel", "all").strip()
    target = request.form.get("target", "all").strip()
    settings = load_notification_settings()
    dashboard = load_dashboard_data()

    try:
        title, body = build_notify_payload(target, dashboard)
        results = send_notification(settings, channel, title, body)
    except Exception as exc:  # noqa: BLE001
        flash(f"推送失败：{exc}", "error")
    else:
        flash(" ".join(results), "success")

    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8000)
