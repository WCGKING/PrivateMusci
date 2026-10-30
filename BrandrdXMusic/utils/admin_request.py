
import logging

from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.errors import (
    ChatAdminRequired,
    FloodWait,
    RPCError,
    UserIsBlocked,
    PeerIdInvalid,
)

from BrandrdXMusic import app

LOGGER = logging.getLogger(__name__)

# Avoid repeated requests in the same running process
_REQUESTED_CHATS = set()


async def check_admin_and_request(message):
    """
    Returns True if the bot is admin.
    Returns False if it isn't admin and a request was sent.
    """
    chat_id = message.chat.id

    try:
        bot = await app.get_me()
        member = await app.get_chat_member(chat_id, bot.id)

        if member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        ):
            return True

        if chat_id in _REQUESTED_CHATS:
            return False

        _REQUESTED_CHATS.add(chat_id)

        group_text = (
            "⚠️ **Admin Permission Required**\n\n"
            "Mujhe music play karne ke liye Admin banayein. 🎵\n"
            "Please promote me to Admin, then try your command again."
        )

        # Try to notify the group owner privately
        owner_name = "Group Owner"
        try:
            async for member in app.get_chat_members(
                chat_id,
                filter=ChatMembersFilter.ADMINISTRATORS,
            ):
                if member.status == ChatMemberStatus.OWNER:
                    owner = member.user
                    owner_name = owner.first_name or owner_name

                    await app.send_message(
                        owner.id,
                        f"⚠️ Admin request for **{message.chat.title}**\n\n"
                        "Please make the BrandrdXMusic bot an Admin "
                        "so it can manage music playback."
                    )
                    break
        except (RPCError, UserIsBlocked, PeerIdInvalid):
            LOGGER.info(
                "Could not privately notify the owner of %s",
                chat_id,
            )

        # Always try to notify the group
        await message.reply_text(group_text)

        return False

    except FloodWait as exc:
        LOGGER.warning("Telegram FloodWait: %s seconds", exc.value)
        return False
    except (ChatAdminRequired, RPCError) as exc:
        LOGGER.warning("Admin check failed in %s: %s", chat_id, exc)
        try:
            await message.reply_text(
                "⚠️ I couldn't verify my Admin status. "
                "Please check my permissions."
            )
        except RPCError:
            pass
        return False
