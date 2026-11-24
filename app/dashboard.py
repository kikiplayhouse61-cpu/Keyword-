from typing import Optional
from app import database as db
from app.utils import format_time, now_local


async def build_dashboard_text(monitoring_active: bool) -> str:
    keywords = await db.get_all_keywords()
    active_kw_count = sum(1 for k in keywords if k["enabled"])
    groups = await db.get_all_groups()
    total_alerts = await db.get_total_alert_count()
    status = "🟢 RUNNING" if monitoring_active else "🔴 PAUSED"

    return (
        f"🤖 *GC KEYWORD ALERT*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Welcome to your control panel\\!\n\n"
        f"📡 *Monitoring:* {status}\n"
        f"👥 *Groups monitored:* `{len(groups)}`\n"
        f"🔑 *Active keywords:* `{active_kw_count}`\n"
        f"🔔 *Total alerts:* `{total_alerts}`\n"
        f"🕒 *Updated:* `{format_time(now_local())}`"
    )


async def build_keywords_text(page: int = 0, page_size: int = 10) -> tuple:
    """Returns (text, keywords_on_page, total_pages, current_page)."""
    from app.utils import paginate
    all_kw = await db.get_all_keywords()
    page_kw, total_pages, page = paginate(all_kw, page, page_size)

    if not all_kw:
        return "🔑 *My Keywords*\n\nNo keywords added yet\\. Use ➕ Add Keyword to get started\\.", [], 1, 0

    lines = [f"🔑 *My Keywords* \\(Page {page + 1}/{total_pages}\\)\n"]
    for kw in page_kw:
        status = "🟢" if kw["enabled"] else "🔴"
        lines.append(f"{status} `{kw['keyword']}`")
    return "\n".join(lines), page_kw, total_pages, page


async def build_groups_text(page: int = 0, page_size: int = 10) -> tuple:
    from app.utils import paginate
    all_groups = await db.get_all_groups()
    page_groups, total_pages, page = paginate(all_groups, page, page_size)

    if not all_groups:
        return "👥 *My Groups*\n\nNo groups found yet\\. Groups appear automatically when messages arrive\\.", [], 1, 0

    lines = [f"👥 *My Groups* \\(Page {page + 1}/{total_pages}\\)\n"]
    for g in page_groups:
        name = g["group_name"].replace("_", "\\_").replace("*", "\\*")
        lines.append(f"• {name} \\(`{g['group_id']}`\\)")
    return "\n".join(lines), page_groups, total_pages, page


async def build_history_text(page: int = 0, page_size: int = 5) -> tuple:
    total = await db.get_total_alert_count()
    import math
    total_pages = max(1, math.ceil(total / page_size))
    page = max(0, min(page, total_pages - 1))
    alerts = await db.get_alert_history(limit=page_size, offset=page * page_size)

    if not alerts:
        return "📜 *Alert History*\n\nNo alerts recorded yet\\.", [], 1, 0

    lines = [f"📜 *Alert History* \\(Page {page + 1}/{total_pages}\\)\n"]
    for a in alerts:
        kw = (a.get("keyword") or "").replace("_", "\\_")
        sender = (a.get("sender_name") or "Unknown").replace("_", "\\_")
        group = (a.get("group_name") or "Unknown").replace("_", "\\_")
        lines.append(
            f"🔑 `{kw}` — 👤 {sender}\n"
            f"   👥 {group} | 🕒 `{a.get('alerted_at', '')}`\n"
        )
    return "\n".join(lines), alerts, total_pages, page


async def build_stats_text() -> str:
    keywords = await db.get_all_keywords()
    groups = await db.get_all_groups()
    total_alerts = await db.get_total_alert_count()
    today_alerts = await db.get_alert_count_today()
    top_kw = await db.get_top_keywords(5)

    top_lines = ""
    for i, t in enumerate(top_kw, 1):
        kw = t["keyword"].replace("_", "\\_")
        top_lines += f"  {i}\\. `{kw}` — {t['hits']} hits\n"

    if not top_lines:
        top_lines = "  _No data yet_\n"

    return (
        f"📊 *Statistics*\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👥 Total groups: `{len(groups)}`\n"
        f"🔑 Total keywords: `{len(keywords)}`\n"
        f"🔔 Total alerts: `{total_alerts}`\n"
        f"📅 Alerts today: `{today_alerts}`\n\n"
        f"🏆 *Top Keywords:*\n{top_lines}"
    )


async def build_settings_text() -> str:
    notif = await db.get_setting("notifications_enabled", "1")
    status = "🔔 Enabled" if notif == "1" else "🔕 Disabled"
    return (
        f"⚙️ *Settings*\n"
        f"━━━━━━━━━━━━━\n"
        f"Notifications: {status}\n"
    )
