# ЧАСТЬ 1: Импорты, конфигурация, BackupManager, Database (начало)
import sqlite3
import asyncio
import random
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import logging
import os

BOT_TOKEN = "8547620515:AAGPC2IJ4qLxSXXDqjyT5foG8sYXlLYud70"
SUPER_ADMIN_ID = 8669060906
BOT_USERNAME = "fluxy_cm_bot"

# JSONBin настройки
JSONBIN_API_KEY = "$2a$10$oQFi.r.b4KoxCupZTsKdzeH6ZktFfBr12SBHnTXgkmRwGBJr1bRdm"
JSONBIN_BIN_ID = "6a8ac58bda38895dfe06783c"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
JSONBIN_HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

WAITING_FOR_ADMIN_ID = 1
WAITING_FOR_ADMIN_LEVEL = 2
WAITING_FOR_AGENT_ID = 3
WAITING_FOR_AGENT_LEVEL = 4
WAITING_FOR_BROADCAST_TEXT = 5
WAITING_FOR_WAR_CLAN_ID = 7
WAITING_FOR_WAR_RATING = 8
WAITING_FOR_BLACKLIST_ID = 11
WAITING_FOR_BLACKLIST_REASON = 12
WAITING_FOR_CLAN_MSG_CLAN = 22
WAITING_FOR_CLAN_MSG_TEXT = 23
WAITING_FOR_INVITE_USER = 20
WAITING_FOR_WELCOME_TEXT = 30
WAITING_FOR_CLAN_ID = 31

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self):
        self.url = JSONBIN_URL
        self.headers = JSONBIN_HEADERS
    
    def backup(self, db):
        try:
            data = {
                "backup_date": datetime.now().isoformat(),
                "users": self._get_users(db),
                "bot_admins": self._get_admins(db),
                "agents": self._get_agents(db),
                "chats": self._get_chats(db),
                "clans": self._get_clans(db),
                "blacklist": self._get_blacklist(db),
                "access_settings": self._get_access(db)
            }
            response = requests.put(self.url, headers=self.headers, json=data)
            if response.status_code == 200:
                print(f"✅ Резервное копирование: {datetime.now().strftime('%H:%M:%S')}")
                return True
            else:
                print(f"❌ Ошибка: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def restore(self, db):
        try:
            response = requests.get(self.url, headers=self.headers)
            if response.status_code == 200:
                data = response.json().get("record", {})
                for user in data.get("users", []):
                    db.cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, clan_id, warnings, registration_date) VALUES (?, ?, ?, ?, ?, ?)", (user["user_id"], user.get("username", ""), user.get("first_name", "Пользователь"), user.get("clan_id"), user.get("warnings", 0), datetime.now().isoformat()))
                for admin in data.get("bot_admins", []):
                    db.cursor.execute("INSERT OR IGNORE INTO bot_admins (user_id, level, added_by, added_date) VALUES (?, ?, ?, ?)", (admin["user_id"], admin.get("level", 1), admin.get("added_by", SUPER_ADMIN_ID), datetime.now().isoformat()))
                for agent in data.get("agents", []):
                    db.cursor.execute("INSERT OR IGNORE INTO support_agents (user_id, level) VALUES (?, ?)", (agent["user_id"], agent.get("level", 1)))
                for clan in data.get("clans", []):
                    db.cursor.execute("INSERT OR IGNORE INTO clans (clan_id, name, leader_id, rating, total_members, wins, losses) VALUES (?, ?, ?, ?, ?, ?, ?)", (clan["clan_id"], clan["name"], clan["leader_id"], clan.get("rating", 0), clan.get("total_members", 0), clan.get("wins", 0), clan.get("losses", 0)))
                for user in data.get("blacklist", []):
                    db.cursor.execute("INSERT OR IGNORE INTO bot_blacklist (user_id, reason, date, added_by) VALUES (?, ?, ?, ?)", (user["user_id"], user.get("reason", ""), datetime.now().isoformat(), SUPER_ADMIN_ID))
                for setting in data.get("access_settings", []):
                    db.cursor.execute("INSERT OR IGNORE INTO access_settings (setting_type, setting_name, display_name, min_level) VALUES (?, ?, ?, ?)", (setting["type"], setting["name"], setting.get("display_name", ""), setting.get("min_level", 10)))
                db.conn.commit()
                print(f"✅ Данные восстановлены из JSONBin")
                return True
        except Exception as e:
            print(f"❌ Ошибка восстановления: {e}")
        return False
    
    def _get_users(self, db):
        db.cursor.execute("SELECT user_id, username, first_name, clan_id, warnings FROM users")
        return [{"user_id": r[0], "username": r[1] or "", "first_name": r[2] or "Пользователь", "clan_id": r[3], "warnings": r[4]} for r in db.cursor.fetchall()]
    
    def _get_admins(self, db):
        db.cursor.execute("SELECT user_id, level, added_by FROM bot_admins")
        return [{"user_id": r[0], "level": r[1], "added_by": r[2]} for r in db.cursor.fetchall()]
    
    def _get_agents(self, db):
        db.cursor.execute("SELECT user_id, level FROM support_agents")
        return [{"user_id": r[0], "level": r[1]} for r in db.cursor.fetchall()]
    
    def _get_chats(self, db):
        db.cursor.execute("SELECT chat_id, title FROM chats WHERE is_active = 1")
        return [{"chat_id": r[0], "title": r[1] or "Чат"} for r in db.cursor.fetchall()]
    
    def _get_clans(self, db):
        db.cursor.execute("SELECT clan_id, name, leader_id, rating, total_members, wins, losses FROM clans")
        return [{"clan_id": r[0], "name": r[1], "leader_id": r[2], "rating": r[3], "total_members": r[4], "wins": r[5], "losses": r[6]} for r in db.cursor.fetchall()]
    
    def _get_blacklist(self, db):
        db.cursor.execute("SELECT user_id, reason FROM bot_blacklist")
        return [{"user_id": r[0], "reason": r[1] or ""} for r in db.cursor.fetchall()]
    
    def _get_access(self, db):
        db.cursor.execute("SELECT setting_type, setting_name, display_name, min_level FROM access_settings")
        return [{"type": r[0], "name": r[1], "display_name": r[2], "min_level": r[3]} for r in db.cursor.fetchall()]


class Database:
    def __init__(self, db_name: str = "fluxy_bot.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        try:
            self.cursor.execute("ALTER TABLE chats ADD COLUMN antispam_max_messages INTEGER DEFAULT 5")
            self.conn.commit()
        except:
            pass
        try:
            self.cursor.execute("ALTER TABLE reports ADD COLUMN message_link TEXT")
            self.conn.commit()
        except:
            pass

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, clan_id INTEGER DEFAULT NULL, clan_join_date TEXT, warnings INTEGER DEFAULT 0, registration_date TEXT, last_activity TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_admins (user_id INTEGER PRIMARY KEY, level INTEGER DEFAULT 1, added_by INTEGER, added_date TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS support_agents (user_id INTEGER PRIMARY KEY, level INTEGER DEFAULT 1, status TEXT DEFAULT 'offline', answered_questions INTEGER DEFAULT 0, online_time INTEGER DEFAULT 0)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, title TEXT, added_date TEXT, is_active INTEGER DEFAULT 1, welcome_text TEXT DEFAULT NULL, welcome_enabled INTEGER DEFAULT 0, antispam_enabled INTEGER DEFAULT 0, antispam_seconds INTEGER DEFAULT 5, antispam_max_messages INTEGER DEFAULT 5)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chat_admins (user_id INTEGER, chat_id INTEGER, level INTEGER DEFAULT 1, added_by INTEGER, added_date TEXT, PRIMARY KEY (user_id, chat_id))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS clans (clan_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, leader_id INTEGER, rating INTEGER DEFAULT 0, entry_type TEXT DEFAULT 'open', created_date TEXT, total_members INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS clan_messages (message_id INTEGER PRIMARY KEY AUTOINCREMENT, from_clan_id INTEGER, to_clan_id INTEGER, from_user_id INTEGER, text TEXT, date TEXT, is_read INTEGER DEFAULT 0)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS punishments (punishment_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, type TEXT, reason TEXT, start_date TEXT, end_date TEXT, is_active INTEGER DEFAULT 1, issued_by INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS rewards (reward_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, from_user_id INTEGER, text TEXT, date TEXT, is_active INTEGER DEFAULT 1)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_blacklist (user_id INTEGER PRIMARY KEY, reason TEXT, date TEXT, added_by INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS bot_rank_names (level INTEGER PRIMARY KEY, name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS agent_rank_names (level INTEGER PRIMARY KEY, name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS chat_rank_names (level INTEGER PRIMARY KEY, name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS clan_requests (request_id INTEGER PRIMARY KEY AUTOINCREMENT, clan_id INTEGER, user_id INTEGER, date TEXT, status TEXT DEFAULT 'pending')''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS clan_wars (war_id INTEGER PRIMARY KEY AUTOINCREMENT, clan1_id INTEGER, clan2_id INTEGER, rating_stake INTEGER, start_date TEXT, end_date TEXT, status TEXT DEFAULT 'active', winner_clan_id INTEGER DEFAULT NULL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reports (report_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, reported_user_id INTEGER, reason TEXT, date TEXT, status TEXT DEFAULT 'pending', handled_by INTEGER DEFAULT NULL, message_link TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS questions (question_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT, date TEXT, status TEXT DEFAULT 'pending', answered_by INTEGER DEFAULT NULL, answer_text TEXT DEFAULT NULL)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS access_settings (setting_id INTEGER PRIMARY KEY AUTOINCREMENT, setting_type TEXT, setting_name TEXT, display_name TEXT, min_level INTEGER DEFAULT 10, UNIQUE(setting_type, setting_name))''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS antispam_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_id INTEGER, message_time TEXT)''')
        self.init_default_ranks()
        self.init_default_access()
        self.conn.commit()
        print("✅ Все таблицы созданы")

    def init_default_ranks(self):
        bot_ranks = {0: "Пользователь", 1: "Младший модератор", 2: "Модератор", 3: "Старший модератор", 4: "Младший админ", 5: "Админ", 6: "Старший админ", 7: "Главный админ", 8: "Заместитель основателя", 9: "Сооснователь", 10: "Основатель бота"}
        for level, name in bot_ranks.items():
            self.cursor.execute("INSERT OR IGNORE INTO bot_rank_names (level, name) VALUES (?, ?)", (level, name))
        agent_ranks = {1: "Младший агент", 2: "Агент", 3: "Старший агент"}
        for level, name in agent_ranks.items():
            self.cursor.execute("INSERT OR IGNORE INTO agent_rank_names (level, name) VALUES (?, ?)", (level, name))
        chat_ranks = {0: "Пользователь", 1: "Младший модератор", 2: "Модератор", 3: "Старший модератор", 4: "Младший админ", 5: "Админ", 6: "Старший админ", 7: "Главный админ", 8: "Заместитель владельца", 9: "Сооснователь", 10: "Владелец"}
        for level, name in chat_ranks.items():
            self.cursor.execute("INSERT OR IGNORE INTO chat_rank_names (level, name) VALUES (?, ?)", (level, name))
        print("✅ Ранги инициализированы")

    def init_default_access(self):
        bot_functions = {'manage_admins': '👥 Управление админами', 'manage_agents': '🔰 Управление агентами', 'blacklist': '🚫 Черный список', 'give_clan_rep': '⭐️ Выдача репутации', 'view_chats': '🗂 Просмотр чатов', 'stats': '📊 Статистика', 'broadcast': '📨 Рассылка', 'view_reports': '❗️ Просмотр жалоб', 'give_reward': '🎁 Выдача наград', 'rename_rank': '📝 Переименование рангов'}
        for func, display_name in bot_functions.items():
            self.cursor.execute("INSERT OR IGNORE INTO access_settings (setting_type, setting_name, display_name, min_level) VALUES ('bot', ?, ?, 10)", (func, display_name))
        agent_functions = {'view_questions': '❓ Просмотр вопросов', 'answer_questions': '✉️ Ответ на вопросы', 'hstats': '📊 Статистика агента'}
        for func, display_name in agent_functions.items():
            self.cursor.execute("INSERT OR IGNORE INTO access_settings (setting_type, setting_name, display_name, min_level) VALUES ('agent', ?, ?, 3)", (func, display_name))
        chat_functions = {'ban': '🔨 Бан', 'unban': '🔓 Разбан', 'mute': '🔇 Мут', 'unmute': '🔊 Размут', 'warn': '⚠️ Предупреждение', 'unwarn': '✅ Снятие предупреждения', 'setadm': '👑 Назначение админов', 'welcome_settings': '👋 Приветствие', 'antispam_settings': '🚫 Антиспам'}
        for func, display_name in chat_functions.items():
            self.cursor.execute("INSERT OR IGNORE INTO access_settings (setting_type, setting_name, display_name, min_level) VALUES ('chat', ?, ?, 10)", (func, display_name))
        self.conn.commit()
        print("✅ Доступы инициализированы")

    def add_user(self, user_id, username, first_name):
        username = username or ""
        first_name = first_name or "Пользователь"
        self.cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, registration_date, last_activity) VALUES (?, ?, ?, ?, ?)", (user_id, username, first_name, datetime.now().isoformat(), datetime.now().isoformat()))
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def get_bot_rank_name(self, level):
        self.cursor.execute("SELECT name FROM bot_rank_names WHERE level = ?", (level,))
        result = self.cursor.fetchone()
        return result[0] if result else f"Уровень {level}"

    def get_chat_rank_name(self, level):
        self.cursor.execute("SELECT name FROM chat_rank_names WHERE level = ?", (level,))
        result = self.cursor.fetchone()
        return result[0] if result else f"Уровень {level}"

    def get_agent_rank_name(self, level):
        self.cursor.execute("SELECT name FROM agent_rank_names WHERE level = ?", (level,))
        result = self.cursor.fetchone()
        return result[0] if result else f"Уровень {level}"

    def add_bot_admin(self, user_id, level, added_by):
        self.cursor.execute("INSERT OR REPLACE INTO bot_admins (user_id, level, added_by, added_date) VALUES (?, ?, ?, ?)", (user_id, level, added_by, datetime.now().isoformat()))
        self.conn.commit()

    def remove_bot_admin(self, user_id):
        self.cursor.execute("DELETE FROM bot_admins WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_bot_admin_level(self, user_id):
        if user_id == SUPER_ADMIN_ID:
            return 10
        self.cursor.execute("SELECT level FROM bot_admins WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def get_all_bot_admins(self):
        self.cursor.execute("SELECT ba.user_id, ba.level, ba.added_by, ba.added_date, u.username, u.first_name FROM bot_admins ba LEFT JOIN users u ON ba.user_id = u.user_id ORDER BY ba.level DESC")
        return self.cursor.fetchall()

    def update_bot_admin_level(self, user_id, level):
        self.cursor.execute("UPDATE bot_admins SET level = ? WHERE user_id = ?", (level, user_id))
        self.conn.commit()

    def add_agent(self, user_id, level):
        self.cursor.execute("INSERT OR REPLACE INTO support_agents (user_id, level) VALUES (?, ?)", (user_id, level))
        self.conn.commit()

    def remove_agent(self, user_id):
        self.cursor.execute("DELETE FROM support_agents WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_agent_level(self, user_id):
        self.cursor.execute("SELECT level FROM support_agents WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def get_all_agents(self):
        self.cursor.execute("SELECT sa.user_id, sa.level, sa.status, sa.answered_questions, sa.online_time, u.username, u.first_name FROM support_agents sa LEFT JOIN users u ON sa.user_id = u.user_id ORDER BY sa.level DESC")
        return self.cursor.fetchall()

    def update_agent_level(self, user_id, level):
        self.cursor.execute("UPDATE support_agents SET level = ? WHERE user_id = ?", (level, user_id))
        self.conn.commit()

    def create_clan(self, name, leader_id):
        self.cursor.execute("INSERT INTO clans (name, leader_id, created_date) VALUES (?, ?, ?)", (name, leader_id, datetime.now().isoformat()))
        self.conn.commit()
        clan_id = self.cursor.lastrowid
        self.join_clan(leader_id, clan_id)
        return clan_id

    def get_clan_by_id(self, clan_id):
        self.cursor.execute("SELECT * FROM clans WHERE clan_id = ?", (clan_id,))
        return self.cursor.fetchone()

    def get_clan_by_name(self, name):
        self.cursor.execute("SELECT * FROM clans WHERE name = ?", (name,))
        return self.cursor.fetchone()

    def get_user_clan(self, user_id):
        self.cursor.execute("SELECT c.* FROM clans c JOIN users u ON u.clan_id = c.clan_id WHERE u.user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def join_clan(self, user_id, clan_id):
        self.cursor.execute("UPDATE users SET clan_id = ?, clan_join_date = ? WHERE user_id = ?", (clan_id, datetime.now().isoformat(), user_id))
        self.cursor.execute("UPDATE clans SET total_members = total_members + 1 WHERE clan_id = ?", (clan_id,))
        self.conn.commit()

    def leave_clan(self, user_id):
        self.cursor.execute("SELECT clan_id FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result and result[0]:
            self.cursor.execute("UPDATE clans SET total_members = total_members - 1 WHERE clan_id = ?", (result[0],))
        self.cursor.execute("UPDATE users SET clan_id = NULL WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_clan_members(self, clan_id):
        self.cursor.execute("SELECT u.user_id, u.username, u.first_name, u.clan_join_date FROM users u WHERE u.clan_id = ? ORDER BY u.clan_join_date", (clan_id,))
        return self.cursor.fetchall()

    def add_clan_rating(self, clan_id, rating):
        self.cursor.execute("UPDATE clans SET rating = rating + ? WHERE clan_id = ?", (rating, clan_id))
        self.conn.commit()

    def get_top_clans(self, limit=10):
        self.cursor.execute("SELECT clan_id, name, rating, leader_id, total_members FROM clans ORDER BY rating DESC, total_members DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()

    def update_clan_entry_type(self, clan_id, entry_type):
        self.cursor.execute("UPDATE clans SET entry_type = ? WHERE clan_id = ?", (entry_type, clan_id))
        self.conn.commit()

    def add_clan_request(self, clan_id, user_id):
        self.cursor.execute("INSERT INTO clan_requests (clan_id, user_id, date) VALUES (?, ?, ?)", (clan_id, user_id, datetime.now().isoformat()))
        self.conn.commit()

    def get_clan_requests(self, clan_id):
        self.cursor.execute("SELECT cr.*, u.username, u.first_name FROM clan_requests cr LEFT JOIN users u ON cr.user_id = u.user_id WHERE cr.clan_id = ? AND cr.status = 'pending'", (clan_id,))
        return self.cursor.fetchall()

    def update_clan_request(self, request_id, status):
        self.cursor.execute("UPDATE clan_requests SET status = ? WHERE request_id = ?", (status, request_id))
        self.conn.commit()

    def declare_war(self, clan1_id, clan2_id, rating_stake):
        clan1 = self.get_clan_by_id(clan1_id)
        clan2 = self.get_clan_by_id(clan2_id)
        if not clan1 or not clan2:
            return None
        clan1_chance = 50
        clan2_chance = 50
        clan1_bonus = min((clan1[3] // 1000) * 5, 25)
        clan2_bonus = min((clan2[3] // 1000) * 5, 25)
        clan1_chance += clan1_bonus - clan2_bonus
        clan2_chance += clan2_bonus - clan1_bonus
        clan1_chance = max(25, min(75, clan1_chance))
        clan2_chance = 100 - clan1_chance
        winner_id = random.choices([clan1_id, clan2_id], weights=[clan1_chance, clan2_chance])[0]
        loser_id = clan2_id if winner_id == clan1_id else clan1_id
        self.add_clan_rating(winner_id, rating_stake)
        self.add_clan_rating(loser_id, -rating_stake)
        if winner_id == clan1_id:
            self.cursor.execute("UPDATE clans SET wins = wins + 1 WHERE clan_id = ?", (clan1_id,))
            self.cursor.execute("UPDATE clans SET losses = losses + 1 WHERE clan_id = ?", (clan2_id,))
        else:
            self.cursor.execute("UPDATE clans SET wins = wins + 1 WHERE clan_id = ?", (clan2_id,))
            self.cursor.execute("UPDATE clans SET losses = losses + 1 WHERE clan_id = ?", (clan1_id,))
        self.cursor.execute("INSERT INTO clan_wars (clan1_id, clan2_id, rating_stake, start_date, end_date, status, winner_clan_id) VALUES (?, ?, ?, ?, ?, 'ended', ?)", (clan1_id, clan2_id, rating_stake, datetime.now().isoformat(), datetime.now().isoformat(), winner_id))
        self.conn.commit()
        return {'winner_id': winner_id, 'clan1_chance': clan1_chance, 'clan2_chance': clan2_chance, 'clan1_name': clan1[1], 'clan2_name': clan2[1]}

    def add_clan_message(self, from_clan_id, to_clan_id, from_user_id, text):
        self.cursor.execute("INSERT INTO clan_messages (from_clan_id, to_clan_id, from_user_id, text, date) VALUES (?, ?, ?, ?, ?)", (from_clan_id, to_clan_id, from_user_id, text, datetime.now().isoformat()))
        self.conn.commit()

    def get_clan_messages(self, clan_id):
        self.cursor.execute("SELECT cm.*, c.name as from_clan_name, u.first_name as from_user_name FROM clan_messages cm LEFT JOIN clans c ON cm.from_clan_id = c.clan_id LEFT JOIN users u ON cm.from_user_id = u.user_id WHERE cm.to_clan_id = ? ORDER BY cm.date DESC", (clan_id,))
        return self.cursor.fetchall()

    def add_punishment(self, user_id, chat_id, ptype, reason, duration_minutes, issued_by):
        end_date = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat() if duration_minutes > 0 else None
        self.cursor.execute("INSERT INTO punishments (user_id, chat_id, type, reason, start_date, end_date, issued_by) VALUES (?, ?, ?, ?, ?, ?, ?)", (user_id, chat_id, ptype, reason, datetime.now().isoformat(), end_date, issued_by))
        self.conn.commit()

    def get_active_punishments(self, user_id):
        self.cursor.execute("SELECT p.*, u.first_name as issued_by_name FROM punishments p LEFT JOIN users u ON p.issued_by = u.user_id WHERE p.user_id = ? AND p.is_active = 1 ORDER BY p.start_date DESC", (user_id,))
        return self.cursor.fetchall()

    def add_reward(self, user_id, from_user_id, text):
        self.cursor.execute("INSERT INTO rewards (user_id, from_user_id, text, date) VALUES (?, ?, ?, ?)", (user_id, from_user_id, text, datetime.now().isoformat()))
        self.conn.commit()

    def get_user_rewards(self, user_id):
        self.cursor.execute("SELECT r.*, u.username, u.first_name FROM rewards r LEFT JOIN users u ON r.from_user_id = u.user_id WHERE r.user_id = ? AND r.is_active = 1 ORDER BY r.date DESC", (user_id,))
        return self.cursor.fetchall()

    def add_to_blacklist(self, user_id, reason, added_by):
        self.cursor.execute("INSERT OR REPLACE INTO bot_blacklist (user_id, reason, date, added_by) VALUES (?, ?, ?, ?)", (user_id, reason, datetime.now().isoformat(), added_by))
        self.conn.commit()

    def remove_from_blacklist(self, user_id):
        self.cursor.execute("DELETE FROM bot_blacklist WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_blacklist(self):
        self.cursor.execute("SELECT bb.*, u.username, u.first_name FROM bot_blacklist bb LEFT JOIN users u ON bb.user_id = u.user_id")
        return self.cursor.fetchall()

    def is_blacklisted(self, user_id):
        self.cursor.execute("SELECT 1 FROM bot_blacklist WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None

    def add_report(self, user_id, reported_user_id, reason, message_link=None):
        self.cursor.execute("INSERT INTO reports (user_id, reported_user_id, reason, date, message_link) VALUES (?, ?, ?, ?, ?)", (user_id, reported_user_id, reason, datetime.now().isoformat(), message_link))
        self.conn.commit()

    def get_pending_reports(self):
        self.cursor.execute("SELECT r.*, u1.first_name as reporter_name, u2.first_name as reported_name FROM reports r LEFT JOIN users u1 ON r.user_id = u1.user_id LEFT JOIN users u2 ON r.reported_user_id = u2.user_id WHERE r.status = 'pending' ORDER BY r.date DESC")
        return self.cursor.fetchall()

    def update_report_status(self, report_id, status, handled_by):
        self.cursor.execute("UPDATE reports SET status = ?, handled_by = ? WHERE report_id = ?", (status, handled_by, report_id))
        self.conn.commit()

    def add_question(self, user_id, text):
        self.cursor.execute("INSERT INTO questions (user_id, text, date) VALUES (?, ?, ?)", (user_id, text, datetime.now().isoformat()))
        self.conn.commit()

    def get_pending_questions(self):
        self.cursor.execute("SELECT q.*, u.first_name, u.username FROM questions q LEFT JOIN users u ON q.user_id = u.user_id WHERE q.status = 'pending' ORDER BY q.date")
        return self.cursor.fetchall()

    def update_question_status(self, question_id, status, answered_by, answer_text=None):
        self.cursor.execute("UPDATE questions SET status = ?, answered_by = ?, answer_text = ? WHERE question_id = ?", (status, answered_by, answer_text, question_id))
        self.conn.commit()

    def add_chat(self, chat_id, title):
        self.cursor.execute("INSERT OR REPLACE INTO chats (chat_id, title, added_date, is_active) VALUES (?, ?, ?, 1)", (chat_id, title or "Чат", datetime.now().isoformat()))
        self.conn.commit()

    def get_all_chats(self):
        self.cursor.execute("SELECT * FROM chats WHERE is_active = 1")
        return self.cursor.fetchall()

    def add_chat_admin(self, user_id, chat_id, level, added_by):
        self.cursor.execute("INSERT OR REPLACE INTO chat_admins (user_id, chat_id, level, added_by, added_date) VALUES (?, ?, ?, ?, ?)", (user_id, chat_id, level, added_by, datetime.now().isoformat()))
        self.conn.commit()

    def get_chat_admin_level(self, user_id, chat_id):
        self.cursor.execute("SELECT level FROM chat_admins WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def get_chat_admins(self, chat_id):
        self.cursor.execute("SELECT ca.user_id, ca.level, ca.added_by, ca.added_date, u.username, u.first_name FROM chat_admins ca LEFT JOIN users u ON ca.user_id = u.user_id WHERE ca.chat_id = ? ORDER BY ca.level DESC", (chat_id,))
        return self.cursor.fetchall()

    def update_chat_owner(self, chat_id, new_owner_id):
        self.cursor.execute("DELETE FROM chat_admins WHERE chat_id = ? AND level = 10 AND user_id != ?", (chat_id, new_owner_id))
        self.cursor.execute("INSERT OR REPLACE INTO chat_admins (user_id, chat_id, level, added_by, added_date) VALUES (?, ?, 10, ?, ?)", (new_owner_id, chat_id, SUPER_ADMIN_ID, datetime.now().isoformat()))
        self.conn.commit()

    def set_access_level(self, setting_type, setting_name, min_level):
        self.cursor.execute("INSERT OR REPLACE INTO access_settings (setting_type, setting_name, min_level) VALUES (?, ?, ?)", (setting_type, setting_name, min_level))
        self.conn.commit()

    def get_access_level(self, setting_type, setting_name):
        self.cursor.execute("SELECT min_level FROM access_settings WHERE setting_type = ? AND setting_name = ?", (setting_type, setting_name))
        result = self.cursor.fetchone()
        return result[0] if result else 10

    def set_welcome_text(self, chat_id, text):
        self.cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
        if not self.cursor.fetchone():
            self.add_chat(chat_id, "Chat")
        self.cursor.execute("UPDATE chats SET welcome_text = ?, welcome_enabled = 1 WHERE chat_id = ?", (text, chat_id))
        self.conn.commit()

    def enable_welcome(self, chat_id, enabled):
        self.cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
        if not self.cursor.fetchone():
            self.add_chat(chat_id, "Chat")
        self.cursor.execute("UPDATE chats SET welcome_enabled = ? WHERE chat_id = ?", (1 if enabled else 0, chat_id))
        self.conn.commit()

    def get_welcome_settings(self, chat_id):
        self.cursor.execute("SELECT welcome_enabled, welcome_text FROM chats WHERE chat_id = ?", (chat_id,))
        return self.cursor.fetchone()

    def enable_antispam(self, chat_id, enabled):
        self.cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
        if not self.cursor.fetchone():
            self.add_chat(chat_id, "Chat")
        self.cursor.execute("UPDATE chats SET antispam_enabled = ? WHERE chat_id = ?", (1 if enabled else 0, chat_id))
        self.conn.commit()

    def set_antispam_seconds(self, chat_id, seconds):
        self.cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
        if not self.cursor.fetchone():
            self.add_chat(chat_id, "Chat")
        self.cursor.execute("UPDATE chats SET antispam_seconds = ? WHERE chat_id = ?", (seconds, chat_id))
        self.conn.commit()

    def set_antispam_max_messages(self, chat_id, max_messages):
        self.cursor.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
        if not self.cursor.fetchone():
            self.add_chat(chat_id, "Chat")
        try:
            self.cursor.execute("UPDATE chats SET antispam_max_messages = ? WHERE chat_id = ?", (max_messages, chat_id))
            self.conn.commit()
        except sqlite3.OperationalError:
            self.cursor.execute("ALTER TABLE chats ADD COLUMN antispam_max_messages INTEGER DEFAULT 5")
            self.conn.commit()
            self.cursor.execute("UPDATE chats SET antispam_max_messages = ? WHERE chat_id = ?", (max_messages, chat_id))
            self.conn.commit()

    def get_antispam_max_messages(self, chat_id):
        try:
            self.cursor.execute("SELECT antispam_max_messages FROM chats WHERE chat_id = ?", (chat_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 5
        except sqlite3.OperationalError:
            return 5

    def get_antispam_settings(self, chat_id):
        self.cursor.execute("SELECT antispam_enabled, antispam_seconds FROM chats WHERE chat_id = ?", (chat_id,))
        return self.cursor.fetchone()

    def add_antispam_message(self, user_id, chat_id):
        self.cursor.execute("INSERT INTO antispam_messages (user_id, chat_id, message_time) VALUES (?, ?, ?)", (user_id, chat_id, datetime.now().isoformat()))
        self.cursor.execute("DELETE FROM antispam_messages WHERE message_time < ?", ((datetime.now() - timedelta(minutes=1)).isoformat(),))
        self.conn.commit()

    def get_recent_messages(self, user_id, chat_id, seconds):
        self.cursor.execute("SELECT COUNT(*) FROM antispam_messages WHERE user_id = ? AND chat_id = ? AND message_time > ?", (user_id, chat_id, (datetime.now() - timedelta(seconds=seconds)).isoformat()))
        return self.cursor.fetchone()[0]

    def update_bot_rank_name(self, level, name):
        self.cursor.execute("INSERT OR REPLACE INTO bot_rank_names (level, name) VALUES (?, ?)", (level, name))
        self.conn.commit()

    def update_agent_rank_name(self, level, name):
        self.cursor.execute("INSERT OR REPLACE INTO agent_rank_names (level, name) VALUES (?, ?)", (level, name))
        self.conn.commit()

    def update_chat_rank_name(self, level, name):
        self.cursor.execute("INSERT OR REPLACE INTO chat_rank_names (level, name) VALUES (?, ?)", (level, name))
        self.conn.commit()

    def get_all_users(self):
        self.cursor.execute("SELECT user_id FROM users")
        return self.cursor.fetchall()

    def get_total_stats(self):
        self.cursor.execute("SELECT COUNT(*) FROM users")
        total_users = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM chats WHERE is_active = 1")
        total_chats = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM clans")
        total_clans = self.cursor.fetchone()[0]
        return total_users, total_chats, total_clans

    def close(self):
        self.conn.close()


db = Database()
backup_manager = BackupManager()
backup_manager.restore(db)

def check_bot_access(user_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_bot_admin_level(user_id)
    required_level = db.get_access_level('bot', function)
    return user_level >= required_level

def check_chat_access(user_id, chat_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_chat_admin_level(user_id, chat_id)
    if user_level >= 10:
        return True
    required_level = db.get_access_level('chat', function)
    return user_level >= required_level

def check_agent_access(user_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_agent_level(user_id)
    required_level = db.get_access_level('agent', function)
    return user_level >= required_level
    
    # ЧАСТЬ 2: Keyboards (все клавиатуры)
class Keyboards:
    @staticmethod
    def main_menu():
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help_menu"), InlineKeyboardButton("📋 Команды", callback_data="commands_menu")],
            [InlineKeyboardButton("🔰 Агенты поддержки", callback_data="agents_list")],
            [InlineKeyboardButton("➕ Добавить в чат", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def main_menu_with_admin():
        keyboard = [
            [InlineKeyboardButton("⭐️ Админ панель бота", callback_data="admin_panel")],
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help_menu"), InlineKeyboardButton("📋 Команды", callback_data="commands_menu")],
            [InlineKeyboardButton("🔰 Агенты поддержки", callback_data="agents_list")],
            [InlineKeyboardButton("➕ Добавить в чат", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def main_menu_with_chat_admin():
        keyboard = [
            [InlineKeyboardButton("👑 Админ панель чата", callback_data="chat_panel")],
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help_menu"), InlineKeyboardButton("📋 Команды", callback_data="commands_menu")],
            [InlineKeyboardButton("🔰 Агенты поддержки", callback_data="agents_list")],
            [InlineKeyboardButton("➕ Добавить в чат", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def main_menu_with_both():
        keyboard = [
            [InlineKeyboardButton("⭐️ Админ панель бота", callback_data="admin_panel")],
            [InlineKeyboardButton("👑 Админ панель чата", callback_data="chat_panel")],
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")],
            [InlineKeyboardButton("❓ Помощь", callback_data="help_menu"), InlineKeyboardButton("📋 Команды", callback_data="commands_menu")],
            [InlineKeyboardButton("🔰 Агенты поддержки", callback_data="agents_list")],
            [InlineKeyboardButton("➕ Добавить в чат", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_panel():
        keyboard = [
            [InlineKeyboardButton("👥 Админы бота", callback_data="admins_list")],
            [InlineKeyboardButton("🔰 Агенты поддержки", callback_data="agents_manage")],
            [InlineKeyboardButton("🚫 Черный список бота", callback_data="bot_blacklist")],
            [InlineKeyboardButton("⭐️ Выдать репутацию клану", callback_data="give_clan_rep")],
            [InlineKeyboardButton("📋 Все команды бота", callback_data="all_commands")],
            [InlineKeyboardButton("🗂 Все чаты с ботом", callback_data="all_chats")],
            [InlineKeyboardButton("📊 Статистика бота", callback_data="bot_stats")],
            [InlineKeyboardButton("📨 Рассылка", callback_data="broadcast_menu")],
            [InlineKeyboardButton("⚙️ Права рангов", callback_data="bot_rank_settings")],
            [InlineKeyboardButton("⚙️ Права уровней АП", callback_data="agent_settings")],
            [InlineKeyboardButton("📝 Названия рангов бота", callback_data="bot_rank_names"), InlineKeyboardButton("📝 Названия уровней АП", callback_data="agent_rank_names")],
            [InlineKeyboardButton("👑 Супер админ", callback_data="super_admin")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def chat_panel():
        keyboard = [
            [InlineKeyboardButton("⚙️ Права рангов", callback_data="chat_rank_settings")],
            [InlineKeyboardButton("👥 Админы чата", callback_data="chat_admins_list")],
            [InlineKeyboardButton("📝 Названия рангов чата", callback_data="chat_rank_names")],
            [InlineKeyboardButton("👋 Приветствие", callback_data="welcome_settings")],
            [InlineKeyboardButton("🚫 Антиспам", callback_data="antispam_settings")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def profile_menu():
        keyboard = [
            [InlineKeyboardButton("🏆 Награды", callback_data="my_rewards")],
            [InlineKeyboardButton("🎁 Выдать награду", callback_data="give_reward")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def stats_menu():
        keyboard = [
            [InlineKeyboardButton("🏆 Награды", callback_data="my_rewards")],
            [InlineKeyboardButton("🎁 Выдать награду", callback_data="give_reward")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def clan_menu():
        keyboard = [
            [InlineKeyboardButton("➕ Создать клан", callback_data="create_clan_btn")],
            [InlineKeyboardButton("📋 Список кланов", callback_data="clan_list_btn")],
            [InlineKeyboardButton("🔍 Найти клан", callback_data="find_clan_btn")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def my_clan_menu():
        keyboard = [
            [InlineKeyboardButton("👥 Участники клана", callback_data="clan_members")],
            [InlineKeyboardButton("🔒 Вход в клан", callback_data="clan_entry")],
            [InlineKeyboardButton("✉️ Сообщения клана", callback_data="clan_messages")],
            [InlineKeyboardButton("⚔ Обьявить войну", callback_data="declare_war")],
            [InlineKeyboardButton("📩 Сообщение клану", callback_data="message_clan")],
            [InlineKeyboardButton("📋 Заявки", callback_data="clan_requests")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def help_menu():
        keyboard = [
            [InlineKeyboardButton("❗️ Жалоба", callback_data="report")],
            [InlineKeyboardButton("❓ Вопрос", callback_data="question")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_manage_menu():
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔄 Изменить уровень", callback_data="change_admin_level")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def agent_manage_menu():
        keyboard = [
            [InlineKeyboardButton("➕ Добавить агента", callback_data="add_agent")],
            [InlineKeyboardButton("➖ Удалить агента", callback_data="remove_agent")],
            [InlineKeyboardButton("🔄 Изменить уровень", callback_data="change_agent_level")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def clan_entry_menu():
        keyboard = [
            [InlineKeyboardButton("✅ Разрешить", callback_data="entry_open")],
            [InlineKeyboardButton("❌ Запретить", callback_data="entry_closed")],
            [InlineKeyboardButton("📝 Заявка", callback_data="entry_request")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="clan_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_start():
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def broadcast_menu():
        keyboard = [
            [InlineKeyboardButton("👥 Рассылка в ЛС", callback_data="broadcast_pm")],
            [InlineKeyboardButton("💬 Рассылка по чатам", callback_data="broadcast_chats")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def welcome_settings_menu(welcome_enabled):
        status = "✅ Включено" if welcome_enabled else "❌ Выключено"
        keyboard = [
            [InlineKeyboardButton(f"Статус: {status}", callback_data="toggle_welcome")],
            [InlineKeyboardButton("📝 Изменить текст", callback_data="edit_welcome_text")],
            [InlineKeyboardButton("👁 Показать приветствие", callback_data="show_welcome")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="chat_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max_messages):
        status = "✅ Включено" if antispam_enabled else "❌ Выключено"
        keyboard = [
            [InlineKeyboardButton(f"Статус: {status}", callback_data="toggle_antispam")],
            [InlineKeyboardButton(f"⏱ Интервал: {antispam_seconds} сек", callback_data="change_antispam_interval")],
            [InlineKeyboardButton(f"📊 Макс. сообщений: {antispam_max_messages}", callback_data="change_antispam_messages")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="chat_panel")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def antispam_interval_menu():
        keyboard = [
            [InlineKeyboardButton("1 секунда", callback_data="set_antispam_1")],
            [InlineKeyboardButton("3 секунды", callback_data="set_antispam_3")],
            [InlineKeyboardButton("5 секунд", callback_data="set_antispam_5")],
            [InlineKeyboardButton("10 секунд", callback_data="set_antispam_10")],
            [InlineKeyboardButton("30 секунд", callback_data="set_antispam_30")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="antispam_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def antispam_messages_menu():
        keyboard = [
            [InlineKeyboardButton("3 сообщения", callback_data="set_msg_3")],
            [InlineKeyboardButton("5 сообщений", callback_data="set_msg_5")],
            [InlineKeyboardButton("7 сообщений", callback_data="set_msg_7")],
            [InlineKeyboardButton("10 сообщений", callback_data="set_msg_10")],
            [InlineKeyboardButton("15 сообщений", callback_data="set_msg_15")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="antispam_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
        
        # ЧАСТЬ 3: Handlers (основные команды)
class Handlers:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name)
        if db.is_blacklisted(user.id):
            await update.message.reply_text("❌ Вы в черном списке бота!")
            return
        
        bot_rank_level = db.get_bot_admin_level(user.id)
        
        is_chat_owner = False
        if update.effective_chat.type != 'private':
            chat_id = update.effective_chat.id
            db.add_chat(chat_id, update.effective_chat.title or "Чат")
            try:
                admins = await context.bot.get_chat_administrators(chat_id)
                for admin in admins:
                    if admin.status == 'creator':
                        db.update_chat_owner(chat_id, admin.user.id)
                        if admin.user.id == user.id:
                            is_chat_owner = True
                        break
            except:
                pass
        
        bot_rank_name = db.get_bot_rank_name(bot_rank_level)
        text = f"""👋 Добро пожаловать в Fluxy | Чат-менеджер.
━━━━━━━━━━━━━━━━

🆔 Ваш ID: {user.id}
🎖️ Ваш ранг: {bot_rank_name}

━━━━━━━━━━━━━━━━
Для продолжения нажмите на кнопку ниже ⬇️"""
        
        if bot_rank_level >= 1 and is_chat_owner:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu_with_both())
        elif bot_rank_level >= 1:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu_with_admin())
        elif is_chat_owner:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu_with_chat_admin())
        else:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu())

    @staticmethod
    async def on_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and update.message.new_chat_members:
            for member in update.message.new_chat_members:
                if member.id == context.bot.id:
                    chat_id = update.effective_chat.id
                    chat_title = update.effective_chat.title or "Чат"
                    db.add_chat(chat_id, chat_title)
                    try:
                        admins = await context.bot.get_chat_administrators(chat_id)
                        for admin in admins:
                            if admin.status == 'creator':
                                db.update_chat_owner(chat_id, admin.user.id)
                                await update.message.reply_text(
                                    f"✅ Бот активирован!\n"
                                    f"👑 Владелец чата: {admin.user.first_name}\n"
                                    f"📝 Напишите /start чтобы увидеть админ панель чата."
                                )
                                break
                    except:
                        pass

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = """📋 Справка по командам:
━━━━━━━━━━━━━━━━

/start - Показать главное меню
/profile - Показать профиль
/ping - Проверить пинг
/id - Показать ID

/clan - Меню клана
/clan_top - Топ кланов
/clan_bonus - Бонус клана
/create_clan - Создать клан
/join_clan - Вступить в клан
/leave_clan - Покинуть клан

/ban - Забанить
/mute - Замутить
/warn - Предупредить
/setadm - Назначить админа
/report - Отправить жалобу
/stats - Статистика"""
        await update.message.reply_text(text)

    @staticmethod
    async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name)
        clan = db.get_user_clan(user.id)
        text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}
🛡️ Клан: {clan[1] if clan else 'Нет'}
🏆 Рейтинг: {clan[3] if clan else 0}"""
        await update.message.reply_text(text, reply_markup=Keyboards.profile_menu())

    @staticmethod
    async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
        import time
        start_time = time.time()
        msg = await update.message.reply_text("Измеряю пинг...")
        end_time = time.time()
        ping = round((end_time - start_time) * 1000)
        moscow_time = datetime.now().strftime("%H:%M:%S")
        await msg.edit_text(f"🏓 Понг!\n⏱ Пинг: {ping}ms\n🕐 Время МСК: {moscow_time}")

    @staticmethod
    async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.reply_to_message:
            user = update.message.reply_to_message.from_user
            await update.message.reply_text(f"🆔 ID: {user.id}")
        else:
            await update.message.reply_text(f"🆔 Ваш ID: {update.effective_user.id}")

    @staticmethod
    async def clan_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if not clan:
            await update.message.reply_text("❌ Вы не в клане!")
            return
        members = db.get_clan_members(clan[0])
        bonus = len(members)
        db.add_clan_rating(clan[0], bonus)
        await update.message.reply_text(f"✅ Клан получил +{bonus} рейтинга!")

    @staticmethod
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте на сообщение!", reply_markup=Keyboards.back_to_start())
            return
        target = update.message.reply_to_message.from_user
        db.add_user(target.id, target.username, target.first_name)
        clan = db.get_user_clan(target.id)
        punishments = db.get_active_punishments(target.id)
        user_data = db.get_user(target.id)
        warnings = user_data[6] if user_data else 0
        
        text = f"""👤 {target.first_name}
━━━━━━━━━━━━━━━━

🆔 ID: {target.id}
🎖️ Ранг: {db.get_bot_rank_name(db.get_bot_admin_level(target.id))}
🛡️ Клан: {clan[1] if clan else 'Нет'}
⚠️ Варны: {warnings}/3
🔨 Наказаний: {len(punishments)}"""
        
        if punishments:
            text += "\n\n📋 Наказания:\n"
            for p in punishments:
                issued_name = p[9] if len(p) > 9 and p[9] else "Неизвестно"
                ptype_emoji = "🔨" if p[3] == "ban" else "🔇" if p[3] == "mute" else "⚠️"
                text += f"{ptype_emoji} {p[3]}: {p[4]}\n"
                text += f"   👤 Выдал: {issued_name}\n"
                text += f"   📅 Дата: {p[5][:10] if p[5] else 'Н/Д'}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
        
        await update.message.reply_text(text, reply_markup=Keyboards.stats_menu())

    @staticmethod
    async def create_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not context.args:
            await update.message.reply_text("❌ /create_clan <название>")
            return
        clan_name = " ".join(context.args)
        if db.get_clan_by_name(clan_name):
            await update.message.reply_text("❌ Клан уже существует!")
            return
        if db.get_user_clan(user.id):
            await update.message.reply_text("❌ Вы уже в клане!")
            return
        clan_id = db.create_clan(clan_name, user.id)
        await update.message.reply_text(f"✅ Клан «{clan_name}» создан!\n🆔 ID: {clan_id}")

    @staticmethod
    async def join_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not context.args:
            await update.message.reply_text("❌ /join_clan <ID>")
            return
        try:
            clan_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        clan = db.get_clan_by_id(clan_id)
        if not clan:
            await update.message.reply_text("❌ Клан не найден!")
            return
        if db.get_user_clan(user.id):
            await update.message.reply_text("❌ Вы уже в клане!")
            return
        if clan[4] == 'closed':
            await update.message.reply_text("❌ Вход закрыт!")
            return
        if clan[4] == 'request':
            db.add_clan_request(clan_id, user.id)
            await update.message.reply_text("✅ Заявка отправлена!")
            return
        db.join_clan(user.id, clan_id)
        await update.message.reply_text(f"✅ Вы вступили в «{clan[1]}»!")

    @staticmethod
    async def leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if not clan:
            await update.message.reply_text("❌ Вы не в клане!")
            return
        if clan[2] == user.id:
            await update.message.reply_text("❌ Лидер не может покинуть клан!")
            return
        db.leave_clan(user.id)
        await update.message.reply_text(f"✅ Вы покинули «{clan[1]}»!")

    @staticmethod
    async def clan_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if clan:
            text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan[0]}
🛡 Название: {clan[1]}
🏆 Рейтинг: {clan[3]}
👥 Участников: {clan[6]}
🏅 Побед: {clan[7]}
💀 Поражений: {clan[8]}"""
            await update.message.reply_text(text, reply_markup=Keyboards.my_clan_menu())
        else:
            await update.message.reply_text("🛡 Кланы\n\nВыберите действие:", reply_markup=Keyboards.clan_menu())

    @staticmethod
    async def clan_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        clans = db.get_top_clans(15)
        text = "🏆 Топ 15 кланов:\n━━━━━━━━━━━━━━━━\n\n"
        if not clans:
            text += "Пока нет кланов"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. 🛡 {clan[1]}\n   🆔 ID: {clan[0]}\n   🏆 Рейтинг: {clan[2]}\n   👥 Участников: {clan[4]}\n━━━━━━━━━━━━━━━━\n"
        await update.message.reply_text(text)

    @staticmethod
    async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        if not context.args:
            await update.message.reply_text("❌ /report <причина>")
            return
        reason = " ".join(context.args)
        target = update.message.reply_to_message.from_user
        
        chat_id = update.effective_chat.id
        message_id = update.message.reply_to_message.message_id
        try:
            chat = await context.bot.get_chat(chat_id)
            if chat.username:
                message_link = f"https://t.me/{chat.username}/{message_id}"
            else:
                message_link = f"https://t.me/c/{str(chat_id).replace('-100', '')}/{message_id}"
        except:
            message_link = "Недоступна"
        
        db.add_report(update.effective_user.id, target.id, reason, message_link)
        await update.message.reply_text("✅ Жалоба отправлена!")
        
        admins = db.get_all_bot_admins()
        for admin in admins:
            try:
                await context.bot.send_message(
                    admin[0],
                    f"❗️ Новая жалоба!\n\n"
                    f"👤 От: {update.effective_user.first_name}\n"
                    f"🎯 На: {target.first_name}\n"
                    f"📝 Причина: {reason}\n"
                    f"🔗 Ссылка: {message_link}\n\n"
                    f"Ответьте: /reports"
                )
            except:
                pass

    @staticmethod
    async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'ban'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        elif context.args:
            try:
                target = (await context.bot.get_chat_member(chat_id, int(context.args[0]))).user
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return
        else:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Не указана"
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            db.add_punishment(target.id, chat_id, "ban", reason, 0, user.id)
            await update.message.reply_text(f"✅ {target.first_name} забанен!\n📝 Причина: {reason}\n👤 Выдал: {user.first_name}")
        except:
            await update.message.reply_text("❌ Не удалось забанить!")

    @staticmethod
    async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'unban'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        elif context.args:
            try:
                target = (await context.bot.get_chat_member(chat_id, int(context.args[0]))).user
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return
        else:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        try:
            await context.bot.unban_chat_member(chat_id, target.id)
            await update.message.reply_text(f"✅ {target.first_name} разбанен!")
        except:
            await update.message.reply_text("❌ Не удалось разбанить!")

    @staticmethod
    async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'mute'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        elif context.args:
            try:
                target = (await context.bot.get_chat_member(chat_id, int(context.args[0]))).user
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return
        else:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        mute_minutes = 60
        reason = "Не указана"
        if context.args:
            if len(context.args) > 1:
                try:
                    mute_minutes = int(context.args[1])
                except:
                    pass
            if len(context.args) > 2:
                reason = " ".join(context.args[2:])
        try:
            until_date = datetime.now() + timedelta(minutes=mute_minutes)
            await context.bot.restrict_chat_member(chat_id, target.id, until_date=until_date, can_send_messages=False)
            db.add_punishment(target.id, chat_id, "mute", reason, mute_minutes, user.id)
            await update.message.reply_text(f"✅ {target.first_name} замучен на {mute_minutes} минут!\n📝 Причина: {reason}\n👤 Выдал: {user.first_name}")
        except:
            await update.message.reply_text("❌ Не удалось замутить!")

    @staticmethod
    async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'unmute'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        elif context.args:
            try:
                target = (await context.bot.get_chat_member(chat_id, int(context.args[0]))).user
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return
        else:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        try:
            await context.bot.restrict_chat_member(chat_id, target.id, can_send_messages=True)
            await update.message.reply_text(f"✅ {target.first_name} размучен!")
        except:
            await update.message.reply_text("❌ Не удалось размутить!")

    @staticmethod
    async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'warn'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        target = update.message.reply_to_message.from_user
        reason = " ".join(context.args) if context.args else "Не указана"
        
        user_data = db.get_user(target.id)
        current_warnings = user_data[6] if user_data else 0
        new_warnings = current_warnings + 1
        
        db.cursor.execute("UPDATE users SET warnings = ? WHERE user_id = ?", (new_warnings, target.id))
        db.conn.commit()
        
        await update.message.reply_text(f"⚠️ {target.first_name} получил предупреждение!\n📝 Причина: {reason}\n👤 Выдал: {user.first_name}\n📊 Варнов: {new_warnings}/3")
        
        if new_warnings >= 3:
            try:
                await context.bot.ban_chat_member(chat_id, target.id)
                await asyncio.sleep(1)
                await context.bot.unban_chat_member(chat_id, target.id)
                await update.message.reply_text(f"🚫 {target.first_name} кикнут за 3 предупреждения!")
                db.cursor.execute("UPDATE users SET warnings = 0 WHERE user_id = ?", (target.id,))
                db.conn.commit()
            except:
                pass

    @staticmethod
    async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'unwarn'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        target = update.message.reply_to_message.from_user
        db.cursor.execute("UPDATE users SET warnings = warnings - 1 WHERE user_id = ? AND warnings > 0", (target.id,))
        db.conn.commit()
        await update.message.reply_text(f"✅ Предупреждение снято с {target.first_name}!")

    @staticmethod
    async def setadm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'setadm'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /setadm <ID> <уровень 0-10>")
            return
        try:
            target_id = int(context.args[0])
            level = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неверные аргументы!")
            return
        db.add_chat_admin(target_id, chat_id, level, user.id)
        await update.message.reply_text(f"✅ {target_id} назначен админом уровня {level}!")

    @staticmethod
    async def permban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_bot_access(user.id, 'blacklist'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if len(context.args) < 1:
            await update.message.reply_text("❌ /permban <ID> <причина>")
            return
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Не указана"
        db.add_to_blacklist(target_id, reason, user.id)
        await update.message.reply_text(f"✅ {target_id} добавлен в ЧС!\n📝 {reason}")

    @staticmethod
    async def unperm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_bot_access(user.id, 'blacklist'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /unperm <ID>")
            return
        try:
            target_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        db.remove_from_blacklist(target_id)
        await update.message.reply_text(f"✅ {target_id} удален из ЧС!")

    @staticmethod
    async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_bot_access(user.id, 'broadcast'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /broadcast <текст>")
            return
        text = " ".join(context.args)
        users = db.get_all_users()
        sent = 0
        for user_data in users:
            try:
                await context.bot.send_message(user_data[0], f"📨 Рассылка:\n\n{text}")
                sent += 1
            except:
                pass
        await update.message.reply_text(f"✅ Отправлено: {sent}")

    @staticmethod
    async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        is_admin = check_bot_access(user_id, 'view_reports')
        is_agent = check_agent_access(user_id, 'view_questions')
        if not is_admin and not is_agent:
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if is_admin:
            reports = db.get_pending_reports()
            if not reports:
                await update.message.reply_text("✅ Нет новых жалоб!")
                return
            text = "❗️ Жалобы:\n\n"
            for report in reports:
                text += f"🆔 #{report[0]}\n👤 От: {report[7]}\n🎯 На: {report[8]}\n📝 Причина: {report[3]}\n"
                if report[9]:
                    text += f"🔗 Ссылка: {report[9]}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
            text += "\n/answer_report <ID> <ответ> или /reject_report <ID>"
            await update.message.reply_text(text)
        elif is_agent:
            questions = db.get_pending_questions()
            if not questions:
                await update.message.reply_text("✅ Нет новых вопросов!")
                return
            text = "❓ Вопросы:\n\n"
            for question in questions:
                text += f"🆔 #{question[0]}\n👤 От: {question[6]}\n💬 Вопрос: {question[2]}\n━━━━━━━━━━━━━━━━\n"
            text += "\n/answer_question <ID> <ответ> или /reject_question <ID>"
            await update.message.reply_text(text)

    @staticmethod
    async def answer_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_bot_access(user.id, 'view_reports'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /answer_report <ID> <ответ>")
            return
        try:
            report_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        answer_text = " ".join(context.args[1:])
        reports = db.get_pending_reports()
        for report in reports:
            if report[0] == report_id:
                db.update_report_status(report_id, 'answered', user.id)
                try:
                    await context.bot.send_message(report[1], f"✅ Ваша жалоба рассмотрена!\n📝 Ответ: {answer_text}")
                except:
                    pass
                await update.message.reply_text(f"✅ Ответ отправлен!")
                return
        await update.message.reply_text("❌ Жалоба не найдена!")

    @staticmethod
    async def reject_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_bot_access(user.id, 'view_reports'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /reject_report <ID>")
            return
        try:
            report_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        db.update_report_status(report_id, 'rejected', user.id)
        await update.message.reply_text(f"✅ Жалоба #{report_id} отклонена!")

    @staticmethod
    async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_agent_access(user.id, 'answer_questions'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /answer_question <ID> <ответ>")
            return
        try:
            question_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        answer_text = " ".join(context.args[1:])
        questions = db.get_pending_questions()
        for q in questions:
            if q[0] == question_id:
                db.update_question_status(question_id, 'answered', user.id, answer_text)
                try:
                    await context.bot.send_message(q[1], f"❓ Ответ на ваш вопрос:\n\n{answer_text}")
                except:
                    pass
                await update.message.reply_text(f"✅ Ответ отправлен!")
                return
        await update.message.reply_text("❌ Вопрос не найден!")

    @staticmethod
    async def reject_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_agent_access(user.id, 'answer_questions'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /reject_question <ID>")
            return
        try:
            question_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        db.update_question_status(question_id, 'rejected', user.id)
        await update.message.reply_text(f"✅ Вопрос #{question_id} отклонен!")

    @staticmethod
    async def astats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if db.get_bot_admin_level(user.id) < 1:
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        await update.message.reply_text(f"📊 Админ {user.first_name}\n🏆 Уровень: {db.get_bot_admin_level(user.id)}")

    @staticmethod
    async def hstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_agent_access(user.id, 'hstats'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        await update.message.reply_text(f"📊 Агент {user.first_name}\n🏆 Уровень: {db.get_agent_level(user.id)}")

    @staticmethod
    async def give_rep(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not check_bot_access(user.id, 'give_clan_rep'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /give_rep <ID клана> <количество>")
            return
        try:
            clan_id = int(context.args[0])
            rating = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неверные аргументы!")
            return
        clan = db.get_clan_by_id(clan_id)
        if not clan:
            await update.message.reply_text("❌ Клан не найден!")
            return
        db.add_clan_rating(clan_id, rating)
        await update.message.reply_text(f"✅ Клану «{clan[1]}» выдано {rating} рейтинга!")

    @staticmethod
    async def rename_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if db.get_bot_admin_level(user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        if len(context.args) < 3:
            await update.message.reply_text("❌ /rename_rank <bot/agent/chat> <уровень> <название>")
            return
        rank_type = context.args[0].lower()
        try:
            level = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неверный уровень!")
            return
        name = " ".join(context.args[2:])
        if rank_type == 'bot':
            db.update_bot_rank_name(level, name)
            await update.message.reply_text(f"✅ Ранг бота {level} → «{name}»!")
        elif rank_type == 'agent':
            db.update_agent_rank_name(level, name)
            await update.message.reply_text(f"✅ Уровень агента {level} → «{name}»!")
        elif rank_type == 'chat':
            db.update_chat_rank_name(level, name)
            await update.message.reply_text(f"✅ Ранг чата {level} → «{name}»!")
        else:
            await update.message.reply_text("❌ Используйте: bot, agent, chat")

    @staticmethod
    async def accept_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if not clan or clan[2] != user.id:
            await update.message.reply_text("❌ Только лидер!")
            return
        if not context.args:
            await update.message.reply_text("❌ /accept_request <ID>")
            return
        try:
            request_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        requests = db.get_clan_requests(clan[0])
        for req in requests:
            if req[0] == request_id:
                db.update_clan_request(request_id, 'accepted')
                db.join_clan(req[2], clan[0])
                await update.message.reply_text(f"✅ Пользователь {req[2]} принят в клан!")
                try:
                    await context.bot.send_message(req[2], f"✅ Ваша заявка в клан «{clan[1]}» принята!")
                except:
                    pass
                return
        await update.message.reply_text("❌ Заявка не найдена!")

    @staticmethod
    async def reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if not clan or clan[2] != user.id:
            await update.message.reply_text("❌ Только лидер!")
            return
        if not context.args:
            await update.message.reply_text("❌ /reject_request <ID>")
            return
        try:
            request_id = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный ID!")
            return
        requests = db.get_clan_requests(clan[0])
        for req in requests:
            if req[0] == request_id:
                db.update_clan_request(request_id, 'rejected')
                await update.message.reply_text(f"✅ Заявка {request_id} отклонена!")
                try:
                    await context.bot.send_message(req[2], f"❌ Ваша заявка в клан «{clan[1]}» отклонена.")
                except:
                    pass
                return
        await update.message.reply_text("❌ Заявка не найдена!")

    @staticmethod
    async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not context.args:
            await update.message.reply_text("❌ /ask <текст вопроса>")
            return
        question = " ".join(context.args)
        db.add_question(user.id, question)
        await update.message.reply_text("✅ Вопрос отправлен агентам!")
        agents = db.get_all_agents()
        for agent in agents:
            try:
                await context.bot.send_message(
                    agent[0],
                    f"❓ Новый вопрос!\n👤 От: {user.first_name}\n💬 Вопрос: {question}\n\nОтветьте: /reports"
                )
            except:
                pass

    @staticmethod
    async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
        for member in update.message.new_chat_members:
            chat_id = update.effective_chat.id
            welcome_settings = db.get_welcome_settings(chat_id)
            if welcome_settings and welcome_settings[0] == 1:
                welcome_text = welcome_settings[1] or "Добро пожаловать, {name}!"
                welcome_text = welcome_text.replace("{name}", member.first_name)
                welcome_text = welcome_text.replace("{id}", str(member.id))
                welcome_text = welcome_text.replace("{chat}", update.effective_chat.title)
                await update.message.reply_text(welcome_text)

    @staticmethod
    async def antispam_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_chat:
            return
        user = update.effective_user
        chat_id = update.effective_chat.id
        if db.get_chat_admin_level(user.id, chat_id) >= 5:
            return
        antispam_settings = db.get_antispam_settings(chat_id)
        if not antispam_settings or antispam_settings[0] != 1:
            return
        antispam_seconds = antispam_settings[1] if antispam_settings[1] else 5
        antispam_max_messages = db.get_antispam_max_messages(chat_id)
        db.add_antispam_message(user.id, chat_id)
        recent = db.get_recent_messages(user.id, chat_id, antispam_seconds)
        if recent > antispam_max_messages:
            try:
                await context.bot.ban_chat_member(chat_id, user.id)
                await asyncio.sleep(1)
                await context.bot.unban_chat_member(chat_id, user.id)
                await update.message.reply_text(f"🚫 {user.first_name} кикнут за спам!\n📊 {recent} сообщений за {antispam_seconds} сек")
            except:
                pass
                
                # ЧАСТЬ 4: Handlers (button_handler - обработчик кнопок)
    @staticmethod
    async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user

        if data == "back_to_start":
            db.add_user(user.id, user.username, user.first_name)
            bot_rank_level = db.get_bot_admin_level(user.id)
            
            is_chat_owner = False
            if update.effective_chat.type != 'private':
                chat_id = update.effective_chat.id
                try:
                    admins = await context.bot.get_chat_administrators(chat_id)
                    for admin in admins:
                        if admin.status == 'creator' and admin.user.id == user.id:
                            is_chat_owner = True
                            break
                except:
                    pass
            
            bot_rank_name = db.get_bot_rank_name(bot_rank_level)
            text = f"""👋 Добро пожаловать в Fluxy | Чат-менеджер.
━━━━━━━━━━━━━━━━

🆔 Ваш ID: {user.id}
🎖️ Ваш ранг: {bot_rank_name}

━━━━━━━━━━━━━━━━
Для продолжения нажмите на кнопку ниже ⬇️"""
            
            if bot_rank_level >= 1 and is_chat_owner:
                await query.edit_message_text(text, reply_markup=Keyboards.main_menu_with_both())
            elif bot_rank_level >= 1:
                await query.edit_message_text(text, reply_markup=Keyboards.main_menu_with_admin())
            elif is_chat_owner:
                await query.edit_message_text(text, reply_markup=Keyboards.main_menu_with_chat_admin())
            else:
                await query.edit_message_text(text, reply_markup=Keyboards.main_menu())

        elif data == "admin_panel":
            if db.get_bot_admin_level(user.id) < 1:
                await query.answer("❌ Нет доступа!")
                return
            await query.edit_message_text("⭐️ Админ панель бота", reply_markup=Keyboards.admin_panel())

        elif data == "chat_panel":
            if update.effective_chat.type == 'private':
                await query.answer("❌ Только в группе!")
                return
            chat_id = update.effective_chat.id
            db.add_chat(chat_id, update.effective_chat.title or "Чат")
            try:
                admins = await context.bot.get_chat_administrators(chat_id)
                is_owner = False
                for admin in admins:
                    if admin.status == 'creator':
                        db.update_chat_owner(chat_id, admin.user.id)
                        if admin.user.id == user.id:
                            is_owner = True
                        break
                if is_owner or db.get_bot_admin_level(user.id) >= 10:
                    await query.edit_message_text("👑 Админ панель чата", reply_markup=Keyboards.chat_panel())
                    return
                await query.answer("❌ Только для владельца чата!")
                return
            except:
                await query.answer("❌ Ошибка проверки прав!")
                return

        elif data == "profile":
            db.add_user(user.id, user.username, user.first_name)
            clan = db.get_user_clan(user.id)
            text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}
🛡️ Клан: {clan[1] if clan else 'Нет'}
🏆 Рейтинг: {clan[3] if clan else 0}"""
            await query.edit_message_text(text, reply_markup=Keyboards.profile_menu())

        elif data == "clan_menu":
            clan = db.get_user_clan(user.id)
            if clan:
                text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan[0]}
🛡 Название: {clan[1]}
🏆 Рейтинг: {clan[3]}
👥 Участников: {clan[6]}
🏅 Побед: {clan[7]}
💀 Поражений: {clan[8]}

━━━━━━━━━━━━━━━━
Выберите действие:"""
                await query.edit_message_text(text, reply_markup=Keyboards.my_clan_menu())
            else:
                text = "🛡 Кланы\n━━━━━━━━━━━━━━━━\n\nВыберите действие:"
                await query.edit_message_text(text, reply_markup=Keyboards.clan_menu())

        elif data == "create_clan_btn":
            await query.edit_message_text(
                "➕ Создание клана\n━━━━━━━━━━━━━━━━\n\nОтправьте команду:\n/create_clan <название клана>",
                reply_markup=Keyboards.back_to_start()
            )

        elif data == "clan_list_btn":
            clans = db.get_top_clans(15)
            text = "📋 Топ 15 кланов:\n━━━━━━━━━━━━━━━━\n\n"
            if not clans:
                text += "Нет кланов"
            for i, clan in enumerate(clans, 1):
                text += f"{i}. 🛡 {clan[1]}\n   🆔 ID: {clan[0]}\n   🏆 Рейтинг: {clan[2]}\n   👥 Участников: {clan[4]}\n━━━━━━━━━━━━━━━━\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "find_clan_btn":
            context.user_data['waiting_clan_id'] = True
            await query.edit_message_text(
                "🔍 Поиск клана\n━━━━━━━━━━━━━━━━\n\nОтправьте ID клана для вступления:",
                reply_markup=Keyboards.back_to_start()
            )
            return WAITING_FOR_CLAN_ID

        elif data == "help_menu":
            await query.edit_message_text("❓ Помощь\nВыберите тип:", reply_markup=Keyboards.help_menu())

        elif data == "report":
            await query.edit_message_text("❗️ Жалоба\nОтветьте на сообщение: /report <причина>", reply_markup=Keyboards.back_to_start())

        elif data == "question":
            await query.edit_message_text("❓ Вопрос\nОтправьте: /ask <текст>", reply_markup=Keyboards.back_to_start())

        elif data == "commands_menu":
            text = """📋 Команды бота:
━━━━━━━━━━━━━━━━

/start - Показать главное меню
/profile - Показать ваш профиль
/ping - Проверить пинг бота
/id - Показать ID пользователя

🛡 Кланы:
/clan - Открыть меню клана
/clan_top - Топ кланов
/clan_bonus - Получить бонус клана
/create_clan - Создать клан
/join_clan - Вступить в клан
/leave_clan - Покинуть клан

👮 Администрирование:
/ban - Забанить пользователя
/unban - Разбанить пользователя
/mute - Замутить пользователя
/unmute - Размутить пользователя
/warn - Выдать предупреждение
/unwarn - Снять предупреждение
/setadm - Назначить админа чата

📝 Прочее:
/report - Отправить жалобу
/stats - Статистика пользователя
/ask - Задать вопрос"""
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "agents_list":
            agents = db.get_all_agents()
            text = "🔰 Агенты поддержки:\n━━━━━━━━━━━━━━━━\n\n"
            if not agents:
                text += "Нет агентов"
            else:
                for agent in agents:
                    status = "🟢 Онлайн" if agent[2] == 'online' else "🔴 Оффлайн"
                    agent_name = agent[6] if agent[6] else "Неизвестный"
                    agent_username = f"(@{agent[5]})" if agent[5] else ""
                    agent_level = db.get_agent_rank_name(agent[1])
                    text += f"{status}\n👤 {agent_name} {agent_username}\n🏆 Уровень: {agent_level}\n━━━━━━━━━━━━━━━━\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "admins_list":
            if not check_bot_access(user.id, 'manage_admins'):
                await query.answer("❌ Нет доступа!")
                return
            admins = db.get_all_bot_admins()
            text = f"👥 Админы:\n\n👑 Основатель: {SUPER_ADMIN_ID}\n"
            for admin in admins:
                text += f"👤 {admin[5]} - {db.get_bot_rank_name(admin[1])}\n"
            keyboard = [
                [InlineKeyboardButton("➕ Добавить", callback_data="add_admin"), InlineKeyboardButton("➖ Удалить", callback_data="remove_admin")],
                [InlineKeyboardButton("🔄 Изменить уровень", callback_data="change_admin_level")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "agents_manage":
            if not check_bot_access(user.id, 'manage_agents'):
                await query.answer("❌ Нет доступа!")
                return
            await query.edit_message_text("🔰 Управление агентами", reply_markup=Keyboards.agent_manage_menu())

        elif data == "bot_blacklist":
            if not check_bot_access(user.id, 'blacklist'):
                await query.answer("❌ Нет доступа!")
                return
            blacklist = db.get_blacklist()
            text = "🚫 Черный список:\n\n"
            for user_data in blacklist:
                text += f"👤 {user_data[6]} - {user_data[1]}\n"
            keyboard = [
                [InlineKeyboardButton("➕ Добавить", callback_data="blacklist_add"), InlineKeyboardButton("➖ Удалить", callback_data="blacklist_remove")],
                [InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "bot_stats":
            if not check_bot_access(user.id, 'stats'):
                await query.answer("❌ Нет доступа!")
                return
            total_users, total_chats, total_clans = db.get_total_stats()
            text = f"📊 Статистика:\n👥 Пользователей: {total_users}\n💬 Чатов: {total_chats}\n🛡 Кланов: {total_clans}"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "all_chats":
            if not check_bot_access(user.id, 'view_chats'):
                await query.answer("❌ Нет доступа!")
                return
            chats = db.get_all_chats()
            text = f"🗂 Чаты ({len(chats)}):\n\n"
            for chat in chats:
                text += f"💬 {chat[1]} - {chat[0]}\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "all_commands":
            text = """📋 Все команды бота:
━━━━━━━━━━━━━━━━

/start - Показать главное меню
/help - Показать справку
/profile - Показать профиль
/ping - Проверить пинг
/id - Показать ID

/clan - Меню клана
/clan_top - Топ кланов
/clan_bonus - Бонус клана
/create_clan - Создать клан
/join_clan - Вступить в клан
/leave_clan - Покинуть клан

/ban - Забанить
/unban - Разбанить
/mute - Замутить
/unmute - Размутить
/warn - Предупредить
/unwarn - Снять предупреждение
/setadm - Назначить админа

/permban - Добавить в ЧС
/unperm - Удалить из ЧС
/broadcast - Рассылка
/reports - Просмотр жалоб/вопросов
/answer_report - Ответить на жалобу
/reject_report - Отклонить жалобу
/answer_question - Ответить на вопрос
/reject_question - Отклонить вопрос
/astats - Статистика админа
/hstats - Статистика агента
/give_rep - Выдать репутацию клану
/rename_rank - Переименовать ранг
/accept_request - Принять заявку
/reject_request - Отклонить заявку
/ask - Задать вопрос"""
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "broadcast_menu":
            if not check_bot_access(user.id, 'broadcast'):
                await query.answer("❌ Нет доступа!")
                return
            await query.edit_message_text("📨 Рассылка", reply_markup=Keyboards.broadcast_menu())

        elif data == "give_clan_rep":
            if not check_bot_access(user.id, 'give_clan_rep'):
                await query.answer("❌ Нет доступа!")
                return
            await query.edit_message_text("⭐️ Выдача репутации\n/give_rep <ID клана> <количество>", reply_markup=Keyboards.back_to_start())

        elif data == "bot_rank_settings":
            if db.get_bot_admin_level(user.id) < 10:
                await query.answer("❌ Только Основатель!")
                return
            text = "⚙️ Права рангов бота\nВыберите ранг:"
            keyboard = []
            for level in range(10, -1, -1):
                rank_name = db.get_bot_rank_name(level)
                keyboard.append([InlineKeyboardButton(f"{level}. {rank_name}", callback_data=f"edit_bot_rank_{level}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("edit_bot_rank_"):
            if db.get_bot_admin_level(user.id) < 10:
                await query.answer("❌ Только Основатель!")
                return
            level = int(data.replace("edit_bot_rank_", ""))
            rank_name = db.get_bot_rank_name(level)
            text = f"⚙️ Права ранга: {rank_name}\nНажмите на функцию:"
            functions = {'manage_admins': '👥 Управление админами', 'manage_agents': '🔰 Управление агентами', 'blacklist': '🚫 Черный список', 'give_clan_rep': '⭐️ Выдача репутации', 'view_chats': '🗂 Просмотр чатов', 'stats': '📊 Статистика', 'broadcast': '📨 Рассылка', 'view_reports': '❗️ Жалобы', 'give_reward': '🎁 Награды'}
            keyboard = []
            for func, display_name in functions.items():
                required = db.get_access_level('bot', func)
                status = "✅" if level >= required else "❌"
                keyboard.append([InlineKeyboardButton(f"{status} {display_name} ({required}+)", callback_data=f"toggle_bot_access_{level}_{func}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="bot_rank_settings")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("toggle_bot_access_"):
            if db.get_bot_admin_level(user.id) < 10:
                await query.answer("❌ Только Основатель!")
                return
            parts = data.replace("toggle_bot_access_", "").split("_")
            level = int(parts[0])
            func = "_".join(parts[1:])
            current = db.get_access_level('bot', func)
            if current == level:
                db.set_access_level('bot', func, 10)
                await query.answer("❌ Доступ убран")
            else:
                db.set_access_level('bot', func, level)
                await query.answer(f"✅ Доступ для {level}+")
            rank_name = db.get_bot_rank_name(level)
            text = f"⚙️ Права ранга: {rank_name}\nНажмите на функцию:"
            functions = {'manage_admins': '👥 Управление админами', 'manage_agents': '🔰 Управление агентами', 'blacklist': '🚫 Черный список', 'give_clan_rep': '⭐️ Выдача репутации', 'view_chats': '🗂 Просмотр чатов', 'stats': '📊 Статистика', 'broadcast': '📨 Рассылка', 'view_reports': '❗️ Жалобы', 'give_reward': '🎁 Награды'}
            keyboard = []
            for func, display_name in functions.items():
                required = db.get_access_level('bot', func)
                status = "✅" if level >= required else "❌"
                keyboard.append([InlineKeyboardButton(f"{status} {display_name} ({required}+)", callback_data=f"toggle_bot_access_{level}_{func}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="bot_rank_settings")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "agent_settings":
            if db.get_bot_admin_level(user.id) < 10:
                await query.answer("❌ Только Основатель!")
                return
            text = "⚙️ Права уровней АП\nВыберите уровень:"
            keyboard = []
            for level in range(3, 0, -1):
                keyboard.append([InlineKeyboardButton(f"{level}. {db.get_agent_rank_name(level)}", callback_data=f"edit_agent_level_{level}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("edit_agent_level_"):
            if db.get_bot_admin_level(user.id) < 10:
                await query.answer("❌ Только Основатель!")
                return
            level = int(data.replace("edit_agent_level_", ""))
            agent_name = db.get_agent_rank_name(level)
            text = f"⚙️ Права уровня: {agent_name}\nНажмите на функцию:"
            functions = {'view_questions': '❓ Просмотр вопросов', 'answer_questions': '✉️ Ответ на вопросы', 'hstats': '📊 Статистика агента'}
            keyboard = []
            for func, display_name in functions.items():
                required = db.get_access_level('agent', func)
                status = "✅" if level >= required else "❌"
                keyboard.append([InlineKeyboardButton(f"{status} {display_name} ({required}+)", callback_data=f"toggle_agent_access_{level}_{func}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="agent_settings")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("toggle_agent_access_"):
            if db.get_bot_admin_level(user.id) < 10:
                await query.answer("❌ Только Основатель!")
                return
            parts = data.replace("toggle_agent_access_", "").split("_")
            level = int(parts[0])
            func = "_".join(parts[1:])
            current = db.get_access_level('agent', func)
            if current == level:
                db.set_access_level('agent', func, 3)
                await query.answer("❌ Доступ убран")
            else:
                db.set_access_level('agent', func, level)
                await query.answer(f"✅ Доступ для {level}+")
            agent_name = db.get_agent_rank_name(level)
            text = f"⚙️ Права уровня: {agent_name}\nНажмите на функцию:"
            functions = {'view_questions': '❓ Просмотр вопросов', 'answer_questions': '✉️ Ответ на вопросы', 'hstats': '📊 Статистика агента'}
            keyboard = []
            for func, display_name in functions.items():
                required = db.get_access_level('agent', func)
                status = "✅" if level >= required else "❌"
                keyboard.append([InlineKeyboardButton(f"{status} {display_name} ({required}+)", callback_data=f"toggle_agent_access_{level}_{func}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="agent_settings")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "chat_rank_settings":
            if update.effective_chat.type == 'private':
                await query.answer("❌ Только в группе!")
                return
            chat_id = update.effective_chat.id
            try:
                admins = await context.bot.get_chat_administrators(chat_id)
                is_owner = False
                for admin in admins:
                    if admin.status == 'creator':
                        db.update_chat_owner(chat_id, admin.user.id)
                        if admin.user.id == user.id:
                            is_owner = True
                        break
                if is_owner:
                    user_level = 10
                else:
                    user_level = db.get_chat_admin_level(user.id, chat_id)
                if user_level < 10 and db.get_bot_admin_level(user.id) < 10:
                    await query.answer("❌ Только Владелец чата!")
                    return
                text = "⚙️ Права рангов чата\nВыберите ранг:"
                keyboard = []
                for level in range(10, -1, -1):
                    keyboard.append([InlineKeyboardButton(f"{level}. {db.get_chat_rank_name(level)}", callback_data=f"edit_chat_rank_{level}")])
                keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="chat_panel")])
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            except:
                await query.answer("❌ Ошибка!")
                return

        elif data.startswith("edit_chat_rank_"):
            level = int(data.replace("edit_chat_rank_", ""))
            rank_name = db.get_chat_rank_name(level)
            text = f"⚙️ Права ранга: {rank_name}\nНажмите на функцию:"
            functions = {'ban': '🔨 Бан', 'unban': '🔓 Разбан', 'mute': '🔇 Мут', 'unmute': '🔊 Размут', 'warn': '⚠️ Предупреждение', 'unwarn': '✅ Снятие предупреждения', 'setadm': '👑 Назначение админов', 'welcome_settings': '👋 Приветствие', 'antispam_settings': '🚫 Антиспам'}
            keyboard = []
            for func, display_name in functions.items():
                required = db.get_access_level('chat', func)
                status = "✅" if level >= required else "❌"
                keyboard.append([InlineKeyboardButton(f"{status} {display_name} ({required}+)", callback_data=f"toggle_chat_access_{level}_{func}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="chat_rank_settings")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data.startswith("toggle_chat_access_"):
            parts = data.replace("toggle_chat_access_", "").split("_")
            level = int(parts[0])
            func = "_".join(parts[1:])
            current = db.get_access_level('chat', func)
            if current == level:
                db.set_access_level('chat', func, 10)
                await query.answer("❌ Доступ убран")
            else:
                db.set_access_level('chat', func, level)
                await query.answer(f"✅ Доступ для {level}+")
            rank_name = db.get_chat_rank_name(level)
            text = f"⚙️ Права ранга: {rank_name}\nНажмите на функцию:"
            functions = {'ban': '🔨 Бан', 'unban': '🔓 Разбан', 'mute': '🔇 Мут', 'unmute': '🔊 Размут', 'warn': '⚠️ Предупреждение', 'unwarn': '✅ Снятие предупреждения', 'setadm': '👑 Назначение админов', 'welcome_settings': '👋 Приветствие', 'antispam_settings': '🚫 Антиспам'}
            keyboard = []
            for func, display_name in functions.items():
                required = db.get_access_level('chat', func)
                status = "✅" if level >= required else "❌"
                keyboard.append([InlineKeyboardButton(f"{status} {display_name} ({required}+)", callback_data=f"toggle_chat_access_{level}_{func}")])
            keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="chat_rank_settings")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "welcome_settings":
            if update.effective_chat.type == 'private':
                await query.answer("❌ Только в группе!")
                return
            chat_id = update.effective_chat.id
            if not check_chat_access(user.id, chat_id, 'welcome_settings'):
                await query.answer("❌ Нет доступа!")
                return
            welcome_settings = db.get_welcome_settings(chat_id)
            welcome_enabled = welcome_settings[0] if welcome_settings else 0
            await query.edit_message_text("👋 Настройка приветствия", reply_markup=Keyboards.welcome_settings_menu(welcome_enabled))

        elif data == "toggle_welcome":
            chat_id = update.effective_chat.id
            welcome_settings = db.get_welcome_settings(chat_id)
            current = welcome_settings[0] if welcome_settings else 0
            db.enable_welcome(chat_id, not current)
            welcome_settings = db.get_welcome_settings(chat_id)
            welcome_enabled = welcome_settings[0] if welcome_settings else 0
            await query.edit_message_text("👋 Настройка приветствия", reply_markup=Keyboards.welcome_settings_menu(welcome_enabled))

        elif data == "edit_welcome_text":
            chat_id = update.effective_chat.id
            context.user_data['editing_welcome'] = chat_id
            await query.edit_message_text("📝 Отправьте текст приветствия:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_WELCOME_TEXT

        elif data == "show_welcome":
            chat_id = update.effective_chat.id
            welcome_settings = db.get_welcome_settings(chat_id)
            if welcome_settings:
                welcome_enabled = welcome_settings[0]
                welcome_text = welcome_settings[1]
                if welcome_enabled == 1 and welcome_text:
                    text = f"👁 Текущее приветствие:\n━━━━━━━━━━━━━━━━\n\n{welcome_text}"
                else:
                    text = "❌ Приветствие не настроено или выключено"
            else:
                text = "❌ Приветствие не настроено"
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="welcome_settings")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "antispam_settings":
            if update.effective_chat.type == 'private':
                await query.answer("❌ Только в группе!")
                return
            chat_id = update.effective_chat.id
            if not check_chat_access(user.id, chat_id, 'antispam_settings'):
                await query.answer("❌ Нет доступа!")
                return
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_seconds = antispam_settings[1] if antispam_settings else 5
            antispam_max_messages = db.get_antispam_max_messages(chat_id)
            await query.edit_message_text("🚫 Настройка антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max_messages))

        elif data == "toggle_antispam":
            chat_id = update.effective_chat.id
            antispam_settings = db.get_antispam_settings(chat_id)
            current = antispam_settings[0] if antispam_settings else 0
            db.enable_antispam(chat_id, not current)
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_seconds = antispam_settings[1] if antispam_settings else 5
            antispam_max_messages = db.get_antispam_max_messages(chat_id)
            await query.edit_message_text("🚫 Настройка антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max_messages))

        elif data == "change_antispam_interval":
            await query.edit_message_text("⏱ Выберите интервал:", reply_markup=Keyboards.antispam_interval_menu())

        elif data == "change_antispam_messages":
            await query.edit_message_text("📊 Выберите максимальное количество сообщений:", reply_markup=Keyboards.antispam_messages_menu())

        elif data.startswith("set_antispam_"):
            chat_id = update.effective_chat.id
            seconds = int(data.replace("set_antispam_", ""))
            db.set_antispam_seconds(chat_id, seconds)
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_seconds = antispam_settings[1] if antispam_settings else 5
            antispam_max_messages = db.get_antispam_max_messages(chat_id)
            await query.edit_message_text("🚫 Настройка антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max_messages))

        elif data.startswith("set_msg_"):
            chat_id = update.effective_chat.id
            messages = int(data.replace("set_msg_", ""))
            db.set_antispam_max_messages(chat_id, messages)
            await query.answer(f"✅ Максимум: {messages} сообщений")
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_seconds = antispam_settings[1] if antispam_settings else 5
            antispam_max_messages = db.get_antispam_max_messages(chat_id)
            await query.edit_message_text("🚫 Настройка антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max_messages))

        elif data == "bot_ranks":
            text = "🏆 Ранги бота:\n\n"
            for level in range(10, -1, -1):
                text += f"{level}. {db.get_bot_rank_name(level)}\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "agent_levels":
            text = "👥 Уровни агентов:\n\n"
            for level in range(3, 0, -1):
                text += f"{level}. {db.get_agent_rank_name(level)}\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "super_admin":
            if db.get_bot_admin_level(user.id) < 10:
                await query.answer("❌ Только Основатель!")
                return
            await query.edit_message_text(f"👑 Супер админ: {SUPER_ADMIN_ID}", reply_markup=Keyboards.back_to_start())

        elif data == "bot_rank_names":
            await query.edit_message_text("📝 Переименование рангов\n/rename_rank bot <уровень> <название>", reply_markup=Keyboards.back_to_start())

        elif data == "agent_rank_names":
            await query.edit_message_text("📝 Переименование уровней АП\n/rename_rank agent <уровень> <название>", reply_markup=Keyboards.back_to_start())

        elif data == "chat_rank_names":
            await query.edit_message_text("📝 Переименование рангов чата\n/rename_rank chat <уровень> <название>", reply_markup=Keyboards.back_to_start())

        elif data == "chat_admins_list":
            chat_id = update.effective_chat.id
            admins = db.get_chat_admins(chat_id)
            text = "👥 Админы чата:\n\n"
            for admin in admins:
                text += f"👤 {admin[5]} - {db.get_chat_rank_name(admin[1])}\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "clan_members":
            clan = db.get_user_clan(user.id)
            if not clan:
                await query.edit_message_text("❌ Вы не в клане!")
                return
            members = db.get_clan_members(clan[0])
            text = f"👥 Участники {clan[1]}:\n\n"
            for member in members:
                leader = "👑 " if member[0] == clan[2] else ""
                text += f"{leader}👤 {member[2]}\n"
            keyboard = [[InlineKeyboardButton("➕ Пригласить", callback_data="invite_member")], [InlineKeyboardButton("⬅️ Назад", callback_data="clan_menu")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "clan_top":
            clans = db.get_top_clans(15)
            text = "🏆 Топ 15 кланов:\n━━━━━━━━━━━━━━━━\n\n"
            if not clans:
                text += "Нет кланов"
            for i, clan in enumerate(clans, 1):
                text += f"{i}. 🛡 {clan[1]}\n   🏆 Рейтинг: {clan[2]}\n   👥 Участников: {clan[4]}\n━━━━━━━━━━━━━━━━\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "clan_entry":
            clan = db.get_user_clan(user.id)
            if not clan or clan[2] != user.id:
                await query.answer("❌ Только лидер!")
                return
            await query.edit_message_text("🔒 Настройка входа", reply_markup=Keyboards.clan_entry_menu())

        elif data == "entry_open":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                db.update_clan_entry_type(clan[0], 'open')
                await query.edit_message_text("✅ Вход открыт!")
            else:
                await query.answer("❌ Только лидер!")

        elif data == "entry_closed":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                db.update_clan_entry_type(clan[0], 'closed')
                await query.edit_message_text("✅ Вход закрыт!")
            else:
                await query.answer("❌ Только лидер!")

        elif data == "entry_request":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                db.update_clan_entry_type(clan[0], 'request')
                await query.edit_message_text("✅ Вход по заявкам!")
            else:
                await query.answer("❌ Только лидер!")

        elif data == "clan_messages":
            clan = db.get_user_clan(user.id)
            if not clan:
                await query.edit_message_text("❌ Вы не в клане!")
                return
            messages = db.get_clan_messages(clan[0])
            text = f"✉️ Сообщения {clan[1]}:\n\n"
            if not messages:
                text += "Нет сообщений"
            for msg in messages[:10]:
                text += f"📨 От: {msg[8]} - {msg[4]}\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "clan_requests":
            clan = db.get_user_clan(user.id)
            if not clan or clan[2] != user.id:
                await query.answer("❌ Только лидер!")
                return
            requests = db.get_clan_requests(clan[0])
            text = f"📋 Заявки:\n\n"
            if not requests:
                text += "Нет заявок"
            for req in requests:
                text += f"👤 {req[7]} (ID: {req[2]})\n✅ /accept_request {req[0]}\n❌ /reject_request {req[0]}\n━━━━━━━━━━━━━━━━\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "declare_war":
            clan = db.get_user_clan(user.id)
            if not clan or clan[2] != user.id:
                await query.answer("❌ Только лидер!")
                return
            context.user_data['war_clan_id'] = True
            await query.edit_message_text(
                f"⚔ Объявление войны\n━━━━━━━━━━━━━━━━\n\nВаш клан: {clan[1]}\nВаш рейтинг: {clan[3]}\n\nШансы:\n• Базовый: 50%\n• +5% за 1000 рейтинга\n• Максимум: 75%\n\nОтправьте ID клана противника:",
                reply_markup=Keyboards.back_to_start()
            )
            return WAITING_FOR_WAR_CLAN_ID

        elif data == "message_clan":
            clan = db.get_user_clan(user.id)
            if not clan:
                await query.edit_message_text("❌ Вы не в клане!")
                return
            context.user_data['clan_msg_to'] = True
            await query.edit_message_text("📩 Отправьте ID клана получателя:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_CLAN_MSG_CLAN

        elif data == "invite_member":
            clan = db.get_user_clan(user.id)
            if not clan or clan[2] != user.id:
                await query.answer("❌ Только лидер!")
                return
            context.user_data['waiting_invite'] = True
            await query.edit_message_text("➕ Отправьте ID пользователя:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_INVITE_USER

        elif data == "my_rewards":
            rewards = db.get_user_rewards(user.id)
            text = "🏆 Награды:\n\n"
            if not rewards:
                text += "Нет наград"
            for reward in rewards:
                text += f"🎁 {reward[3]} от {reward[8]}\n"
            await query.edit_message_text(text, reply_markup=Keyboards.back_to_start())

        elif data == "give_reward":
            await query.edit_message_text("🎁 Выдача награды\nОтветьте на сообщение пользователя и напишите текст награды", reply_markup=Keyboards.back_to_start())

        elif data == "add_admin":
            if not check_bot_access(user.id, 'manage_admins'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'add_admin'
            await query.edit_message_text("➕ Отправьте ID админа:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_ADMIN_ID

        elif data == "remove_admin":
            if not check_bot_access(user.id, 'manage_admins'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'remove_admin'
            await query.edit_message_text("➖ Отправьте ID админа:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_ADMIN_ID

        elif data == "change_admin_level":
            if not check_bot_access(user.id, 'manage_admins'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'change_admin_level'
            await query.edit_message_text("🔄 Отправьте ID админа:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_ADMIN_ID

        elif data == "add_agent":
            if not check_bot_access(user.id, 'manage_agents'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'add_agent'
            await query.edit_message_text("➕ Отправьте ID агента:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_AGENT_ID

        elif data == "remove_agent":
            if not check_bot_access(user.id, 'manage_agents'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'remove_agent'
            await query.edit_message_text("➖ Отправьте ID агента:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_AGENT_ID

        elif data == "change_agent_level":
            if not check_bot_access(user.id, 'manage_agents'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'change_agent_level'
            await query.edit_message_text("🔄 Отправьте ID агента:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_AGENT_ID

        elif data == "blacklist_add":
            if not check_bot_access(user.id, 'blacklist'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'blacklist_add'
            await query.edit_message_text("➕ Отправьте ID пользователя:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_BLACKLIST_ID

        elif data == "blacklist_remove":
            if not check_bot_access(user.id, 'blacklist'):
                await query.answer("❌ Нет доступа!")
                return
            context.user_data['action'] = 'blacklist_remove'
            await query.edit_message_text("➖ Отправьте ID пользователя:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_BLACKLIST_ID

        elif data == "broadcast_pm":
            context.user_data['broadcast_type'] = 'pm'
            await query.edit_message_text("📨 Отправьте текст рассылки:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_BROADCAST_TEXT

        elif data == "broadcast_chats":
            context.user_data['broadcast_type'] = 'chats'
            await query.edit_message_text("📨 Отправьте текст рассылки:", reply_markup=Keyboards.back_to_start())
            return WAITING_FOR_BROADCAST_TEXT
            
            # ЧАСТЬ 5: Handlers (text_handler) + main()
    @staticmethod
    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text

        if 'editing_welcome' in context.user_data:
            chat_id = context.user_data['editing_welcome']
            db.set_welcome_text(chat_id, text)
            await update.message.reply_text(f"✅ Приветствие установлено!")
            context.user_data.pop('editing_welcome', None)
            return ConversationHandler.END

        if 'waiting_clan_id' in context.user_data:
            try:
                clan_id = int(text)
                clan = db.get_clan_by_id(clan_id)
                if not clan:
                    await update.message.reply_text("❌ Клан не найден!")
                    return WAITING_FOR_CLAN_ID
                user_clan = db.get_user_clan(user.id)
                if user_clan:
                    await update.message.reply_text("❌ Вы уже состоите в клане!")
                    context.user_data.pop('waiting_clan_id', None)
                    return ConversationHandler.END
                if clan[4] == 'closed':
                    await update.message.reply_text("❌ Вход в клан закрыт!")
                    context.user_data.pop('waiting_clan_id', None)
                    return ConversationHandler.END
                if clan[4] == 'request':
                    db.add_clan_request(clan_id, user.id)
                    await update.message.reply_text(f"✅ Заявка в клан «{clan[1]}» отправлена!")
                    context.user_data.pop('waiting_clan_id', None)
                    return ConversationHandler.END
                db.join_clan(user.id, clan_id)
                await update.message.reply_text(f"✅ Вы вступили в клан «{clan[1]}»!")
                context.user_data.pop('waiting_clan_id', None)
                return ConversationHandler.END
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_CLAN_ID

        if 'action' in context.user_data:
            action = context.user_data['action']

            if action == 'add_admin':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'add_admin_level'
                    await update.message.reply_text("Отправьте уровень (1-9):")
                    return WAITING_FOR_ADMIN_LEVEL
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID

            elif action == 'add_admin_level':
                try:
                    level = int(text)
                    target_id = context.user_data.get('target_id')
                    db.add_bot_admin(target_id, level, user.id)
                    await update.message.reply_text(f"✅ Админ {target_id} добавлен!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_ADMIN_LEVEL

            elif action == 'remove_admin':
                try:
                    target_id = int(text)
                    db.remove_bot_admin(target_id)
                    await update.message.reply_text(f"✅ Админ {target_id} удален!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID

            elif action == 'change_admin_level':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'change_admin_level_value'
                    await update.message.reply_text("Отправьте новый уровень (1-9):")
                    return WAITING_FOR_ADMIN_LEVEL
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID

            elif action == 'change_admin_level_value':
                try:
                    level = int(text)
                    target_id = context.user_data.get('target_id')
                    db.update_bot_admin_level(target_id, level)
                    await update.message.reply_text(f"✅ Уровень изменен на {level}!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_ADMIN_LEVEL

            elif action == 'add_agent':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'add_agent_level'
                    await update.message.reply_text("Отправьте уровень (1-3):")
                    return WAITING_FOR_AGENT_LEVEL
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID

            elif action == 'add_agent_level':
                try:
                    level = int(text)
                    target_id = context.user_data.get('target_id')
                    db.add_agent(target_id, level)
                    await update.message.reply_text(f"✅ Агент {target_id} добавлен!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_AGENT_LEVEL

            elif action == 'remove_agent':
                try:
                    target_id = int(text)
                    db.remove_agent(target_id)
                    await update.message.reply_text(f"✅ Агент {target_id} удален!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID

            elif action == 'change_agent_level':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'change_agent_level_value'
                    await update.message.reply_text("Отправьте новый уровень (1-3):")
                    return WAITING_FOR_AGENT_LEVEL
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID

            elif action == 'change_agent_level_value':
                try:
                    level = int(text)
                    target_id = context.user_data.get('target_id')
                    db.update_agent_level(target_id, level)
                    await update.message.reply_text(f"✅ Уровень изменен на {level}!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_AGENT_LEVEL

            elif action == 'blacklist_add':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'blacklist_add_reason'
                    await update.message.reply_text("Отправьте причину:")
                    return WAITING_FOR_BLACKLIST_REASON
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_BLACKLIST_ID

            elif action == 'blacklist_add_reason':
                target_id = context.user_data.get('target_id')
                db.add_to_blacklist(target_id, text, user.id)
                await update.message.reply_text(f"✅ {target_id} в ЧС!")
                context.user_data.clear()
                return ConversationHandler.END

            elif action == 'blacklist_remove':
                try:
                    target_id = int(text)
                    db.remove_from_blacklist(target_id)
                    await update.message.reply_text(f"✅ {target_id} удален из ЧС!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_BLACKLIST_ID

        if 'broadcast_type' in context.user_data:
            broadcast_type = context.user_data['broadcast_type']
            sent = 0
            if broadcast_type == 'pm':
                users = db.get_all_users()
                for user_data in users:
                    try:
                        await context.bot.send_message(user_data[0], f"📨 Рассылка:\n\n{text}")
                        sent += 1
                    except:
                        pass
            elif broadcast_type == 'chats':
                chats = db.get_all_chats()
                for chat in chats:
                    try:
                        await context.bot.send_message(chat[0], f"📨 Рассылка:\n\n{text}")
                        sent += 1
                    except:
                        pass
            await update.message.reply_text(f"✅ Отправлено: {sent}")
            context.user_data.clear()
            return ConversationHandler.END

        if 'war_clan_id' in context.user_data:
            try:
                enemy_clan_id = int(text)
                clan = db.get_user_clan(user.id)
                enemy_clan = db.get_clan_by_id(enemy_clan_id)
                if not enemy_clan:
                    await update.message.reply_text("❌ Клан не найден!")
                    return WAITING_FOR_WAR_CLAN_ID
                if enemy_clan_id == clan[0]:
                    await update.message.reply_text("❌ Нельзя объявить войну своему клану!")
                    return WAITING_FOR_WAR_CLAN_ID
                context.user_data['enemy_clan_id'] = enemy_clan_id
                context.user_data.pop('war_clan_id')
                context.user_data['waiting_war_rating'] = True
                await update.message.reply_text("Отправьте ставку рейтинга:")
                return WAITING_FOR_WAR_RATING
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_WAR_CLAN_ID

        if 'waiting_war_rating' in context.user_data:
            try:
                rating = int(text)
                if rating < 1:
                    await update.message.reply_text("❌ Ставка должна быть больше 0!")
                    return WAITING_FOR_WAR_RATING
                clan = db.get_user_clan(user.id)
                enemy_clan_id = context.user_data.get('enemy_clan_id')
                enemy_clan = db.get_clan_by_id(enemy_clan_id)
                if clan[3] < rating:
                    await update.message.reply_text(f"❌ У вашего клана недостаточно рейтинга! (У вас: {clan[3]})")
                    return WAITING_FOR_WAR_RATING
                if enemy_clan[3] < rating:
                    await update.message.reply_text(f"❌ У клана противника недостаточно рейтинга! (У них: {enemy_clan[3]})")
                    return WAITING_FOR_WAR_RATING
                result = db.declare_war(clan[0], enemy_clan_id, rating)
                if not result:
                    await update.message.reply_text("❌ Ошибка!")
                    return ConversationHandler.END
                winner_name = result['clan1_name'] if result['winner_id'] == clan[0] else result['clan2_name']
                loser_name = result['clan2_name'] if result['winner_id'] == clan[0] else result['clan1_name']
                text = f"""⚔ ВОЙНА ЗАВЕРШЕНА!
━━━━━━━━━━━━━━━━

🛡 {result['clan1_name']}: {result['clan1_chance']}%
🛡 {result['clan2_name']}: {result['clan2_chance']}%

━━━━━━━━━━━━━━━━

🏆 ПОБЕДИТЕЛЬ: {winner_name}!
💰 Выигрыш: +{rating} рейтинга

❌ ПРОИГРАВШИЙ: {loser_name}
💸 Потеря: -{rating} рейтинга"""
                await update.message.reply_text(text)
                try:
                    await context.bot.send_message(enemy_clan[2], f"⚔ Война с кланом «{clan[1]}» завершена!\n🏆 Победитель: {winner_name}\n💰 Ставка: {rating} рейтинга")
                except:
                    pass
                context.user_data.clear()
                return ConversationHandler.END
            except:
                await update.message.reply_text("❌ Неверная ставка!")
                return WAITING_FOR_WAR_RATING

        if 'clan_msg_to' in context.user_data:
            try:
                to_clan_id = int(text)
                context.user_data['clan_msg_to'] = to_clan_id
                context.user_data['waiting_clan_msg_text'] = True
                await update.message.reply_text("Отправьте текст сообщения:")
                return WAITING_FOR_CLAN_MSG_TEXT
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_CLAN_MSG_CLAN

        if 'waiting_clan_msg_text' in context.user_data:
            clan = db.get_user_clan(user.id)
            to_clan_id = context.user_data.get('clan_msg_to')
            db.add_clan_message(clan[0], to_clan_id, user.id, text)
            await update.message.reply_text("✅ Сообщение отправлено!")
            context.user_data.clear()
            return ConversationHandler.END

        if 'waiting_invite' in context.user_data:
            try:
                invite_user_id = int(text)
                clan = db.get_user_clan(user.id)
                db.join_clan(invite_user_id, clan[0])
                await update.message.reply_text(f"✅ Пользователь {invite_user_id} приглашен!")
                context.user_data.clear()
                return ConversationHandler.END
            except:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_INVITE_USER


def main():
    print("🤖 Запуск Fluxy бота...")
    application = Application.builder().token(BOT_TOKEN).build()

    # Автоматическое резервное копирование каждые 30 минут
    async def auto_backup(context):
        backup_manager.backup(db)
    
    application.job_queue.run_repeating(auto_backup, interval=1800, first=10)

    # Регистрация всех команд
    application.add_handler(CommandHandler("start", Handlers.start))
    application.add_handler(CommandHandler("help", Handlers.help_command))
    application.add_handler(CommandHandler("profile", Handlers.profile))
    application.add_handler(CommandHandler("ping", Handlers.ping))
    application.add_handler(CommandHandler("id", Handlers.get_id))
    application.add_handler(CommandHandler("clan", Handlers.clan_menu_command))
    application.add_handler(CommandHandler("clan_top", Handlers.clan_top_command))
    application.add_handler(CommandHandler("clan_bonus", Handlers.clan_bonus))
    application.add_handler(CommandHandler("stats", Handlers.stats))
    application.add_handler(CommandHandler("create_clan", Handlers.create_clan))
    application.add_handler(CommandHandler("join_clan", Handlers.join_clan))
    application.add_handler(CommandHandler("leave_clan", Handlers.leave_clan))
    application.add_handler(CommandHandler("report", Handlers.report))
    application.add_handler(CommandHandler("ban", Handlers.ban))
    application.add_handler(CommandHandler("unban", Handlers.unban))
    application.add_handler(CommandHandler("mute", Handlers.mute))
    application.add_handler(CommandHandler("unmute", Handlers.unmute))
    application.add_handler(CommandHandler("warn", Handlers.warn))
    application.add_handler(CommandHandler("unwarn", Handlers.unwarn))
    application.add_handler(CommandHandler("setadm", Handlers.setadm))
    application.add_handler(CommandHandler("permban", Handlers.permban))
    application.add_handler(CommandHandler("unperm", Handlers.unperm))
    application.add_handler(CommandHandler("broadcast", Handlers.broadcast))
    application.add_handler(CommandHandler("reports", Handlers.reports))
    application.add_handler(CommandHandler("answer_report", Handlers.answer_report))
    application.add_handler(CommandHandler("reject_report", Handlers.reject_report))
    application.add_handler(CommandHandler("answer_question", Handlers.answer_question))
    application.add_handler(CommandHandler("reject_question", Handlers.reject_question))
    application.add_handler(CommandHandler("astats", Handlers.astats))
    application.add_handler(CommandHandler("hstats", Handlers.hstats))
    application.add_handler(CommandHandler("give_rep", Handlers.give_rep))
    application.add_handler(CommandHandler("rename_rank", Handlers.rename_rank))
    application.add_handler(CommandHandler("accept_request", Handlers.accept_request))
    application.add_handler(CommandHandler("reject_request", Handlers.reject_request))
    application.add_handler(CommandHandler("ask", Handlers.ask))

    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, Handlers.on_bot_added), group=2)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, Handlers.welcome_new_member), group=3)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.antispam_check), group=1)

    # ConversationHandler для диалогов
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(Handlers.button_handler, pattern="^add_admin$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^remove_admin$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^change_admin_level$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^add_agent$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^remove_agent$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^change_agent_level$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^blacklist_add$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^blacklist_remove$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^broadcast_pm$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^broadcast_chats$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^declare_war$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^message_clan$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^invite_member$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^edit_welcome_text$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^find_clan_btn$")
        ],
        states={
            WAITING_FOR_ADMIN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_ADMIN_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_AGENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_AGENT_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_WAR_CLAN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_WAR_RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_CLAN_MSG_CLAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_CLAN_MSG_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_BLACKLIST_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_BLACKLIST_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_INVITE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_WELCOME_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_CLAN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(conv_handler)

    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(Handlers.button_handler))

    print("✅ Бот запущен!")
    print(f"👑 Основатель: {SUPER_ADMIN_ID}")
    print("📦 Резервное копирование в JSONBin активировано")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()