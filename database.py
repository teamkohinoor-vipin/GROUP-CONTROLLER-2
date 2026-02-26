import aiosqlite
import json
import time
from typing import Optional, List, Dict, Any
from config import DB_PATH, DEFAULT_GROUP_SETTINGS

class Database:
    def __init__(self):
        self.conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        self.conn = await aiosqlite.connect(DB_PATH)
        await self.conn.execute("PRAGMA foreign_keys = ON")

        # Groups
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                title TEXT,
                settings TEXT NOT NULL DEFAULT '{}',
                created_at INTEGER NOT NULL
            )
        """)

        # Users
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at INTEGER NOT NULL
            )
        """)

        # Warnings
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                reason TEXT,
                admin_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        # Mutes
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                until INTEGER NOT NULL,
                PRIMARY KEY (user_id, group_id)
            )
        """)

        # Bans
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bans (
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                until INTEGER NOT NULL,
                PRIMARY KEY (user_id, group_id)
            )
        """)

        # Media settings
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS media_settings (
                group_id INTEGER NOT NULL,
                media_type TEXT NOT NULL,
                action TEXT NOT NULL,
                PRIMARY KEY (group_id, media_type)
            )
        """)

        # Link settings
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS link_settings (
                group_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                action TEXT NOT NULL,
                PRIMARY KEY (group_id, domain)
            )
        """)

        # Banned words
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS banned_words (
                group_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                PRIMARY KEY (group_id, word)
            )
        """)

        # Stats
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                group_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                messages INTEGER DEFAULT 0,
                PRIMARY KEY (group_id, date)
            )
        """)

        # Logs
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                user_id INTEGER,
                admin_id INTEGER,
                details TEXT,
                created_at INTEGER NOT NULL
            )
        """)

        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    # ---------- Group methods ----------
    async def get_group_settings(self, group_id: int) -> Dict[str, Any]:
        async with self.conn.execute("SELECT settings FROM groups WHERE group_id = ?", (group_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            return json.loads(row[0])
        else:
            settings = DEFAULT_GROUP_SETTINGS.copy()
            await self.conn.execute(
                "INSERT INTO groups (group_id, title, settings, created_at) VALUES (?, ?, ?, ?)",
                (group_id, "", json.dumps(settings), int(time.time()))
            )
            await self.conn.commit()
            return settings

    async def update_group_settings(self, group_id: int, settings: Dict[str, Any]):
        await self.conn.execute(
            "UPDATE groups SET settings = ? WHERE group_id = ?",
            (json.dumps(settings), group_id)
        )
        await self.conn.commit()

    # ---------- User methods ----------
    async def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        await self.conn.execute("""
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, int(time.time())))
        await self.conn.commit()

    # ---------- Warn methods ----------
    async def add_warn(self, user_id: int, group_id: int, reason: str, admin_id: int) -> int:
        cursor = await self.conn.execute(
            "INSERT INTO warnings (user_id, group_id, reason, admin_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, group_id, reason, admin_id, int(time.time()))
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_warn_count(self, user_id: int, group_id: int) -> int:
        async with self.conn.execute(
            "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def reset_warns(self, user_id: int, group_id: int):
        await self.conn.execute(
            "DELETE FROM warnings WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        )
        await self.conn.commit()

    async def get_warn_list(self, group_id: int) -> List[Dict]:
        async with self.conn.execute(
            "SELECT user_id, reason, admin_id, created_at FROM warnings WHERE group_id = ? ORDER BY created_at DESC",
            (group_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [{"user_id": r[0], "reason": r[1], "admin_id": r[2], "created_at": r[3]} for r in rows]

    # ---------- Mute methods ----------
    async def mute_user(self, user_id: int, group_id: int, duration: int):
        until = int(time.time()) + duration
        await self.conn.execute(
            "INSERT OR REPLACE INTO mutes (user_id, group_id, until) VALUES (?, ?, ?)",
            (user_id, group_id, until)
        )
        await self.conn.commit()

    async def unmute_user(self, user_id: int, group_id: int):
        await self.conn.execute(
            "DELETE FROM mutes WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        )
        await self.conn.commit()

    async def is_muted(self, user_id: int, group_id: int) -> bool:
        async with self.conn.execute(
            "SELECT until FROM mutes WHERE user_id = ? AND group_id = ? AND until > ?",
            (user_id, group_id, int(time.time()))
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None

    async def get_all_muted(self, group_id: int) -> List[int]:
        async with self.conn.execute(
            "SELECT user_id FROM mutes WHERE group_id = ? AND until > ?",
            (group_id, int(time.time()))
        ) as cursor:
            rows = await cursor.fetchall()
        return [r[0] for r in rows]

    # ---------- Ban methods ----------
    async def ban_user(self, user_id: int, group_id: int, duration: int = None):
        until = int(time.time()) + duration if duration else 0
        await self.conn.execute(
            "INSERT OR REPLACE INTO bans (user_id, group_id, until) VALUES (?, ?, ?)",
            (user_id, group_id, until)
        )
        await self.conn.commit()

    async def unban_user(self, user_id: int, group_id: int):
        await self.conn.execute(
            "DELETE FROM bans WHERE user_id = ? AND group_id = ?",
            (user_id, group_id)
        )
        await self.conn.commit()

    async def is_banned(self, user_id: int, group_id: int) -> bool:
        async with self.conn.execute(
            "SELECT until FROM bans WHERE user_id = ? AND group_id = ? AND (until = 0 OR until > ?)",
            (user_id, group_id, int(time.time()))
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None

    # ---------- Media settings ----------
    async def set_media_action(self, group_id: int, media_type: str, action: str):
        await self.conn.execute(
            "INSERT OR REPLACE INTO media_settings (group_id, media_type, action) VALUES (?, ?, ?)",
            (group_id, media_type, action)
        )
        await self.conn.commit()

    async def get_media_action(self, group_id: int, media_type: str) -> str:
        async with self.conn.execute(
            "SELECT action FROM media_settings WHERE group_id = ? AND media_type = ?",
            (group_id, media_type)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else "off"

    # ---------- Link settings ----------
    async def add_link_rule(self, group_id: int, domain: str, action: str):
        await self.conn.execute(
            "INSERT OR REPLACE INTO link_settings (group_id, domain, action) VALUES (?, ?, ?)",
            (group_id, domain, action)
        )
        await self.conn.commit()

    async def remove_link_rule(self, group_id: int, domain: str):
        await self.conn.execute(
            "DELETE FROM link_settings WHERE group_id = ? AND domain = ?",
            (group_id, domain)
        )
        await self.conn.commit()

    async def get_link_action(self, group_id: int, domain: str) -> Optional[str]:
        async with self.conn.execute(
            "SELECT action FROM link_settings WHERE group_id = ? AND domain = ?",
            (group_id, domain)
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    # ---------- Banned words ----------
    async def add_banned_word(self, group_id: int, word: str):
        await self.conn.execute(
            "INSERT OR REPLACE INTO banned_words (group_id, word) VALUES (?, ?)",
            (group_id, word.lower())
        )
        await self.conn.commit()

    async def remove_banned_word(self, group_id: int, word: str):
        await self.conn.execute(
            "DELETE FROM banned_words WHERE group_id = ? AND word = ?",
            (group_id, word.lower())
        )
        await self.conn.commit()

    async def get_banned_words(self, group_id: int) -> List[str]:
        async with self.conn.execute(
            "SELECT word FROM banned_words WHERE group_id = ?",
            (group_id,)
        ) as cursor:
            rows = await cursor.fetchall()
        return [r[0] for r in rows]

    # ---------- Stats ----------
    async def increment_message_count(self, group_id: int):
        date = time.strftime("%Y-%m-%d")
        await self.conn.execute("""
            INSERT INTO stats (group_id, date, messages)
            VALUES (?, ?, 1)
            ON CONFLICT(group_id, date) DO UPDATE SET messages = messages + 1
        """, (group_id, date))
        await self.conn.commit()

    # ---------- Logs ----------
    async def add_log(self, group_id: int, event_type: str, user_id: int = None, admin_id: int = None, details: str = None):
        await self.conn.execute(
            "INSERT INTO logs (group_id, event_type, user_id, admin_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (group_id, event_type, user_id, admin_id, details, int(time.time()))
        )
        await self.conn.commit()

    async def get_logs(self, group_id: int, limit: int = 50) -> List[Dict]:
        async with self.conn.execute(
            "SELECT event_type, user_id, admin_id, details, created_at FROM logs WHERE group_id = ? ORDER BY created_at DESC LIMIT ?",
            (group_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
        return [{"type": r[0], "user_id": r[1], "admin_id": r[2], "details": r[3], "time": r[4]} for r in rows]
