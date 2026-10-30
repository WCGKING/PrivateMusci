import asyncio
import logging

from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.errors import FloodWait, RPCError

from BrandrdXMusic import app

LOGGER = logging.getLogger(__name__)

_REQUESTED_CHATS = set()


async def safe_reply(message, text):
    try:
        LOGGER.info(
            "ADMIN REQUEST: Sending group message to %s",
            message.chat.id,
        )

        sent_message = await message.reply_text(text)

        LOGGER.info(
            "ADMIN REQUEST: Group message sent successfully. Message ID: %s",
            sent_message.id,
        )
        return True

    except FloodWait as exc:
        LOGGER.warning(
            "ADMIN REQUEST: Group FloodWait: %s seconds",
            exc.value,
        )

        await asyncio.sleep(exc.value + 1)

        try:
            sent_message = await message.reply_text(text)

            LOGGER.info(
                "ADMIN REQUEST: Group message sent after retry. ID: %s",
                sent_message.id,
            )
            return True

        except Exception:
            LOGGER.exception(
                "ADMIN REQUEST: Group message retry failed"
            )
            return False

    except Exception:
        LOGGER.exception(
            "ADMIN REQUEST: Could not send group message"
        )
        return False


async def notify_owner(message):
    chat_id = message.chat.id

    LOGGER.info(
        "ADMIN REQUEST: Searching group owner in %s",
        chat_id,
    )

    try:
        async for member in app.get_chat_members(
            chat_id,
            filter=ChatMembersFilter.ADMINISTRATORS,
        ):
            if member.status == ChatMemberStatus.OWNER:
                owner = member.user

                LOGGER.info(
                    "ADMIN REQUEST: Owner found: %s",
                    owner.id,
                )

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

                    LOGGER.info(
                        "ADMIN REQUEST: Private message sent to owner %s",
                        owner.id,
                    )
                    return True

                except Exception:
                    LOGGER.exception(
                        "ADMIN REQUEST: Could not DM owner %s",
                        owner.id,
                    )
                    return False

        LOGGER.warning(
            "ADMIN REQUEST: Group owner not found in %s",
            chat_id,
        )

    except Exception:
        LOGGER.exception(
            "ADMIN REQUEST: Could not search group administrators"
        )

    return False


async def check_admin_and_request(message):
    chat_id = message.chat.id

    LOGGER.info(
        "ADMIN REQUEST: Function called in chat %s",
        chat_id,
    )

    try:
        bot = await app.get_me()

        LOGGER.info(
            "ADMIN REQUEST: Checking bot %s in chat %s",
            bot.id,
            chat_id,
        )

        member = await app.get_chat_member(
            chat_id,
            bot.id,
        )

        LOGGER.info(
            "ADMIN REQUEST: Current bot status: %s",
            member.status,
        )

        if member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            LOGGER.info(
                "ADMIN REQUEST: Bot is already admin in %s",
                chat_id,
            )

            _REQUESTED_CHATS.discard(chat_id)
            return True

    except FloodWait as exc:
        LOGGER.warning(
            "ADMIN REQUEST: Admin check FloodWait: %s seconds",
            exc.value,
        )

        await asyncio.sleep(exc.value + 1)
        return False

    except Exception:
        LOGGER.exception(
            "ADMIN REQUEST: Failed to check bot status in %s",
            chat_id,
        )

        await safe_reply(
            message,
            (
                "⚠️ I couldn't verify my Admin status.\n\n"
                "Please check my group permissions."
            ),
        )
        return False

    if chat_id in _REQUESTED_CHATS:
        LOGGER.info(
            "ADMIN REQUEST: Request already sent for %s",
            chat_id,
        )
        return False

    group_text = (
        "⚠️ **Admin Permission Required**\n\n"
        "Mujhe music play karne ke liye Admin banayein. 🎵\n\n"
        "Please promote me to Admin, then try your command again."
    )

    LOGGER.info(
        "ADMIN REQUEST: Bot is not admin. Sending notifications."
    )

    # First send the group notification.
    sent = await safe_reply(
        message,
        group_text,
    )

    # Then try to notify the group owner privately.
    await notify_owner(message)

    if sent:
        _REQUESTED_CHATS.add(chat_id)

    LOGGER.info(
        "ADMIN REQUEST: Finished for chat %s. Group sent: %s",
        chat_id,
        sent,
    )

    return False
