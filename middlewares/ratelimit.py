from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message) and event.chat.type in ["group", "supergroup"]:
            db = data.get("db")
            user_id = event.from_user.id
            chat_id = event.chat.id

            if await db.is_banned(user_id, chat_id):
                try:
                    await event.delete()
                except:
                    pass
                return

            if await db.is_muted(user_id, chat_id):
                try:
                    await event.delete()
                except:
                    pass
                return

            try:
                member = await event.bot.get_chat_member(chat_id, user_id)
                data["is_admin"] = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
                data["is_owner"] = member.status == ChatMemberStatus.CREATOR
            except TelegramBadRequest:
                data["is_admin"] = False
                data["is_owner"] = False

        return await handler(event, data)
