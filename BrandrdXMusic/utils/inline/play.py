import math

from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton

from BrandrdXMusic.utils.database import is_autoplay
from BrandrdXMusic.utils.formatters import time_to_seconds


COLORS = (
    ButtonStyle.PRIMARY,
    ButtonStyle.SUCCESS,
    ButtonStyle.DANGER,
)


# ============================================================
# Track Markup
# ============================================================

def track_markup(_, videoid, user_id, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text=_["P_B_1"],
                callback_data=f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text=_["P_B_2"],
                callback_data=f"MusicStream {videoid}|{user_id}|v|{channel}|{fplay}",
                style=COLORS[1],
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {videoid}|{user_id}",
                style=COLORS[2],
            )
        ],
    ]


# ============================================================
# Autoplay Markup
# ============================================================

def autoplay_markup(chat_id, mode=None):
    if mode is True:
        text = "🟢 Autoplay: ON"
        style = COLORS[1]
    elif mode is False:
        text = "🔴 Autoplay: OFF"
        style = COLORS[2]
    else:
        text = "🔁 Autoplay: ON/OFF"
        style = COLORS[0]

    return [
        InlineKeyboardButton(
            text=text,
            callback_data=f"autoplay {chat_id}",
            style=style,
        )
    ]


# ============================================================
# Stream Timer Markup
# ============================================================

def stream_markup_timer(_, vidid, chat_id, played, dur):
    played_sec = time_to_seconds(played) or 0
    duration_sec = time_to_seconds(dur) or 1

    percentage = max(
        0,
        min(100, (played_sec / duration_sec) * 100),
    )

    # Ten-step progress bar
    position = min(9, int(percentage // 10))
    bar = "—" * position + "▷" + "—" * (9 - position)

    return [
        [
            InlineKeyboardButton(
                text=f"{played} {bar} {dur}",
                callback_data="GetTimer",
                style=COLORS[0],
            )
        ],
        [
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"ADMIN Resume|{chat_id}",
                style=COLORS[1],
            ),
            InlineKeyboardButton(
                text="⏸️",
                callback_data=f"ADMIN Pause|{chat_id}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text="🔄",
                callback_data=f"ADMIN Replay|{chat_id}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text="⏭️",
                callback_data=f"ADMIN Skip|{chat_id}",
                style=COLORS[1],
            ),
            InlineKeyboardButton(
                text="⏹️",
                callback_data=f"ADMIN Stop|{chat_id}",
                style=COLORS[2],
            ),
        ],
        autoplay_markup(chat_id),
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
                style=COLORS[2],
            )
        ],
    ]


# ============================================================
# Normal Stream Markup
# ============================================================

def stream_markup(_, videoid, chat_id):
    return [
        [
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"ADMIN Resume|{chat_id}",
                style=COLORS[1],
            ),
            InlineKeyboardButton(
                text="⏸️",
                callback_data=f"ADMIN Pause|{chat_id}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text="🔄",
                callback_data=f"ADMIN Replay|{chat_id}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text="⏭️",
                callback_data=f"ADMIN Skip|{chat_id}",
                style=COLORS[1],
            ),
            InlineKeyboardButton(
                text="⏹️",
                callback_data=f"ADMIN Stop|{chat_id}",
                style=COLORS[2],
            ),
        ],
        autoplay_markup(chat_id),
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data="close",
                style=COLORS[2],
            )
        ],
    ]


# ============================================================
# Compatibility Function
# ============================================================

def stream_markup2(_, videoid, chat_id):
    return stream_markup(_, videoid, chat_id)


# ============================================================
# Playlist Markup
# ============================================================

def playlist_markup(_, videoid, user_id, ptype, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text=_["P_B_1"],
                callback_data=f"Playlists {videoid}|{user_id}|{ptype}|a|{channel}|{fplay}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text=_["P_B_2"],
                callback_data=f"Playlists {videoid}|{user_id}|{ptype}|v|{channel}|{fplay}",
                style=COLORS[1],
            ),
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {videoid}|{user_id}",
                style=COLORS[2],
            )
        ],
    ]


# ============================================================
# Livestream Markup
# ============================================================

def livestream_markup(_, videoid, user_id, mode, channel, fplay):
    return [
        [
            InlineKeyboardButton(
                text=_["P_B_3"],
                callback_data=f"LiveStream {videoid}|{user_id}|{mode}|{channel}|{fplay}",
                style=COLORS[1],
            )
        ],
        [
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {videoid}|{user_id}",
                style=COLORS[2],
            )
        ],
    ]


# ============================================================
# Slider Markup
# ============================================================

def slider_markup(_, videoid, user_id, query, query_type, channel, fplay):
    query = str(query)[:20]

    return [
        [
            InlineKeyboardButton(
                text=_["P_B_1"],
                callback_data=f"MusicStream {videoid}|{user_id}|a|{channel}|{fplay}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text=_["P_B_2"],
                callback_data=f"MusicStream {videoid}|{user_id}|v|{channel}|{fplay}",
                style=COLORS[1],
            ),
        ],
        [
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"slider B|{query_type}|{query}|{user_id}|{channel}|{fplay}",
                style=COLORS[0],
            ),
            InlineKeyboardButton(
                text=_["CLOSE_BUTTON"],
                callback_data=f"forceclose {videoid}|{user_id}",
                style=COLORS[2],
            ),
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"slider F|{query_type}|{query}|{user_id}|{channel}|{fplay}",
                style=COLORS[1],
            ),
        ],
    ]
