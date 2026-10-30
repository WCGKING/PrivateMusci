import asyncio

from pyrogram.enums import ChatMemberStatus, ChatMembersFilter, ParseMode
from pyrogram.errors import FloodWait

from BrandrdXMusic import app

_REQUESTED_CHATS = set()


async def safe_reply(message, text):
    formatted_text = f"<b><blockquote>{text}</blockquote></b>"

    try:
        await message.reply_text(
            formatted_text,
            parse_mode=ParseMode.HTML,
        )
        return True

    except FloodWait as exc:
        await asyncio.sleep(exc.value + 1)

        try:
            await message.reply_text(
                formatted_text,
                parse_mode=ParseMode.HTML,
            )
            return True
        except Exception:
            return False

    except Exception:
        return False


async def notify_owner(message):
    chat_id = message.chat.id

    try:
        async for member in app.get_chat_members(
            chat_id,
            filter=ChatMembersFilter.ADMINISTRATORS,
        ):
            if member.status == ChatMemberStatus.OWNER:
                owner = member.user

                try:
                    await app.send_message(
                        owner.id,
                        (
                            "<b><blockquote>"
                            "⚠️ Admin Request\n\n"
                            f"Group: {message.chat.title or 'Unknown'}\n"
                            f"Group ID: <code>{chat_id}</code>\n\n"
                            "Please make the BrandrdXMusic bot an "
                            "Admin to enable music playback. 🎵"
                            "</blockquote></b>"
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                    return True

                except Exception:
                    return False

    except Exception:
        return False

    return False


async def check_admin_and_request(message):
    chat_id = message.chat.id

    try:
        bot = await app.get_me()

        member = await app.get_chat_member(
            chat_id,
            bot.id,
        )

        if member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            _REQUESTED_CHATS.discard(chat_id)
            return True

    except FloodWait as exc:
        await asyncio.sleep(exc.value + 1)
        return False

    except Exception:
        await safe_reply(
            message,
            (
                "⚠️ I couldn't verify my Admin status.\n\n"
                "Please check my group permissions."
            ),
        )
        return False

    if chat_id in _REQUESTED_CHATS:
        return False

    group_text = (
        "⚠️ Admin Permission Required\n\n"
        "Mujhe music play karne ke liye Admin banayein. 🎵\n\n"
        "Please promote me to Admin, then try your command again."
    )

    sent = await safe_reply(message, group_text)

    await notify_owner(message)

    if sent:
        _REQUESTED_CHATS.add(chat_id)

    return False
4v
