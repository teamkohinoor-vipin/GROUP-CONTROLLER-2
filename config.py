import os
import random
from typing import List

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set.")

START_IMAGES: List[str] = [
    "https://i.ibb.co/WjSVjw2",
    "https://i.ibb.co/Nn6CcSHw",
    "https://i.ibb.co/7dqjmGvs",
    "https://i.ibb.co/rK7bXx5L",
    "https://i.ibb.co/k6qZk7mg",
    "https://i.ibb.co/8LGHn6Fp",
    "https://i.ibb.co/q3sfj6vZ",
    "https://i.ibb.co/XrvznYh8",
]

DB_PATH = "data/bot.db"
os.makedirs("data", exist_ok=True)

DEFAULT_GROUP_SETTINGS = {
    "flood_limit": 5,
    "flood_action": "mute",
    "flood_mute_duration": 3600,
    "caps_limit": 10,
    "caps_action": "delete",
    "emoji_limit": 15,
    "emoji_action": "delete",
    "mention_limit": 5,
    "mention_action": "delete",
    "warn_limit": 3,
    "warn_action": "mute",
    "warn_mute_duration": 86400,
    "link_block_enabled": False,
    "link_allowed_only": False,
    "media_settings": {
        "text": "off",
        "photo": "off",
        "video": "off",
        "gif": "off",
        "sticker": "off",
        "voice": "off",
        "audio": "off",
        "file": "off",
        "emoji": "off",
        "premium_emoji": "off",
        "album": "off",
    },
    "min_message_length": 1,
    "max_message_length": 4096,
    "length_action": "delete",
}
