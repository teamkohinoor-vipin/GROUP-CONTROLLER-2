import time
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message
from collections import defaultdict

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, time_window: int = 5, max_messages: int = 5):
        self.time_window = time_window
        self.max_messages = max_messages
        self.user_message_times = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if not event.chat or event.chat.type not in ["group", "supergroup"]:
            return await handler(event, data)

        user_id = event.from_user.id
        chat_id = event.chat.id
        key = (chat_id, user_id)
        now = time.time()

        self.user_message_times[key] = [t for t in self.user_message_times[key] if now - t < self.time_window]

        if len(self.user_message_times[key]) >= self.max_messages:
            db: Database = data.get("db")
            settings = await db.get_group_settings(chat_id)
            action = settings.get("flood_action", "mute")
            duration = settings.get("flood_mute_duration", 3600)

            try:
                if action == "mute":
                    await event.chat.restrict(user_id, permissions={"can_send_messages": False}, until_date=now+duration)
                    await db.mute_user(user_id, chat_id, duration)
                    await db.add_log(chat_id, "flood_mute", user_id, details=f"Flood muted for {duration}s")
                elif action == "kick":
                    await event.chat.ban(user_id)
                    await event.chat.unban(user_id)
                    await db.add_log(chat_id, "flood_kick", user_id)
                elif action == "ban":
                    await event.chat.ban(user_id)
                    await db.ban_user(user_id, chat_id, 0)
                    await db.add_log(chat_id, "flood_ban", user_id)
                await event.delete()
            except:
                pass
            return

        self.user_message_times[key].append(now)
        return await handler(event, data)
