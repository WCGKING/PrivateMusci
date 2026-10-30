import asyncio
import logging

from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.errors import FloodWait, RPCError

from BrandrdXMusic import app

LOGGER = logging.getLogger(__name__)

_REQUESTED_CHATS = set()


async def safe_reply(message, text):
    try:
        await message.reply_text(text)
        return True

    except FloodWait as exc:
        LOGGER.warning("Group message FloodWait: %s", exc.value)
        await asyncio.sleep(exc.value + 1)

        try:
            await message.reply_text(text)
            return True
        except Exception:
            LOGGER.exception("Group notification retry failed")
            return False

    except Exception:
        LOGGER.exception("Could not send group notification")
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
                            "⚠️ **Admin Request**\n\n"
                            f"Group: **{message.chat.title or 'Unknown'}**\n"
                            f"Group ID: `{chat_id}`\n\n"
                            "Please make the BrandrdXMusic bot an "
                            "Admin to enable music playback. 🎵"
                        ),
                    )
                    LOGGER.info("Owner notification sent for %s", chat_id)
                    return True

                except Exception:
                    LOGGER.exception(
                        "Could not DM group owner for %s",
                        chat_id,
                    )
                    return False

    except Exception:
        LOGGER.exception("Could not find group owner for %s", chat_id)

    return False


async def check_admin_and_request(message):
    chat_id = message.chat.id

    try:
        bot = await app.get_me()
        member = await app.get_chat_member(chat_id, bot.id)

        if member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            _REQUESTED_CHATS.discard(chat_id)
            return True

    except FloodWait as exc:
        LOGGER.warning("Admin check FloodWait: %s", exc.value)
        await asyncio.sleep(exc.value + 1)
        return False

    except Exception:
        LOGGER.exception("Could not check bot admin status in %s", chat_id)
        await safe_reply(
            message,
            "⚠️ I couldn't verify my Admin status. "
            "Please check my group permissions.",
        )
        return False

    if chat_id in _REQUESTED_CHATS:
        return False

    group_text = (
        "⚠️ **Admin Permission Required**\n\n"
        "Mujhe music play karne ke liye Admin banayein. 🎵\n\n"
        "Please promote me to Admin, then try your command again."
    )

    # Group notification is attempted independently of owner DM.
    sent = await safe_reply(message, group_text)

    # Owner DM is attempted separately.
    await notify_owner(message)

    if sent:
        _REQUESTED_CHATS.add(chat_id)

    return False
