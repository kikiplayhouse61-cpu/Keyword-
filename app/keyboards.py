from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Dict, Any


def main_dashboard_keyboard(monitoring_active: bool) -> InlineKeyboardMarkup:
    start_stop = "⏹ STOP" if monitoring_active else "▶️ START"
    start_stop_data = "action:stop" if monitoring_active else "action:start"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(start_stop, callback_data=start_stop_data),
            InlineKeyboardButton("🔄 Refresh", callback_data="action:refresh"),
        ],
        [
            InlineKeyboardButton("➕ Add Keyword", callback_data="action:add_keyword"),
            InlineKeyboardButton("➖ Remove Keyword", callback_data="action:remove_keyword"),
        ],
        [
            InlineKeyboardButton("🔑 My Keywords", callback_data="action:keywords:0"),
            InlineKeyboardButton("👥 My Groups", callback_data="action:groups:0"),
        ],
        [
            InlineKeyboardButton("📜 Alert History", callback_data="action:history:0"),
            InlineKeyboardButton("📊 Statistics", callback_data="action:stats"),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="action:settings"),
        ],
    ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="action:dashboard")]
    ])


def keywords_keyboard(keywords: List[Dict[str, Any]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for kw in keywords:
        status = "🟢" if kw["enabled"] else "🔴"
        rows.append([
            InlineKeyboardButton(
                f"{status} {kw['keyword']}",
                callback_data=f"kw:toggle:{kw['id']}"
            )
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"action:keywords:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"action:keywords:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="action:dashboard")])
    return InlineKeyboardMarkup(rows)


def remove_keywords_keyboard(keywords: List[Dict[str, Any]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for kw in keywords:
        rows.append([
            InlineKeyboardButton(
                f"❌ {kw['keyword']}",
                callback_data=f"kw:delete:{kw['id']}"
            )
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"action:remove_keyword_page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"action:remove_keyword_page:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="action:dashboard")])
    return InlineKeyboardMarkup(rows)


def groups_keyboard(groups: List[Dict[str, Any]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for g in groups:
        name = g["group_name"][:30]
        rows.append([InlineKeyboardButton(f"👥 {name}", callback_data=f"grp:info:{g['group_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"action:groups:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"action:groups:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="action:dashboard")])
    return InlineKeyboardMarkup(rows)


def history_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"action:history:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️ Next", callback_data=f"action:history:{page + 1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="action:dashboard")])
    return InlineKeyboardMarkup(rows)


def settings_keyboard(notif_enabled: bool) -> InlineKeyboardMarkup:
    notif_label = "🔕 Disable Notifications" if notif_enabled else "🔔 Enable Notifications"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(notif_label, callback_data="settings:toggle_notif")],
        [InlineKeyboardButton("🗑 Clear Alert History", callback_data="settings:clear_history")],
        [InlineKeyboardButton("🔄 Reload Groups", callback_data="settings:reload_groups")],
        [InlineKeyboardButton("🔙 Back", callback_data="action:dashboard")],
    ])


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm:yes:{action}"),
            InlineKeyboardButton("❌ No", callback_data="action:dashboard"),
        ]
    ])
