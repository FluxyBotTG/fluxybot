import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8980577910:AAGJFO588dLcq86neXNAcPUwIW9_xG7UHc8"
FOUNDER_ID = 8669060906
ONLY_OWNER_MODE = False

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_RANK_USER = 0
BOT_RANK_1 = 1
BOT_RANK_2 = 2
BOT_RANK_3 = 3
BOT_RANK_4 = 4
BOT_RANK_5 = 5
BOT_RANK_6 = 6
BOT_RANK_7 = 7
BOT_RANK_8 = 8
BOT_RANK_9 = 9
BOT_RANK_FOUNDER = 10

AGENT_LEVEL_1 = 1
AGENT_LEVEL_2 = 2
AGENT_LEVEL_3 = 3

CHAT_RANK_USER = 0
CHAT_RANK_1 = 1
CHAT_RANK_2 = 2
CHAT_RANK_3 = 3
CHAT_RANK_4 = 4
CHAT_RANK_OWNER = 5

# ==================== АНТИСПАМ СИСТЕМА ====================
# Храним сообщения: {(chat_id, user_id): [timestamps]}
message_history = {}

class Database:
    def __init__(self, db_path: str = "fluxy_bot.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                bot_rank INTEGER DEFAULT 0,
                agent_level INTEGER DEFAULT 0,
                clan_id INTEGER,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bot_rank_names (
                rank_level INTEGER PRIMARY KEY,
                rank_name TEXT
            );
            CREATE TABLE IF NOT EXISTS bot_rank_permissions (
                rank_level INTEGER,
                permission TEXT,
                PRIMARY KEY (rank_level, permission)
            );
            CREATE TABLE IF NOT EXISTS agent_level_names (
                level INTEGER PRIMARY KEY,
                level_name TEXT
            );
            CREATE TABLE IF NOT EXISTS agent_level_permissions (
                level INTEGER,
                permission TEXT,
                PRIMARY KEY (level, permission)
            );
            CREATE TABLE IF NOT EXISTS chat_rank_names (
                chat_id INTEGER,
                rank_level INTEGER,
                rank_name TEXT,
                PRIMARY KEY (chat_id, rank_level)
            );
            CREATE TABLE IF NOT EXISTS chat_rank_permissions (
                chat_id INTEGER,
                rank_level INTEGER,
                permission TEXT,
                PRIMARY KEY (chat_id, rank_level, permission)
            );
            CREATE TABLE IF NOT EXISTS chat_members (
                chat_id INTEGER,
                user_id INTEGER,
                chat_rank INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                warned_by INTEGER,
                reason TEXT,
                warn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                banned_by INTEGER,
                reason TEXT,
                ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS mutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                muted_by INTEGER,
                reason TEXT,
                mute_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unmute_date TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS awards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                awarded_by INTEGER,
                award_text TEXT,
                award_date TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bot_admins (
                user_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS super_admins (
                user_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS black_list (
                user_id INTEGER PRIMARY KEY,
                reason TEXT
            );
            CREATE TABLE IF NOT EXISTS clans (
                clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                leader_id INTEGER,
                rating INTEGER DEFAULT 0,
                join_enabled INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS clan_members (
                user_id INTEGER PRIMARY KEY,
                clan_id INTEGER,
                role TEXT DEFAULT 'member'
            );
            CREATE TABLE IF NOT EXISTS clan_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clan_id INTEGER,
                sender_id INTEGER,
                message TEXT,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                reporter_username TEXT,
                target_id INTEGER,
                target_username TEXT,
                reason TEXT,
                chat_id INTEGER,
                chat_title TEXT,
                message_link TEXT,
                report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_username TEXT,
                question TEXT,
                status TEXT DEFAULT 'open',
                agent_id INTEGER,
                agent_username TEXT,
                answer TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_date TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                chat_type TEXT,
                chat_title TEXT
            );
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                antispam_enabled INTEGER DEFAULT 0,
                antispam_limit INTEGER DEFAULT 5,
                welcome_enabled INTEGER DEFAULT 0,
                welcome_text TEXT DEFAULT 'Привет, {name}! Добро пожаловать в {chat}! 🎉'
            );
        ''')
        self.init_default_data()
        self.conn.commit()

    def init_default_data(self):
        for lvl, name in {0:"Пользователь",1:"Ранг 1",2:"Ранг 2",3:"Ранг 3",4:"Ранг 4",5:"Ранг 5",6:"Ранг 6",7:"Ранг 7",8:"Админ бота",9:"Высший админ",10:"Основатель бота"}.items():
            self.cursor.execute("INSERT OR IGNORE INTO bot_rank_names VALUES (?, ?)", (lvl, name))
        for lvl, name in {0:"Не агент",1:"Агент поддержки",2:"Главный агент поддержки",3:"ГС агентов поддержки"}.items():
            self.cursor.execute("INSERT OR IGNORE INTO agent_level_names VALUES (?, ?)", (lvl, name))
        for rank, perms in {8:["btn_admin_panel","btn_admins_list","btn_agents_list","btn_blacklist","btn_give_rep","btn_commands","btn_chats"],
                            9:["btn_admin_panel","btn_admins_list","btn_agents_list","btn_blacklist","btn_give_rep","btn_commands","btn_chats","btn_ranks","btn_rank_names","btn_rank_perms","btn_super_admins","btn_agent_levels","btn_agent_names","btn_agent_perms"]}.items():
            for p in perms:
                self.cursor.execute("INSERT OR IGNORE INTO bot_rank_permissions VALUES (?, ?)", (rank, p))
        for level, perms in {1:["btn_answer_tickets"],2:["btn_answer_tickets","btn_close_tickets"],3:["btn_answer_tickets","btn_close_tickets","btn_manage_agents","btn_view_reports"]}.items():
            for p in perms:
                self.cursor.execute("INSERT OR IGNORE INTO agent_level_permissions VALUES (?, ?)", (level, p))
        self.cursor.execute("SELECT chat_id FROM chats")
        for (chat_id,) in self.cursor.fetchall():
            for level, name in {0:"Пользователь",1:"Ранг 1",2:"Ранг 2",3:"Ранг 3",4:"Ранг 4",5:"Владелец"}.items():
                self.cursor.execute("INSERT OR IGNORE INTO chat_rank_names VALUES (?, ?, ?)", (chat_id, level, name))
            for rank, perms in {1:["btn_chat_admin"],2:["btn_chat_admin","btn_kick"],3:["btn_chat_admin","btn_kick","btn_warn","btn_mute"],4:["btn_chat_admin","btn_kick","btn_warn","btn_mute","btn_ban"]}.items():
                for p in perms:
                    self.cursor.execute("INSERT OR IGNORE INTO chat_rank_permissions VALUES (?, ?, ?)", (chat_id, rank, p))
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def get_user_by_username(self, username):
        username = username.replace('@', '')
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def add_user(self, user_id, username, first_name):
        if not self.get_user(user_id):
            self.cursor.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, username, first_name))
            self.conn.commit()

    def update_user_activity(self, user_id):
        self.cursor.execute("UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_bot_rank(self, user_id):
        if user_id == FOUNDER_ID:
            return BOT_RANK_FOUNDER
        user = self.get_user(user_id)
        return user['bot_rank'] if user else 0

    def set_bot_rank(self, user_id, rank):
        self.cursor.execute("UPDATE users SET bot_rank = ? WHERE user_id = ?", (rank, user_id))
        self.conn.commit()

    def get_bot_rank_name(self, user_id):
        rank = self.get_bot_rank(user_id)
        self.cursor.execute("SELECT rank_name FROM bot_rank_names WHERE rank_level = ?", (rank,))
        result = self.cursor.fetchone()
        return result[0] if result else f"Ранг {rank}"

    def has_bot_rank_permission(self, rank_level, permission):
        if rank_level == BOT_RANK_FOUNDER:
            return True
        self.cursor.execute("SELECT 1 FROM bot_rank_permissions WHERE rank_level = ? AND permission = ?", (rank_level, permission))
        return self.cursor.fetchone() is not None

    def get_agent_level(self, user_id):
        user = self.get_user(user_id)
        return user['agent_level'] if user else 0

    def set_agent_level(self, user_id, level):
        self.cursor.execute("UPDATE users SET agent_level = ? WHERE user_id = ?", (level, user_id))
        self.conn.commit()

    def get_agent_level_name(self, user_id):
        level = self.get_agent_level(user_id)
        self.cursor.execute("SELECT level_name FROM agent_level_names WHERE level = ?", (level,))
        result = self.cursor.fetchone()
        return result[0] if result else "Не агент"

    def get_all_agents(self):
        self.cursor.execute("SELECT u.user_id, u.username, u.first_name, u.agent_level FROM users u WHERE u.agent_level > 0")
        return [{'user_id': r[0], 'username': r[1] or 'Нет', 'first_name': r[2] or 'Нет', 'agent_level': r[3]} for r in self.cursor.fetchall()]

    def get_all_bot_admins(self):
        admins = []
        self.cursor.execute("SELECT user_id, username, first_name FROM users WHERE user_id = ?", (FOUNDER_ID,))
        founder = self.cursor.fetchone()
        if founder:
            admins.append({'user_id': founder[0], 'username': founder[1] or 'Основатель', 'first_name': founder[2] or 'Основатель'})
        else:
            admins.append({'user_id': FOUNDER_ID, 'username': 'Основатель', 'first_name': 'Основатель'})
        self.cursor.execute("SELECT u.user_id, u.username, u.first_name FROM users u WHERE u.bot_rank >= 8 AND u.user_id != ?", (FOUNDER_ID,))
        for row in self.cursor.fetchall():
            admins.append({'user_id': row[0], 'username': row[1] or 'Нет', 'first_name': row[2] or 'Нет'})
        return admins

    def is_super_admin(self, user_id):
        if user_id == FOUNDER_ID:
            return True
        self.cursor.execute("SELECT 1 FROM super_admins WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None

    def add_super_admin(self, user_id):
        self.cursor.execute("INSERT OR IGNORE INTO super_admins VALUES (?)", (user_id,))
        self.set_bot_rank(user_id, 9)
        self.conn.commit()

    def remove_super_admin(self, user_id):
        self.cursor.execute("DELETE FROM super_admins WHERE user_id = ?", (user_id,))
        self.set_bot_rank(user_id, 0)
        self.conn.commit()

    def add_chat_member(self, chat_id, user_id, chat_rank=0):
        self.cursor.execute("INSERT OR IGNORE INTO chat_members VALUES (?, ?, ?)", (chat_id, user_id, chat_rank))
        self.conn.commit()

    def get_chat_member_rank(self, chat_id, user_id):
        self.cursor.execute("SELECT chat_rank FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def set_chat_member_rank(self, chat_id, user_id, rank):
        self.cursor.execute("INSERT OR REPLACE INTO chat_members VALUES (?, ?, ?)", (chat_id, user_id, rank))
        self.conn.commit()

    def get_chat_members_by_rank(self, chat_id, rank):
        self.cursor.execute('''
            SELECT cm.user_id, cm.chat_rank, u.username, u.first_name
            FROM chat_members cm LEFT JOIN users u ON cm.user_id = u.user_id
            WHERE cm.chat_id = ? AND cm.chat_rank = ?
        ''', (chat_id, rank))
        return [{'user_id': r[0], 'chat_rank': r[1], 'username': r[2] or 'Нет', 'first_name': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    def get_all_chat_admins(self, chat_id):
        self.cursor.execute('''
            SELECT cm.user_id, cm.chat_rank, u.username, u.first_name
            FROM chat_members cm LEFT JOIN users u ON cm.user_id = u.user_id
            WHERE cm.chat_id = ? AND cm.chat_rank >= 1 ORDER BY cm.chat_rank DESC
        ''', (chat_id,))
        return [{'user_id': r[0], 'chat_rank': r[1], 'username': r[2] or 'Нет', 'first_name': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    def has_chat_permission(self, chat_id, rank_level, permission):
        if rank_level == CHAT_RANK_OWNER:
            return True
        self.cursor.execute("SELECT 1 FROM chat_rank_permissions WHERE chat_id = ? AND rank_level = ? AND permission = ?", (chat_id, rank_level, permission))
        return self.cursor.fetchone() is not None

    def get_rank_name(self, chat_id, rank_level):
        self.cursor.execute("SELECT rank_name FROM chat_rank_names WHERE chat_id = ? AND rank_level = ?", (chat_id, rank_level))
        result = self.cursor.fetchone()
        return result[0] if result else f"Ранг {rank_level}"

    def set_rank_name(self, chat_id, rank_level, name):
        self.cursor.execute("INSERT OR REPLACE INTO chat_rank_names VALUES (?, ?, ?)", (chat_id, rank_level, name))
        self.conn.commit()

    def get_all_rank_names(self, chat_id):
        self.cursor.execute("SELECT rank_level, rank_name FROM chat_rank_names WHERE chat_id = ? ORDER BY rank_level", (chat_id,))
        return {row[0]: row[1] for row in self.cursor.fetchall()}

    def add_chat(self, chat_id, chat_type, chat_title):
        self.cursor.execute("INSERT OR REPLACE INTO chats VALUES (?, ?, ?)", (chat_id, chat_type, chat_title))
        self.conn.commit()
        self.init_default_data()

    def add_warning(self, chat_id, user_id, warned_by, reason):
        self.cursor.execute("INSERT INTO warnings (chat_id, user_id, warned_by, reason) VALUES (?, ?, ?, ?)", (chat_id, user_id, warned_by, reason))
        self.conn.commit()

    def remove_warning(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        self.conn.commit()

    def add_ban(self, chat_id, user_id, banned_by, reason):
        self.cursor.execute("INSERT INTO bans (chat_id, user_id, banned_by, reason) VALUES (?, ?, ?, ?)", (chat_id, user_id, banned_by, reason))
        self.conn.commit()

    def remove_ban(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM bans WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        self.conn.commit()

    def add_mute(self, chat_id, user_id, muted_by, reason, unmute_date):
        self.cursor.execute("INSERT INTO mutes (chat_id, user_id, muted_by, reason, unmute_date) VALUES (?, ?, ?, ?, ?)", (chat_id, user_id, muted_by, reason, unmute_date))
        self.conn.commit()

    def remove_mute(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        self.conn.commit()

    def add_award(self, user_id, awarded_by, award_text):
        award_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        self.cursor.execute("INSERT INTO awards (user_id, awarded_by, award_text, award_date) VALUES (?, ?, ?, ?)", (user_id, awarded_by, award_text, award_time))
        self.conn.commit()

    def get_user_awards(self, user_id):
        self.cursor.execute('''
            SELECT a.award_text, a.award_date, u.username FROM awards a
            LEFT JOIN users u ON a.awarded_by = u.user_id
            WHERE a.user_id = ? ORDER BY a.award_date DESC
        ''', (user_id,))
        return [{'award_text': r[0], 'award_date': r[1], 'awarded_by_username': r[2] or 'Нет'} for r in self.cursor.fetchall()]

    def is_blacklisted(self, user_id):
        self.cursor.execute("SELECT 1 FROM black_list WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None

    def add_to_blacklist(self, user_id, reason):
        self.cursor.execute("INSERT OR REPLACE INTO black_list VALUES (?, ?)", (user_id, reason))
        self.conn.commit()

    def remove_from_blacklist(self, user_id):
        self.cursor.execute("DELETE FROM black_list WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def get_blacklist(self):
        self.cursor.execute("SELECT bl.user_id, bl.reason, u.username, u.first_name FROM black_list bl LEFT JOIN users u ON bl.user_id = u.user_id")
        return [{'user_id': r[0], 'reason': r[1], 'username': r[2] or 'Нет', 'first_name': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    def add_ticket(self, user_id, user_username, question):
        self.cursor.execute("INSERT INTO support_tickets (user_id, user_username, question) VALUES (?, ?, ?)", (user_id, user_username, question))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_ticket(self, ticket_id):
        self.cursor.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def assign_ticket(self, ticket_id, agent_id, agent_username):
        self.cursor.execute("UPDATE support_tickets SET status='in_progress', agent_id=?, agent_username=? WHERE id=?", (agent_id, agent_username, ticket_id))
        self.conn.commit()

    def close_ticket(self, ticket_id, answer):
        self.cursor.execute("UPDATE support_tickets SET status='closed', answer=?, closed_date=CURRENT_TIMESTAMP WHERE id=?", (answer, ticket_id))
        self.conn.commit()

    def add_report(self, reporter_id, reporter_username, target_id, target_username, reason, chat_id, chat_title, message_link):
        self.cursor.execute('''
            INSERT INTO reports (reporter_id, reporter_username, target_id, target_username, reason, chat_id, chat_title, message_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (reporter_id, reporter_username, target_id, target_username, reason, chat_id, chat_title, message_link))
        self.conn.commit()
        return self.cursor.lastrowid

    def set_report_answered_by(self, report_id, admin_id):
        self.cursor.execute("UPDATE reports SET answered_by = ? WHERE id = ?", (admin_id, report_id))
        self.conn.commit()

    def get_admin_reply_count(self, admin_id):
        self.cursor.execute("SELECT COUNT(*) FROM reports WHERE answered_by = ?", (admin_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def get_agent_reply_count(self, agent_id):
        self.cursor.execute("SELECT COUNT(*) FROM support_tickets WHERE agent_id = ? AND status = 'closed' AND answer IS NOT NULL AND answer != ''", (agent_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def create_clan(self, name, leader_id):
        self.cursor.execute("INSERT INTO clans (name, leader_id) VALUES (?, ?)", (name, leader_id))
        clan_id = self.cursor.lastrowid
        self.cursor.execute("INSERT INTO clan_members VALUES (?, ?, 'leader')", (leader_id, clan_id))
        self.cursor.execute("UPDATE users SET clan_id = ? WHERE user_id = ?", (clan_id, leader_id))
        self.conn.commit()
        return clan_id

    def get_clan(self, clan_id):
        self.cursor.execute("SELECT * FROM clans WHERE clan_id = ?", (clan_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def get_user_clan(self, user_id):
        user = self.get_user(user_id)
        if user and user['clan_id']:
            return self.get_clan(user['clan_id'])
        return None

    def get_clan_member(self, user_id):
        self.cursor.execute("SELECT * FROM clan_members WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def get_clan_members(self, clan_id):
        self.cursor.execute('''
            SELECT cm.user_id, cm.role, u.username, u.first_name FROM clan_members cm
            LEFT JOIN users u ON cm.user_id = u.user_id WHERE cm.clan_id = ?
        ''', (clan_id,))
        return [{'user_id': r[0], 'role': r[1], 'username': r[2] or 'Нет', 'first_name': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    def set_clan_join_enabled(self, clan_id, enabled):
        self.cursor.execute("UPDATE clans SET join_enabled = ? WHERE clan_id = ?", (1 if enabled else 0, clan_id))
        self.conn.commit()

    def get_top_clans(self, limit=10):
        self.cursor.execute("SELECT clan_id, name, rating FROM clans ORDER BY rating DESC LIMIT ?", (limit,))
        return [{'clan_id': r[0], 'name': r[1], 'rating': r[2]} for r in self.cursor.fetchall()]

    def add_clan_rating(self, clan_id, rating):
        self.cursor.execute("UPDATE clans SET rating = rating + ? WHERE clan_id = ?", (rating, clan_id))
        self.conn.commit()

    def add_clan_message(self, clan_id, sender_id, message):
        self.cursor.execute("INSERT INTO clan_messages (clan_id, sender_id, message) VALUES (?, ?, ?)", (clan_id, sender_id, message))
        self.conn.commit()

    def get_clan_messages(self, clan_id, limit=10):
        self.cursor.execute('''
            SELECT cm.sender_id, cm.message, cm.sent_date, u.username FROM clan_messages cm
            LEFT JOIN users u ON cm.sender_id = u.user_id WHERE cm.clan_id = ? ORDER BY cm.sent_date DESC LIMIT ?
        ''', (clan_id, limit))
        return [{'sender_id': r[0], 'message': r[1], 'sent_date': r[2], 'username': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    # ==================== НАСТРОЙКИ ЧАТА ====================
    def get_chat_settings(self, chat_id: int):
        self.cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def save_chat_settings(self, chat_id: int, **kwargs):
        # Проверяем, есть ли запись
        self.cursor.execute("SELECT chat_id FROM chat_settings WHERE chat_id = ?", (chat_id,))
        exists = self.cursor.fetchone()
        
        if not exists:
            self.cursor.execute("INSERT INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
        
        # Обновляем переданные поля
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE chat_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id))
        
        self.conn.commit()

db = Database()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def has_astats_permission(user_id: int) -> bool:
    return has_bot_permission(user_id, "btn_astats")

def has_hstats_permission(user_id: int) -> bool:
    return db.has_agent_level_permission(db.get_agent_level(user_id), "btn_hstats")

def is_blacklisted_check(user_id: int) -> bool:
    return db.is_blacklisted(user_id)

def has_bot_permission(user_id: int, permission: str) -> bool:
    return db.has_bot_rank_permission(db.get_bot_rank(user_id), permission)

def is_super_admin(user_id: int) -> bool:
    return db.is_super_admin(user_id)

def is_chat_owner(chat_id: int, user_id: int) -> bool:
    return db.get_chat_member_rank(chat_id, user_id) == CHAT_RANK_OWNER

def has_chat_permission(chat_id: int, user_id: int, permission: str) -> bool:
    return db.has_chat_permission(chat_id, db.get_chat_member_rank(chat_id, user_id), permission)

def is_staff(user_id: int) -> bool:
    return has_bot_permission(user_id, "btn_admin_panel") or db.get_agent_level(user_id) > 0

def format_clan_info(clan: Dict) -> str:
    if not clan:
        return "Вы не состоите в клане"
    return f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 Клан айди: {clan['clan_id']}
🛡 Название клана: {clan['name']}
🏆 Рейтинг клана: {clan['rating']}

━━━━━━━━━━━━━━━━
Выберите кнопку ниже ⬇️"""

async def get_target_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    if context.args and context.args[0].isdigit():
        return int(context.args[0])
    if context.args and context.args[0].startswith('@'):
        username = context.args[0].replace('@', '')
        user = db.get_user_by_username(username)
        if user:
            return user['user_id']
        chat = update.effective_chat
        if chat and chat.type != "private":
            try:
                member = await context.bot.get_chat_member(chat.id, username)
                if member:
                    return member.user.id
            except Exception:
                pass
        return None
    return None

# ==================== ФУНКЦИЯ ПРОВЕРКИ АНТИСПАМА ====================
async def check_antispam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет антиспам. Возвращает True если сообщение нужно заблокировать.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    settings = db.get_chat_settings(chat_id)
    if not settings or not settings.get("antispam_enabled"):
        return False
    
    now = time.time()
    limit = settings.get("antispam_limit", 5)
    
    key = (chat_id, user_id)
    timestamps = message_history.get(key, [])
    
    # Оставляем только сообщения за последнюю секунду
    timestamps = [t for t in timestamps if now - t < 1]
    
    if len(timestamps) >= limit:
        # Превышен лимит - кикаем
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            await update.effective_message.reply_text(
                f"🚫 <b>{update.effective_user.full_name}</b> исключён за спам!",
                parse_mode='HTML'
            )
            # Очищаем историю
            message_history[key] = []
        except Exception as e:
            logger.error(f"Ошибка при кике за спам: {e}")
        return True
    
    # Добавляем текущее сообщение в историю
    timestamps.append(now)
    message_history[key] = timestamps
    
    return False

# ==================== КОМАНДА /id ====================
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    target_id = await get_target_user_id(update, context)
    if target_id:
        await update.message.reply_text(f"🆔 ID пользователя: {target_id}")
    else:
        await update.message.reply_text("Использование: /id [ID или @username]\nИли ответьте на сообщение пользователя")

# ==================== КОМАНДА /ping ====================
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    start_time = time.time()
    msg = await update.message.reply_text("📡 Измеряю пинг...")
    end_time = time.time()
    ping = round((end_time - start_time) * 1000)
    await msg.edit_text(f"🏓 Понг!\n━━━━━━━━━━━━━━━━\n⏱️ Пинг: {ping} мс\n🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

# ==================== КОМАНДА /stats ====================
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /stats [ID или @username]\nИли ответьте на сообщение пользователя")
        return
    target_user_data = db.get_user(target_id)
    if not target_user_data:
        try:
            chat = update.effective_chat
            member = await context.bot.get_chat_member(chat.id, target_id)
            db.add_user(member.user.id, member.user.username, member.user.first_name)
            target_user_data = db.get_user(target_id)
        except:
            await update.message.reply_text("❌ Пользователь не найден")
            return
    clan = db.get_user_clan(target_id)
    clan_name = clan['name'] if clan else "Нет клана"
    clan_rating = clan['rating'] if clan else 0
    text = f"""👤 Профиль пользователя
━━━━━━━━━━━━━━━━

👤 Имя: {target_user_data['first_name'] or 'Нет'}
🔗 Username: @{target_user_data['username'] or 'Нет'}
🆔 ID: {target_user_data['user_id']}

🎖️ Ранг бота: {db.get_bot_rank_name(target_id)}
📊 Уровень агента: {db.get_agent_level_name(target_id)}

🛡️ Клан: {clan_name}
🏆 Рейтинг клана: {clan_rating}

━━━━━━━━━━━━━━━━"""
    keyboard = [
        [InlineKeyboardButton("🏅 Выдать награду", callback_data=f"give_award_{target_id}")],
        [InlineKeyboardButton("🏆 Награды", callback_data=f"show_awards_{target_id}")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== КОМАНДА /permban ====================
async def permban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_bot_permission(user.id, "btn_blacklist"):
        await update.message.reply_text("⛔ У вас нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /permban [ID или @username] [причина]\nИли ответьте на сообщение")
        return
    if is_super_admin(target_id):
        await update.message.reply_text("⛔ Нельзя забанить супер-админа или основателя")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    if update.message.reply_to_message:
        reason = ' '.join(context.args) if context.args else "Не указана"
    db.add_to_blacklist(target_id, reason)
    await update.message.reply_text(f"🚫 Пользователь {target_id} добавлен в ЧС\nПричина: {reason}")

# ==================== КОМАНДА /unperm ====================
async def unperm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_bot_permission(user.id, "btn_blacklist"):
        await update.message.reply_text("⛔ У вас нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /unperm [ID или @username]\nИли ответьте на сообщение")
        return
    db.remove_from_blacklist(target_id)
    await update.message.reply_text(f"✅ Пользователь {target_id} удален из ЧС")

# ==================== КОМАНДА /kick ====================
async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_kick"):
        await update.message.reply_text("⛔ У вас нет прав на кик")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /kick [ID или @username] [причина]\nИли ответьте на сообщение нарушителя")
        return
    if is_super_admin(target_id):
        await update.message.reply_text("⛔ Нельзя кикнуть супер-админа")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    if update.message.reply_to_message:
        reason = ' '.join(context.args) if context.args else "Не указана"
    try:
        await context.bot.ban_chat_member(chat.id, target_id)
        await context.bot.unban_chat_member(chat.id, target_id)
        await update.message.reply_text(f"✅ Пользователь {target_id} кикнут\nПричина: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ==================== КОМАНДА /warn ====================
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_warn"):
        await update.message.reply_text("⛔ У вас нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /warn [ID или @username] [причина]\nИли ответьте на сообщение нарушителя")
        return
    if is_super_admin(target_id):
        await update.message.reply_text("⛔ Нельзя предупредить супер-админа")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    if update.message.reply_to_message:
        reason = ' '.join(context.args) if context.args else "Не указана"
    db.add_warning(chat.id, target_id, user.id, reason)
    await update.message.reply_text(f"⚠️ Пользователь {target_id} получил предупреждение\nПричина: {reason}")

# ==================== КОМАНДА /ban ====================
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_ban"):
        await update.message.reply_text("⛔ У вас нет прав на бан")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /ban [ID или @username] [причина]\nИли ответьте на сообщение нарушителя")
        return
    if is_super_admin(target_id):
        await update.message.reply_text("⛔ Нельзя забанить супер-админа")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    if update.message.reply_to_message:
        reason = ' '.join(context.args) if context.args else "Не указана"
    try:
        await context.bot.ban_chat_member(chat.id, target_id)
        db.add_ban(chat.id, target_id, user.id, reason)
        await update.message.reply_text(f"🔨 Пользователь {target_id} забанен\nПричина: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ==================== КОМАНДА /mute ====================
async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_mute"):
        await update.message.reply_text("⛔ У вас нет прав на мут")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /mute [ID или @username] [время в минутах] [причина]\nИли ответьте на сообщение")
        return
    if is_super_admin(target_id):
        await update.message.reply_text("⛔ Нельзя замутить супер-админа")
        return
    if update.message.reply_to_message:
        if len(context.args) >= 1 and context.args[0].isdigit():
            minutes = int(context.args[0])
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
        else:
            minutes = 60
            reason = ' '.join(context.args) if context.args else "Не указана"
    else:
        if len(context.args) >= 2 and context.args[1].isdigit():
            minutes = int(context.args[1])
            reason = ' '.join(context.args[2:]) if len(context.args) > 2 else "Не указана"
        else:
            minutes = 60
            reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    try:
        unmute_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=ChatPermissions(can_send_messages=False, can_send_other_messages=False, can_add_web_page_previews=False),
            until_date=unmute_time
        )
        local_unmute = datetime.now() + timedelta(minutes=minutes)
        db.add_mute(chat.id, target_id, user.id, reason, local_unmute.strftime('%Y-%m-%d %H:%M:%S'))
        await update.message.reply_text(f"🔇 Пользователь {target_id} замучен на {minutes} мин\nПричина: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ==================== КОМАНДА /unmute ====================
async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_mute"):
        await update.message.reply_text("⛔ У вас нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /unmute [ID или @username]\nИли ответьте на сообщение")
        return
    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target_id,
            permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True, can_change_info=True, can_invite_users=True, can_pin_messages=True)
        )
        db.remove_mute(chat.id, target_id)
        await update.message.reply_text(f"🔊 Пользователь {target_id} размучен")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ==================== КОМАНДА /unban ====================
async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_ban"):
        await update.message.reply_text("⛔ У вас нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /unban [ID или @username]\nИли ответьте на сообщение")
        return
    try:
        await context.bot.unban_chat_member(chat.id, target_id)
        db.remove_ban(chat.id, target_id)
        await update.message.reply_text(f"✅ Пользователь {target_id} разбанен")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ==================== КОМАНДА /unwarn ====================
async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_warn"):
        await update.message.reply_text("⛔ У вас нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /unwarn [ID или @username]\nИли ответьте на сообщение")
        return
    db.remove_warning(chat.id, target_id)
    await update.message.reply_text(f"✅ Предупреждение с пользователя {target_id} снято")

# ==================== КОМАНДА /setadm ====================
async def setadm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not (is_chat_owner(chat.id, user.id) or is_super_admin(user.id)):
        await update.message.reply_text("⛔ Только владелец чата или супер-админ может выдавать ранги")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /setadm [ID или @username] [ранг 0-5]")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    try:
        rank = int(context.args[1])
        if rank < 0 or rank > 5:
            await update.message.reply_text("❌ Ранг должен быть от 0 до 5")
            return
    except ValueError:
        await update.message.reply_text("❌ Введите число ранга")
        return
    db.set_chat_member_rank(chat.id, target_id, rank)
    rank_name = db.get_rank_name(chat.id, rank)
    await update.message.reply_text(f"✅ Пользователь {target_id} получил ранг «{rank_name}»")

# ==================== КОМАНДА /admins ====================
async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    admins = db.get_all_chat_admins(chat.id)
    text = "👥 Админы чата\n━━━━━━━━━━━━━━━━\n\n"
    if not admins:
        text += "Нет админов"
    else:
        for admin in admins:
            rank_name = db.get_rank_name(chat.id, admin['chat_rank'])
            text += f"• {admin['first_name']} (@{admin['username']})\n  Ранг: {rank_name} ({admin['chat_rank']})\n  ID: {admin['user_id']}\n\n"
    await update.message.reply_text(text)

# ==================== КОМАНДА /botadmins ====================
async def botadmins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    admins = db.get_all_bot_admins()
    text = "🤖 Админы бота\n━━━━━━━━━━━━━━━━\n\n"
    if not admins:
        text += "Нет админов"
    else:
        for admin in admins:
            rank_name = db.get_bot_rank_name(admin['user_id'])
            text += f"• {admin['first_name']} (@{admin['username']})\n  Ранг: {rank_name}\n  ID: {admin['user_id']}\n\n"
    await update.message.reply_text(text)

# ==================== КОМАНДА /astats ====================
async def astats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_astats_permission(user.id):
        await update.message.reply_text("⛔ У вас нет прав на использование /astats")
        return
    if is_super_admin(user.id):
        admins = db.get_all_bot_admins()
        text = "📊 Статистика ответов на жалобы (все админы)\n━━━━━━━━━━━━━━━━\n\n"
        for admin in admins:
            count = db.get_admin_reply_count(admin['user_id'])
            text += f"• {admin['first_name']} (@{admin['username']}): {count} ответов\n"
        if not admins:
            text += "Нет админов"
    else:
        count = db.get_admin_reply_count(user.id)
        text = f"📊 Ваша статистика ответов на жалобы\n━━━━━━━━━━━━━━━━\n\n✅ Отвечено жалоб: {count}"
    await update.message.reply_text(text)

# ==================== КОМАНДА /hstats ====================
async def hstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_hstats_permission(user.id):
        await update.message.reply_text("⛔ У вас нет прав на использование /hstats")
        return
    if is_super_admin(user.id):
        agents = db.get_all_agents()
        text = "📊 Статистика ответов на вопросы (все агенты)\n━━━━━━━━━━━━━━━━\n\n"
        for agent in agents:
            count = db.get_agent_reply_count(agent['user_id'])
            text += f"• {agent['first_name']} (@{agent['username']}): {count} ответов\n"
        if not agents:
            text += "Нет агентов"
    else:
        count = db.get_agent_reply_count(user.id)
        text = f"📊 Ваша статистика ответов на вопросы\n━━━━━━━━━━━━━━━━\n\n✅ Отвечено вопросов: {count}"
    await update.message.reply_text(text)

# ==================== КОМАНДА /onlyowner ====================
async def onlyowner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ONLY_OWNER_MODE
    user = update.effective_user
    if user.id != FOUNDER_ID:
        await update.message.reply_text("⛔ Только основатель бота может использовать эту команду")
        return
    ONLY_OWNER_MODE = not ONLY_OWNER_MODE
    if ONLY_OWNER_MODE:
        await update.message.reply_text("🔒 Глобальный режим «только основатель» включён. Бот отвечает только вам.")
    else:
        await update.message.reply_text("🔓 Глобальный режим «только основатель» выключен. Бот снова отвечает всем.")

# ==================== КОМАНДА /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    chat = update.effective_chat
    db.add_user(user.id, user.username, user.first_name)
    if chat:
        db.add_chat(chat.id, chat.type, chat.title or "Личный чат")
        db.add_chat_member(chat.id, user.id)
    if chat and chat.type != "private":
        owners = db.get_chat_members_by_rank(chat.id, CHAT_RANK_OWNER)
        if not owners:
            db.set_chat_member_rank(chat.id, user.id, CHAT_RANK_OWNER)
    if user.id == FOUNDER_ID:
        db.add_super_admin(user.id)
    text = f"""👋 Добро пожаловать в Fluxy | Чат-менеджер.
━━━━━━━━━━━━━━━━

🆔 Ваш ID: {user.id}
🎖️ Ваш ранг: {db.get_bot_rank_name(user.id)}
📊 Уровень агента: {db.get_agent_level_name(user.id)}

━━━━━━━━━━━━━━━━
Для продолжения нажмите на кнопку ниже ⬇️"""
    keyboard = []
    if has_bot_permission(user.id, "btn_admin_panel"):
        keyboard.append([InlineKeyboardButton("⭐️ Админ панель бота", callback_data="admin_panel")])
    if chat and chat.type != "private":
        if has_chat_permission(chat.id, user.id, "btn_chat_admin"):
            keyboard.append([InlineKeyboardButton("👑 Админ панель чата", callback_data="chat_admin_panel")])
    keyboard.append([InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")])
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="help"), InlineKeyboardButton("📋 Команды", callback_data="commands")])
    keyboard.append([InlineKeyboardButton("🔰 Агенты поддержки", callback_data="agents_list")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== КОМАНДА /help ====================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    text = """❓ Помощь
━━━━━━━━━━━━━━━━

Основные команды:
/start - Запуск бота
/help - Помощь
/ping - Пинг бота
/id - Узнать ID
/stats - Профиль пользователя
/profile - Свой профиль
/clan - Меню клана
/clan_top - Топ кланов
/report - Жалоба
"""
    # Модерация видна только при наличии прав
    if update.effective_chat and update.effective_chat.type != "private":
        chat = update.effective_chat
        if has_chat_permission(chat.id, user.id, "btn_kick"):
            text += "\n/kick [ID/@username] [причина]\n/unban [ID/@username]\n"
        if has_chat_permission(chat.id, user.id, "btn_warn"):
            text += "/warn [ID/@username] [причина]\n/unwarn [ID/@username]\n"
        if has_chat_permission(chat.id, user.id, "btn_ban"):
            text += "/ban [ID/@username] [причина]\n"
        if has_chat_permission(chat.id, user.id, "btn_mute"):
            text += "/mute [ID/@username] [время] [причина]\n/unmute [ID/@username]\n"
        if is_chat_owner(chat.id, user.id) or has_chat_permission(chat.id, user.id, "btn_chat_admin"):
            text += "\n/setadm [ID/@username] [0-5] - Выдать ранг в чате\n/admins - Список админов чата\n"
    # Админ-команды
    if has_bot_permission(user.id, "btn_blacklist"):
        text += "\nЧС:\n/permban [ID] [причина]\n/unperm [ID]\n"
    if has_astats_permission(user.id):
        text += "\n/astats - Статистика жалоб\n"
    if has_hstats_permission(user.id):
        text += "\n/hstats - Статистика вопросов\n"
    if user.id == FOUNDER_ID:
        text += "\n/onlyowner - Режим «только основатель»\n/botadmins - Админы бота\n"
    text += "\nВыберите тип обращения:"
    keyboard = [
        [InlineKeyboardButton("❗️ Жалоба", callback_data="help_report")],
        [InlineKeyboardButton("❓ Вопрос", callback_data="help_question")],
        [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== КОМАНДА /report ====================
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if is_staff(user.id):
        await update.message.reply_text("⛔ Админы и агенты не могут отправлять жалобы")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответьте на сообщение нарушителя командой /report <причина>")
        return
    reporter = update.effective_user
    target = update.message.reply_to_message.from_user
    reason = ' '.join(context.args) if context.args else "Не указана"
    chat = update.effective_chat
    message_link = f"https://t.me/c/{str(chat.id)[4:]}/{update.message.reply_to_message.message_id}" if str(chat.id).startswith('-100') else "Нет ссылки"
    report_id = db.add_report(reporter.id, reporter.username or f"id{reporter.id}", target.id, target.username or f"id{target.id}", reason, chat.id, chat.title or "Личный чат", message_link)
    admins = db.get_all_bot_admins()
    for admin in admins:
        try:
            text = f"""❗️ Новая жалоба
━━━━━━━━━━━━━━━━

👤 Кто: {reporter.username or 'Нет'} (ID: {reporter.id})
👤 На кого: {target.username or 'Нет'} (ID: {target.id})
📝 Причина: {reason}
💬 Чат: {chat.title or 'Личный чат'}
🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
🔗 Ссылка: {message_link}"""
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_report_{report_id}_{reporter.id}")]])
            await context.bot.send_message(admin['user_id'], text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка отправки жалобы админу {admin['user_id']}: {e}")
    await update.message.reply_text("✅ Жалоба отправлена администрации")

# ==================== КОМАНДА /clan_top ====================
async def clan_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    top_clans = db.get_top_clans()
    if not top_clans:
        await update.message.reply_text("Пока нет кланов")
        return
    text = "🏆 Топ кланов\n━━━━━━━━━━━━━━━━\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, clan in enumerate(top_clans[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {clan['name']} — {clan['rating']}\n"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]]))

# ==================== КОМАНДА /profile ====================
async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    clan = db.get_user_clan(user.id)
    text = f"""👤 Ваш профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(user.id)}
📊 Агент: {db.get_agent_level_name(user.id)}

🛡️ Клан: {clan['name'] if clan else 'Нет'}
🏆 Рейтинг: {clan['rating'] if clan else 0}

━━━━━━━━━━━━━━━━"""
    keyboard = [[InlineKeyboardButton("🏆 Награды", callback_data=f"show_awards_{user.id}")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== КОМАНДА /clan ====================
async def clan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    clan = db.get_user_clan(user.id)
    if not clan:
        keyboard = [
            [InlineKeyboardButton("➕ Создать клан", callback_data="create_clan")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
        ]
        await update.message.reply_text("Вы не состоите в клане", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [
            [InlineKeyboardButton("👥 Участники", callback_data="clan_members")],
            [InlineKeyboardButton("🔒 Вход в клан", callback_data="clan_join_settings")],
            [InlineKeyboardButton("✉️ Сообщения", callback_data="clan_messages")],
            [InlineKeyboardButton("🏆 Топ кланов", callback_data="clan_top")],
            [InlineKeyboardButton("⚔ Война", callback_data="clan_war")],
            [InlineKeyboardButton("📩 Сообщение клану", callback_data="clan_pm")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
        ]
        await update.message.reply_text(format_clan_info(clan), reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ДОПОЛНИТЕЛЬНЫЕ АДМИН-КОМАНДЫ ====================
async def setrank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not is_super_admin(user.id):
        await update.message.reply_text("⛔ Только супер-админ")
        return
    if len(context.args) < 2:
        await update.message.reply_text("/setrank [ID] [ранг 0-10]")
        return
    try:
        target_id = int(context.args[0])
        rank = int(context.args[1])
        if rank < 0 or rank > 10:
            await update.message.reply_text("❌ Ранг 0-10")
            return
        db.set_bot_rank(target_id, rank)
        await update.message.reply_text(f"✅ Ранг: {db.get_bot_rank_name(target_id)}")
    except ValueError:
        await update.message.reply_text("❌ Введите числа")

async def setagentlevel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not is_super_admin(user.id):
        await update.message.reply_text("⛔ Только супер-админ")
        return
    if len(context.args) < 2:
        await update.message.reply_text("/setagentlevel [ID] [уровень 0-3]")
        return
    try:
        target_id = int(context.args[0])
        level = int(context.args[1])
        if level < 0 or level > 3:
            await update.message.reply_text("❌ Уровень 0-3")
            return
        db.set_agent_level(target_id, level)
        await update.message.reply_text(f"✅ Уровень: {db.get_agent_level_name(target_id)}")
    except ValueError:
        await update.message.reply_text("❌ Введите числа")

async def setsuperadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if user.id != FOUNDER_ID:
        await update.message.reply_text("⛔ Только основатель")
        return
    if not context.args:
        await update.message.reply_text("/setsuperadmin [ID]")
        return
    try:
        db.add_super_admin(int(context.args[0]))
        await update.message.reply_text("✅ Супер-админ назначен")
    except ValueError:
        await update.message.reply_text("❌ Введите ID")

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not (has_bot_permission(user.id, "btn_agents_list") or db.get_agent_level(user.id) > 0):
        await update.message.reply_text("⛔ Нет доступа")
        return
    agents = db.get_all_agents()
    text = "🔰 Агенты поддержки\n━━━━━━━━━━━━━━━━\n\n"
    if not agents:
        text += "Нет агентов"
    else:
        for agent in agents:
            text += f"• {agent['first_name']} (@{agent['username']})\n  Уровень: {db.get_agent_level_name(agent['user_id'])}\n\n"
    await update.message.reply_text(text)

async def giverep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_bot_permission(user.id, "btn_give_rep"):
        await update.message.reply_text("⛔ Нет доступа")
        return
    if len(context.args) < 2:
        await update.message.reply_text("/giverep [ID клана] [количество]")
        return
    try:
        clan_id = int(context.args[0])
        rating = int(context.args[1])
        clan = db.get_clan(clan_id)
        if clan:
            db.add_clan_rating(clan_id, rating)
            await update.message.reply_text(f"✅ Клану {clan['name']} +{rating}")
    except ValueError:
        await update.message.reply_text("❌ Введите числа")

async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_bot_permission(user.id, "btn_blacklist"):
        await update.message.reply_text("⛔ Нет доступа")
        return
    blacklist = db.get_blacklist()
    text = "🚫 Черный список\n━━━━━━━━━━━━━━━━\n\n"
    if not blacklist:
        text += "Пуст"
    else:
        for u in blacklist:
            text += f"• {u['first_name']} (@{u['username']})\n  ID: {u['user_id']}\n  Причина: {u['reason']}\n\n"
    await update.message.reply_text(text)

# ==================== СПИСКИ ПРАВ ДЛЯ КНОПОК ====================
BOT_BUTTON_PERMISSIONS = {
    "btn_admin_panel": "⭐️ Админ панель",
    "btn_admins_list": "👥 Админы бота",
    "btn_agents_list": "🔰 Агенты поддержки",
    "btn_blacklist": "🚫 Черный список",
    "btn_give_rep": "⭐️ Выдать репутацию",
    "btn_commands": "📋 Все команды",
    "btn_chats": "🗂 Все чаты",
    "btn_ranks": "📊 Ранги бота",
    "btn_rank_names": "📝 Названия рангов",
    "btn_rank_perms": "⚙️ Права рангов",
    "btn_super_admins": "👑 Супер-админы",
    "btn_agent_levels": "📊 Уровни агентов",
    "btn_agent_names": "📝 Названия уровней АП",
    "btn_agent_perms": "⚙️ Права уровней АП",
    "btn_astats": "📊 Статистика жалоб (/astats)",
}

AGENT_BUTTON_PERMISSIONS = {
    "btn_answer_tickets": "✅ Отвечать на тикеты",
    "btn_close_tickets": "❌ Закрывать тикеты",
    "btn_manage_agents": "👥 Управлять агентами",
    "btn_view_reports": "📋 Просматривать жалобы",
    "btn_manage_blacklist": "🚫 Управлять ЧС",
    "btn_hstats": "📊 Статистика вопросов (/hstats)",
}

CHAT_BUTTON_PERMISSIONS = {
    "btn_chat_admin": "👑 Админ панель",
    "btn_kick": "👢 Кик",
    "btn_warn": "⚠️ Предупреждение",
    "btn_mute": "🔇 Мут",
    "btn_ban": "🔨 Бан",
}

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ONLY_OWNER_MODE
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat = query.message.chat if query.message else None
    data = query.data

    db.update_user_activity(user.id)

    if db.is_blacklisted(user.id):
        await query.edit_message_text("❌ Вы в черном списке бота")
        return

    if ONLY_OWNER_MODE and user.id != FOUNDER_ID:
        await query.answer("⛔ Бот временно недоступен", show_alert=True)
        return

    # Награды
    if data.startswith("give_award_"):
        target_id = int(data.split("_")[-1])
        context.user_data['awarding_user'] = target_id
        await query.edit_message_text("✏️ Введите текст награды:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="cancel_award")]]))
    elif data == "cancel_award":
        context.user_data['awarding_user'] = None
        await query.edit_message_text("❌ Выдача награды отменена")
    elif data.startswith("show_awards_"):
        target_id = int(data.split("_")[-1])
        awards = db.get_user_awards(target_id)
        if not awards:
            await query.edit_message_text("🏅 Наград пока нет")
            return
        text = f"🏅 Награды пользователя\n━━━━━━━━━━━━━━━━\n\n"
        for award in awards:
            award_date = datetime.strptime(award['award_date'], '%Y-%m-%d %H:%M:%S')
            award_date = award_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            time_ago = now - award_date
            days = time_ago.days
            hours = time_ago.seconds // 3600
            minutes = (time_ago.seconds % 3600) // 60
            if days > 0:
                time_str = f"{days} дн. назад"
            elif hours > 0:
                time_str = f"{hours} ч. назад"
            elif minutes > 0:
                time_str = f"{minutes} мин. назад"
            else:
                time_str = "только что"
            text += f"🏅 {award['award_text']}\n   От: @{award['awarded_by_username']}\n   {time_str}\n\n"
        await query.edit_message_text(text)

    # Ответ на жалобу
    elif data.startswith("reply_report_"):
        parts = data.split("_")
        report_id = int(parts[2])
        reporter_id = int(parts[3])
        context.user_data['replying_report'] = {'report_id': report_id, 'reporter_id': reporter_id}
        await query.edit_message_text("✏️ Введите текст ответа для пользователя:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="cancel_reply_report")]]))
    elif data == "cancel_reply_report":
        context.user_data['replying_report'] = None
        await query.edit_message_text("❌ Отправка ответа отменена")

    # Главное меню
    elif data == "start_menu":
        text = f"""👋 Добро пожаловать в Fluxy | Чат-менеджер.
━━━━━━━━━━━━━━━━

🆔 Ваш ID: {user.id}
🎖️ Ваш ранг: {db.get_bot_rank_name(user.id)}
📊 Уровень агента: {db.get_agent_level_name(user.id)}

━━━━━━━━━━━━━━━━
Для продолжения нажмите на кнопку ниже ⬇️"""
        keyboard = []
        if has_bot_permission(user.id, "btn_admin_panel"):
            keyboard.append([InlineKeyboardButton("⭐️ Админ панель бота", callback_data="admin_panel")])
        if chat and chat.type != "private":
            if has_chat_permission(chat.id, user.id, "btn_chat_admin"):
                keyboard.append([InlineKeyboardButton("👑 Админ панель чата", callback_data="chat_admin_panel")])
        keyboard.append([InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")])
        keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="help"), InlineKeyboardButton("📋 Команды", callback_data="commands")])
        keyboard.append([InlineKeyboardButton("🔰 Агенты поддержки", callback_data="agents_list")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Админ-панель бота
    elif data == "admin_panel":
        if not has_bot_permission(user.id, "btn_admin_panel"):
            await query.edit_message_text("⛔ У вас нет доступа")
            return
        text = "⭐️ Админ панель бота Fluxy\n━━━━━━━━━━━━━━━━\nВыберите действие:"
        keyboard = []
        row = []
        if has_bot_permission(user.id, "btn_admins_list"):
            row.append(InlineKeyboardButton("👥 Админы бота", callback_data="bot_admins_list"))
        if has_bot_permission(user.id, "btn_agents_list"):
            row.append(InlineKeyboardButton("🔰 Агенты", callback_data="list_agents"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_blacklist"):
            row.append(InlineKeyboardButton("🚫 Черный список", callback_data="black_list"))
        if has_bot_permission(user.id, "btn_give_rep"):
            row.append(InlineKeyboardButton("⭐️ Репутация", callback_data="give_rep"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_ranks"):
            row.append(InlineKeyboardButton("📊 Ранги бота", callback_data="bot_ranks"))
        if has_bot_permission(user.id, "btn_rank_names"):
            row.append(InlineKeyboardButton("📝 Названия рангов", callback_data="bot_rank_names"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_rank_perms"):
            row.append(InlineKeyboardButton("⚙️ Права рангов", callback_data="bot_rank_permissions"))
        if has_bot_permission(user.id, "btn_super_admins"):
            row.append(InlineKeyboardButton("👑 Супер-админы", callback_data="super_admins_list"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_agent_levels"):
            row.append(InlineKeyboardButton("📊 Уровни агентов", callback_data="agent_levels"))
        if has_bot_permission(user.id, "btn_agent_names"):
            row.append(InlineKeyboardButton("📝 Названия уровней АП", callback_data="agent_level_names"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_agent_perms"):
            row.append(InlineKeyboardButton("⚙️ Права уровней АП", callback_data="agent_level_permissions"))
        if has_bot_permission(user.id, "btn_commands"):
            row.append(InlineKeyboardButton("📋 Все команды", callback_data="all_commands"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_chats"):
            row.append(InlineKeyboardButton("🗂 Все чаты", callback_data="all_chats"))
        row.append(InlineKeyboardButton("⬅️ Выход", callback_data="start_menu"))
        keyboard.append(row)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Управление админами
    elif data == "bot_admins_list":
        if not has_bot_permission(user.id, "btn_admins_list"): return
        admins = db.get_all_bot_admins()
        text = "👥 Админы бота\n━━━━━━━━━━━━━━━━\n\n"
        if not admins:
            text += "Нет админов"
        else:
            for admin in admins:
                rank_name = db.get_bot_rank_name(admin['user_id'])
                text += f"• {admin['first_name']} (@{admin['username']})\n  Ранг: {rank_name}\n  ID: {admin['user_id']}\n\n"
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data="add_admin"), InlineKeyboardButton("➖ Удалить", callback_data="remove_admin")],
            [InlineKeyboardButton("📊 Изменить ранг", callback_data="change_admin_rank")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_admin":
        context.user_data['adding_admin'] = True
        await query.edit_message_text("Введите ID пользователя:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="bot_admins_list")]]))
    elif data == "remove_admin":
        context.user_data['removing_admin'] = True
        await query.edit_message_text("Введите ID админа:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="bot_admins_list")]]))
    elif data == "change_admin_rank":
        context.user_data['changing_admin_rank'] = True
        await query.edit_message_text("Введите ID админа и новый ранг (0-10) через пробел:\nНапример: 123456789 8", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="bot_admins_list")]]))

    # Управление агентами
    elif data == "list_agents":
        if not has_bot_permission(user.id, "btn_agents_list"): return
        agents = db.get_all_agents()
        text = "🔰 Агенты поддержки\n━━━━━━━━━━━━━━━━\n\n"
        if not agents:
            text += "Нет агентов"
        else:
            for agent in agents:
                text += f"• {agent['first_name']} (@{agent['username']})\n  Уровень: {db.get_agent_level_name(agent['user_id'])}\n  ID: {agent['user_id']}\n\n"
        keyboard = [
            [InlineKeyboardButton("➕ Назначить", callback_data="add_agent"), InlineKeyboardButton("➖ Удалить", callback_data="remove_agent")],
            [InlineKeyboardButton("📊 Изменить уровень", callback_data="change_agent_level")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_agent":
        context.user_data['adding_agent'] = True
        await query.edit_message_text("Введите ID пользователя:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="list_agents")]]))
    elif data == "remove_agent":
        context.user_data['removing_agent'] = True
        await query.edit_message_text("Введите ID агента:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="list_agents")]]))
    elif data == "change_agent_level":
        context.user_data['changing_agent_level'] = True
        await query.edit_message_text("Введите ID и уровень (1-3) через пробел:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="list_agents")]]))

    # Черный список
    elif data == "black_list":
        if not has_bot_permission(user.id, "btn_blacklist"): return
        blacklist = db.get_blacklist()
        text = "🚫 Черный список\n━━━━━━━━━━━━━━━━\n\n"
        if not blacklist:
            text += "Пуст"
        else:
            for u in blacklist:
                text += f"• {u['first_name']} (@{u['username']})\n  ID: {u['user_id']}\n  Причина: {u['reason']}\n\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]]))

    # Репутация
    elif data == "give_rep":
        if not has_bot_permission(user.id, "btn_give_rep"): return
        text = "⭐️ Выдать репутацию клану\n━━━━━━━━━━━━━━━━\n\nИспользуйте команду:\n/giverep [ID клана] [количество]"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]]))

    # Ранги бота
    elif data == "bot_ranks":
        if not has_bot_permission(user.id, "btn_ranks"): return
        text = "📊 Ранги бота\n━━━━━━━━━━━━━━━━\n\n"
        for level, name in db.get_all_bot_rank_names().items():
            text += f"{level}. {name}\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]]))
    elif data == "bot_rank_names":
        if not has_bot_permission(user.id, "btn_rank_names"): return
        text = "📝 Названия рангов бота\n━━━━━━━━━━━━━━━━\n\nВыберите ранг (1-9):"
        keyboard = []
        for level in range(1, 10):
            name = db.get_all_bot_rank_names().get(level, f"Ранг {level}")
            keyboard.append([InlineKeyboardButton(f"Ранг {level}: {name}", callback_data=f"edit_bot_rank_name_{level}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("edit_bot_rank_name_"):
        if not has_bot_permission(user.id, "btn_rank_names"): return
        rank_level = int(data.split("_")[-1])
        context.user_data['editing_bot_rank'] = rank_level
        await query.edit_message_text(f"Введите новое название для ранга {rank_level}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="bot_rank_names")]]))

    # Права рангов бота
    elif data == "bot_rank_permissions":
        if not has_bot_permission(user.id, "btn_rank_perms"): return
        text = "⚙️ Права рангов бота\n━━━━━━━━━━━━━━━━\n\nВыберите ранг (1-9):"
        keyboard = []
        for level in range(1, 10):
            name = db.get_all_bot_rank_names().get(level, f"Ранг {level}")
            keyboard.append([InlineKeyboardButton(f"{name} (Ранг {level})", callback_data=f"edit_bot_perms_{level}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("edit_bot_perms_"):
        if not has_bot_permission(user.id, "btn_rank_perms"): return
        rank_level = int(data.split("_")[-1])
        rank_name = db.get_bot_rank_name(rank_level)
        permissions = db.get_bot_rank_permissions(rank_level)
        text = f"⚙️ Доступ для ранга: {rank_name}\n━━━━━━━━━━━━━━━━\n\nНажмите чтобы переключить:\n\n"
        keyboard = []
        for perm, desc in BOT_BUTTON_PERMISSIONS.items():
            if perm in permissions:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="bot_rank_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("toggle_bot_perm_"):
        if not has_bot_permission(user.id, "btn_rank_perms"): return
        parts = data.split("_")
        rank_level = int(parts[3])
        permission = "_".join(parts[4:])
        perms = db.get_bot_rank_permissions(rank_level)
        if permission in perms:
            db.remove_bot_rank_permission(rank_level, permission)
        else:
            db.add_bot_rank_permission(rank_level, permission)
        rank_name = db.get_bot_rank_name(rank_level)
        perms = db.get_bot_rank_permissions(rank_level)
        text = f"⚙️ Доступ для ранга: {rank_name}\n━━━━━━━━━━━━━━━━\n\nНажмите чтобы переключить:\n\n"
        keyboard = []
        for perm, desc in BOT_BUTTON_PERMISSIONS.items():
            if perm in perms:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="bot_rank_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Супер-админы
    elif data == "super_admins_list":
        if not has_bot_permission(user.id, "btn_super_admins"): return
        super_admins = db.get_all_super_admins()
        text = "👑 Супер-админы\n━━━━━━━━━━━━━━━━\n\n"
        text += f"• Основатель (ID: {FOUNDER_ID})\n\n"
        for admin in super_admins:
            text += f"• {admin['first_name']} (@{admin['username']})\n  ID: {admin['user_id']}\n\n"
        keyboard = []
        if user.id == FOUNDER_ID:
            keyboard.append([InlineKeyboardButton("➕ Добавить", callback_data="add_super_admin"), InlineKeyboardButton("➖ Удалить", callback_data="remove_super_admin")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_super_admin":
        if user.id != FOUNDER_ID:
            await query.answer("⛔ Только основатель", show_alert=True); return
        context.user_data['adding_super_admin'] = True
        await query.edit_message_text("Введите ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="super_admins_list")]]))
    elif data == "remove_super_admin":
        if user.id != FOUNDER_ID:
            await query.answer("⛔ Только основатель", show_alert=True); return
        context.user_data['removing_super_admin'] = True
        await query.edit_message_text("Введите ID:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="super_admins_list")]]))

    # Уровни агентов
    elif data == "agent_levels":
        if not has_bot_permission(user.id, "btn_agent_levels"): return
        text = "📊 Уровни агентов\n━━━━━━━━━━━━━━━━\n\n"
        for level, name in db.get_all_agent_level_names().items():
            if level > 0:
                text += f"{level}. {name}\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]]))
    elif data == "agent_level_names":
        if not has_bot_permission(user.id, "btn_agent_names"): return
        text = "📝 Названия уровней агентов\n━━━━━━━━━━━━━━━━\n\nВыберите уровень (1-3):"
        keyboard = []
        for level in range(1, 4):
            name = db.get_all_agent_level_names().get(level, f"Уровень {level}")
            keyboard.append([InlineKeyboardButton(f"Уровень {level}: {name}", callback_data=f"edit_agent_level_name_{level}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("edit_agent_level_name_"):
        if not has_bot_permission(user.id, "btn_agent_names"): return
        level = int(data.split("_")[-1])
        context.user_data['editing_agent_level'] = level
        await query.edit_message_text(f"Введите новое название для уровня {level}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="agent_level_names")]]))

    # Права уровней агентов
    elif data == "agent_level_permissions":
        if not has_bot_permission(user.id, "btn_agent_perms"): return
        text = "⚙️ Права уровней агентов\n━━━━━━━━━━━━━━━━\n\nВыберите уровень (1-3):"
        keyboard = []
        for level in range(1, 4):
            name = db.get_all_agent_level_names().get(level, f"Уровень {level}")
            keyboard.append([InlineKeyboardButton(f"{name} (Уровень {level})", callback_data=f"edit_agent_perms_{level}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("edit_agent_perms_"):
        if not has_bot_permission(user.id, "btn_agent_perms"): return
        level = int(data.split("_")[-1])
        level_name = db.get_agent_level_name(level) if level > 0 else f"Уровень {level}"
        perms = db.get_agent_level_permissions(level)
        text = f"⚙️ Доступ для уровня: {level_name}\n━━━━━━━━━━━━━━━━\n\nНажмите чтобы переключить:\n\n"
        keyboard = []
        for perm, desc in AGENT_BUTTON_PERMISSIONS.items():
            if perm in perms:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_agent_perm_{level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_agent_perm_{level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="agent_level_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("toggle_agent_perm_"):
        if not has_bot_permission(user.id, "btn_agent_perms"): return
        parts = data.split("_")
        level = int(parts[3])
        permission = "_".join(parts[4:])
        perms = db.get_agent_level_permissions(level)
        if permission in perms:
            db.remove_agent_level_permission(level, permission)
        else:
            db.add_agent_level_permission(level, permission)
        level_name = db.get_agent_level_name(level) if level > 0 else f"Уровень {level}"
        perms = db.get_agent_level_permissions(level)
        text = f"⚙️ Доступ для уровня: {level_name}\n━━━━━━━━━━━━━━━━\n\nНажмите чтобы переключить:\n\n"
        keyboard = []
        for perm, desc in AGENT_BUTTON_PERMISSIONS.items():
            if perm in perms:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_agent_perm_{level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_agent_perm_{level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="agent_level_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Все команды и чаты
    elif data == "all_commands":
        if not has_bot_permission(user.id, "btn_commands"): return
        text = "📋 Все команды бота\n━━━━━━━━━━━━━━━━\n\n"
        text += "/profile - Профиль\n/clan - Клан\n/clan_top - Топ кланов\n/help - Помощь\n/report - Жалоба\n/ping - Пинг\n/stats - Профиль игрока\n/id - Узнать ID\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]]))
    elif data == "all_chats":
        if not has_bot_permission(user.id, "btn_chats"): return
        chats = db.get_all_chats()
        text = "🗂 Все чаты\n━━━━━━━━━━━━━━━━\n\n"
        if not chats:
            text += "Нет чатов"
        else:
            for chat_info in chats:
                text += f"• {chat_info['chat_title']} ({chat_info['chat_type']})\n  ID: {chat_info['chat_id']}\n\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]]))

    # Админ-панель чата
    elif data == "chat_admin_panel":
        if not chat or chat.type == "private":
            await query.edit_message_text("⛔ Только для групп"); return
        if not has_chat_permission(chat.id, user.id, "btn_chat_admin"):
            await query.edit_message_text("⛔ У вас нет доступа"); return
        user_rank = db.get_chat_member_rank(chat.id, user.id)
        rank_name = db.get_rank_name(chat.id, user_rank)
        text = f"""👑 Админ панель чата
━━━━━━━━━━━━━━━━

Чат: {chat.title}
Ваш ранг: {rank_name} ({user_rank})

Команды модерации:
/kick [ID/@username] [причина]
/warn [ID/@username] [причина]
/ban [ID/@username] [причина]
/mute [ID/@username] [время] [причина]
/unmute [ID/@username]
/unban [ID/@username]
/unwarn [ID/@username]
/setadm [ID/@username] [0-5]

Выберите действие:"""
        keyboard = [
            [InlineKeyboardButton("👥 Админы чата", callback_data="chat_admins_list")],
            [InlineKeyboardButton("📊 Ранги чата", callback_data="chat_ranks_list")],
            [InlineKeyboardButton("🛡 Антиспам", callback_data="antispam_settings")],
            [InlineKeyboardButton("👋 Приветствие", callback_data="welcome_settings")],
        ]
        if is_chat_owner(chat.id, user.id):
            keyboard.append([InlineKeyboardButton("⚙️ Настройка прав рангов", callback_data="chat_rank_permissions")])
            keyboard.append([InlineKeyboardButton("📝 Названия рангов", callback_data="chat_rank_names")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # 🆕 АНТИСПАМ НАСТРОЙКИ
    elif data == "antispam_settings":
        if not chat or chat.type == "private": return
        settings = db.get_chat_settings(chat.id)
        antispam_enabled = settings.get("antispam_enabled") if settings else 0
        antispam_limit = settings.get("antispam_limit", 5) if settings else 5
        
        text = f"""🛡 Настройки антиспама
━━━━━━━━━━━━━━━━

Статус: {'✅ Включён' if antispam_enabled else '❌ Выключен'}
Лимит: {antispam_limit} сообщений/секунду

Выберите действие:"""
        
        keyboard = [
            [InlineKeyboardButton(
                "❌ Выключить" if antispam_enabled else "✅ Включить",
                callback_data="toggle_antispam"
            )],
            [InlineKeyboardButton("⚙️ Изменить лимит", callback_data="change_antispam_limit")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "toggle_antispam":
        if not chat or chat.type == "private": return
        settings = db.get_chat_settings(chat.id)
        current_status = settings.get("antispam_enabled") if settings else 0
        db.save_chat_settings(chat.id, antispam_enabled=0 if current_status else 1)
        await query.answer(
            "✅ Антиспам включён" if not current_status else "❌ Антиспам выключен",
            show_alert=True
        )
        settings = db.get_chat_settings(chat.id)
        antispam_enabled = settings.get("antispam_enabled")
        antispam_limit = settings.get("antispam_limit", 5)
        text = f"""🛡 Настройки антиспама
━━━━━━━━━━━━━━━━

Статус: {'✅ Включён' if antispam_enabled else '❌ Выключен'}
Лимит: {antispam_limit} сообщений/секунду

Выберите действие:"""
        keyboard = [
            [InlineKeyboardButton(
                "❌ Выключить" if antispam_enabled else "✅ Включить",
                callback_data="toggle_antispam"
            )],
            [InlineKeyboardButton("⚙️ Изменить лимит", callback_data="change_antispam_limit")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "change_antispam_limit":
        if not chat or chat.type == "private": return
        context.user_data['changing_antispam_limit'] = True
        await query.edit_message_text(
            "💬 Отправьте число — сколько сообщений в секунду разрешено.\n"
            "Например: <code>5</code>\n\n"
            "Если пользователь превысит лимит, он будет исключён!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="antispam_settings")]])
        )
    
    # 🆕 ПРИВЕТСТВИЕ НАСТРОЙКИ
    elif data == "welcome_settings":
        if not chat or chat.type == "private": return
        settings = db.get_chat_settings(chat.id)
        welcome_enabled = settings.get("welcome_enabled") if settings else 0
        welcome_text = settings.get("welcome_text", 'Привет, {name}! Добро пожаловать в {chat}!') if settings else 'Привет, {name}! Добро пожаловать в {chat}!'
        
        text = f"""👋 Настройки приветствия
━━━━━━━━━━━━━━━━

Статус: {'✅ Включено' if welcome_enabled else '❌ Выключено'}
Текст: {welcome_text}

Выберите действие:"""
        
        keyboard = [
            [InlineKeyboardButton(
                "❌ Выключить" if welcome_enabled else "✅ Включить",
                callback_data="toggle_welcome"
            )],
            [InlineKeyboardButton("⚙️ Изменить текст", callback_data="change_welcome_text")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "toggle_welcome":
        if not chat or chat.type == "private": return
        settings = db.get_chat_settings(chat.id)
        current_status = settings.get("welcome_enabled") if settings else 0
        db.save_chat_settings(chat.id, welcome_enabled=0 if current_status else 1)
        await query.answer(
            "✅ Приветствие включено" if not current_status else "❌ Приветствие выключено",
            show_alert=True
        )
        settings = db.get_chat_settings(chat.id)
        welcome_enabled = settings.get("welcome_enabled")
        welcome_text = settings.get("welcome_text", 'Привет, {name}! Добро пожаловать в {chat}!')
        text = f"""👋 Настройки приветствия
━━━━━━━━━━━━━━━━

Статус: {'✅ Включено' if welcome_enabled else '❌ Выключено'}
Текст: {welcome_text}

Выберите действие:"""
        keyboard = [
            [InlineKeyboardButton(
                "❌ Выключить" if welcome_enabled else "✅ Включить",
                callback_data="toggle_welcome"
            )],
            [InlineKeyboardButton("⚙️ Изменить текст", callback_data="change_welcome_text")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "change_welcome_text":
        if not chat or chat.type == "private": return
        context.user_data['changing_welcome_text'] = True
        await query.edit_message_text(
            "👋 Отправьте текст приветствия.\n"
            "Можно использовать:\n"
            "• <code>{name}</code> — имя участника\n"
            "• <code>{chat}</code> — название чата\n\n"
            "Пример: <code>Привет, {name}! Рады видеть в {chat} 🎉</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="welcome_settings")]])
        )

    elif data == "chat_admins_list":
        if not chat or chat.type == "private": return
        admins = db.get_all_chat_admins(chat.id)
        text = f"👥 Админы чата\n━━━━━━━━━━━━━━━━\n\n"
        if not admins:
            text += "Нет админов"
        else:
            for admin in admins:
                rank_name = db.get_rank_name(chat.id, admin['chat_rank'])
                text += f"• {admin['first_name']} (@{admin['username']})\n  Ранг: {rank_name} ({admin['chat_rank']})\n  ID: {admin['user_id']}\n\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")]]))
    elif data == "chat_ranks_list":
        if not chat or chat.type == "private": return
        text = f"📊 Ранги чата\n━━━━━━━━━━━━━━━━\n\n"
        rank_names = db.get_all_rank_names(chat.id)
        for level, name in rank_names.items():
            count = len(db.get_chat_members_by_rank(chat.id, level))
            text += f"{level}. {name} — {count} участников\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")]]))
    elif data == "chat_rank_permissions":
        if not chat or chat.type == "private": return
        if not is_chat_owner(chat.id, user.id):
            await query.edit_message_text("⛔ Только владелец чата"); return
        text = "⚙️ Настройка прав рангов\n━━━━━━━━━━━━━━━━\n\nВыберите ранг (1-4):"
        keyboard = []
        for level in range(1, 5):
            rank_name = db.get_rank_name(chat.id, level)
            keyboard.append([InlineKeyboardButton(f"{rank_name} (Ранг {level})", callback_data=f"edit_chat_perms_{level}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("edit_chat_perms_"):
        if not chat or chat.type == "private": return
        if not is_chat_owner(chat.id, user.id): return
        rank_level = int(data.split("_")[-1])
        rank_name = db.get_rank_name(chat.id, rank_level)
        perms = db.get_chat_rank_permissions(chat.id, rank_level)
        text = f"⚙️ Доступ для ранга: {rank_name}\n━━━━━━━━━━━━━━━━\n\nНажмите чтобы переключить:\n\n"
        keyboard = []
        for perm, desc in CHAT_BUTTON_PERMISSIONS.items():
            if perm in perms:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_chat_perm_{rank_level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_chat_perm_{rank_level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="chat_rank_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("toggle_chat_perm_"):
        if not chat or chat.type == "private": return
        if not is_chat_owner(chat.id, user.id): return
        parts = data.split("_")
        rank_level = int(parts[3])
        permission = "_".join(parts[4:])
        perms = db.get_chat_rank_permissions(chat.id, rank_level)
        if permission in perms:
            db.remove_chat_rank_permission(chat.id, rank_level, permission)
        else:
            db.add_chat_rank_permission(chat.id, rank_level, permission)
        rank_name = db.get_rank_name(chat.id, rank_level)
        perms = db.get_chat_rank_permissions(chat.id, rank_level)
        text = f"⚙️ Доступ для ранга: {rank_name}\n━━━━━━━━━━━━━━━━\n\nНажмите чтобы переключить:\n\n"
        keyboard = []
        for perm, desc in CHAT_BUTTON_PERMISSIONS.items():
            if perm in perms:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_chat_perm_{rank_level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_chat_perm_{rank_level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="chat_rank_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "chat_rank_names":
        if not chat or chat.type == "private": return
        if not is_chat_owner(chat.id, user.id):
            await query.edit_message_text("⛔ Только владелец чата"); return
        text = "📝 Названия рангов чата\n━━━━━━━━━━━━━━━━\n\n"
        text += "Базовые (нельзя изменить):\n"
        text += f"0. {db.get_rank_name(chat.id, 0)}\n"
        text += f"5. {db.get_rank_name(chat.id, 5)}\n\n"
        text += "Настраиваемые (1-4):\n"
        keyboard = []
        for level in range(1, 5):
            name = db.get_rank_name(chat.id, level)
            keyboard.append([InlineKeyboardButton(f"Ранг {level}: {name}", callback_data=f"edit_chat_rank_name_{level}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="chat_admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("edit_chat_rank_name_"):
        if not chat or chat.type == "private": return
        if not is_chat_owner(chat.id, user.id): return
        rank_level = int(data.split("_")[-1])
        context.user_data['editing_chat_rank'] = rank_level
        await query.edit_message_text(f"Введите новое название для ранга {rank_level}:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="chat_rank_names")]]))

    # Профиль
    elif data == "profile":
        clan = db.get_user_clan(user.id)
        clan_name = clan['name'] if clan else "Нет клана"
        clan_rating = clan['rating'] if clan else 0
        text = f"""👤 Ваш профиль
━━━━━━━━━━━━━━━━

🆔 Ваш ID: {user.id}
🎖️ Ранг бота: {db.get_bot_rank_name(user.id)}
📊 Уровень агента: {db.get_agent_level_name(user.id)}

🛡️ Ваш клан: {clan_name}
🏆 Рейтинг клана: {clan_rating}

━━━━━━━━━━━━━━━━"""
        if chat and chat.type != "private":
            chat_rank = db.get_rank_name(chat.id, db.get_chat_member_rank(chat.id, user.id))
            text += f"\n👑 Ранг в чате: {chat_rank}"
        keyboard = [
            [InlineKeyboardButton("🏆 Награды", callback_data=f"show_awards_{user.id}")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Кланы
    elif data == "clan_menu":
        clan = db.get_user_clan(user.id)
        if not clan:
            text = "Вы не состоите в клане\n\nХотите создать клан?"
            keyboard = [
                [InlineKeyboardButton("➕ Создать клан", callback_data="create_clan")],
                [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
            ]
        else:
            text = format_clan_info(clan)
            keyboard = [
                [InlineKeyboardButton("👥 Участники клана", callback_data="clan_members")],
                [InlineKeyboardButton("🔒 Вход в клан", callback_data="clan_join_settings")],
                [InlineKeyboardButton("✉️ Сообщения клана", callback_data="clan_messages")],
                [InlineKeyboardButton("🏆 Топ кланов", callback_data="clan_top")],
                [InlineKeyboardButton("⚔ Обьявить войну", callback_data="clan_war")],
                [InlineKeyboardButton("📩 Сообщение клану", callback_data="clan_pm")],
                [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
            ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "create_clan":
        context.user_data['creating_clan'] = True
        await query.edit_message_text("Введите название клана:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="clan_menu")]]))
    elif data == "clan_members":
        clan = db.get_user_clan(user.id)
        if not clan: return
        members = db.get_clan_members(clan['clan_id'])
        text = f"👥 Участники клана {clan['name']}\n━━━━━━━━━━━━━━━━\n\n"
        for member in members:
            role_text = "Лидер" if member['role'] == 'leader' else "Участник"
            text += f"• {member['first_name']} (@{member['username']}) - {role_text}\n  ID: {member['user_id']}\n\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="clan_menu")]]))
    elif data == "clan_join_settings":
        clan = db.get_user_clan(user.id)
        if not clan: return
        clan_member = db.get_clan_member(user.id)
        if not clan_member or clan_member['role'] != 'leader':
            await query.edit_message_text("Только лидер клана может менять настройки"); return
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data="join_yes"), InlineKeyboardButton("❌ Нет", callback_data="join_no")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="clan_menu")]
        ]
        await query.edit_message_text("Разрешить вход в клан?", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "join_yes":
        clan = db.get_user_clan(user.id)
        if clan:
            db.set_clan_join_enabled(clan['clan_id'], True)
            await query.answer("✅ Вход разрешен", show_alert=True)
            await query.edit_message_text("✅ Вход в клан разрешен")
    elif data == "join_no":
        clan = db.get_user_clan(user.id)
        if clan:
            db.set_clan_join_enabled(clan['clan_id'], False)
            await query.answer("❌ Вход запрещен", show_alert=True)
            await query.edit_message_text("❌ Вход в клан запрещен")
    elif data == "clan_messages":
        clan = db.get_user_clan(user.id)
        if not clan: return
        messages = db.get_clan_messages(clan['clan_id'])
        text = f"✉️ Сообщения клана {clan['name']}\n━━━━━━━━━━━━━━━━\n\n"
        if not messages:
            text += "Нет сообщений"
        else:
            for msg in messages[:10]:
                text += f"• {msg['username']}: {msg['message']}\n  {msg['sent_date']}\n\n"
        keyboard = [
            [InlineKeyboardButton("➕ Написать", callback_data="send_clan_message")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="clan_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "send_clan_message":
        context.user_data['sending_clan_message'] = True
        await query.edit_message_text("Введите сообщение для клана:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="clan_messages")]]))
    elif data == "clan_top":
        top_clans = db.get_top_clans()
        text = "🏆 Топ кланов\n━━━━━━━━━━━━━━━━\n\n"
        if not top_clans:
            text += "Пока нет кланов"
        else:
            medals = ["🥇", "🥈", "🥉"]
            for i, clan in enumerate(top_clans[:10]):
                medal = medals[i] if i < 3 else f"{i+1}."
                text += f"{medal} {clan['name']} — {clan['rating']}\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="clan_menu")]]))
    elif data == "clan_war":
        clan = db.get_user_clan(user.id)
        if not clan: return
        clan_member = db.get_clan_member(user.id)
        if not clan_member or clan_member['role'] != 'leader':
            await query.edit_message_text("Только лидер клана может объявить войну"); return
        context.user_data['war_state'] = 'waiting_target'
        await query.edit_message_text("Введите ID клана противника:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="clan_menu")]]))
    elif data == "war_confirm":
        target_clan_id = context.user_data.get('war_target')
        rating = context.user_data.get('war_rating')
        if target_clan_id and rating:
            target_clan = db.get_clan(target_clan_id)
            user_clan = db.get_user_clan(user.id)
            if target_clan and user_clan:
                await query.edit_message_text(f"⚔ Война объявлена!\n{user_clan['name']} vs {target_clan['name']}\nНа кону: {rating} рейтинга")
            else:
                await query.edit_message_text("❌ Ошибка")
        else:
            await query.edit_message_text("❌ Ошибка данных")
        context.user_data['war_target'] = None
        context.user_data['war_rating'] = None
        context.user_data['war_state'] = None
    elif data == "war_cancel":
        context.user_data['war_target'] = None
        context.user_data['war_rating'] = None
        context.user_data['war_state'] = None
        await query.edit_message_text("❌ Война отменена")
    elif data == "clan_pm":
        keyboard = [
            [InlineKeyboardButton("📤 Отправить", callback_data="send_pm")],
            [InlineKeyboardButton("📥 Входящие", callback_data="inbox_pm")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="clan_menu")]
        ]
        await query.edit_message_text("📩 Сообщение клану\n━━━━━━━━━━━━━━━━\nВыберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "send_pm":
        context.user_data['sending_pm'] = True
        await query.edit_message_text("Введите ID клана и сообщение через пробел:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="clan_pm")]]))
    elif data == "inbox_pm":
        await query.edit_message_text("📥 Входящие сообщения\n━━━━━━━━━━━━━━━━\n\nНет входящих")

    # Помощь
    elif data == "help":
        text = """❓ Помощь
━━━━━━━━━━━━━━━━

Основные команды:
/start - Запуск бота
/help - Помощь
/ping - Пинг бота
/id - Узнать ID
/stats - Профиль пользователя
/profile - Свой профиль
/clan - Меню клана
/clan_top - Топ кланов
/report - Жалоба
"""
        if chat and chat.type != "private":
            if has_chat_permission(chat.id, user.id, "btn_kick"):
                text += "\n/kick [ID/@username] [причина]\n/unban [ID/@username]\n"
            if has_chat_permission(chat.id, user.id, "btn_warn"):
                text += "/warn [ID/@username] [причина]\n/unwarn [ID/@username]\n"
            if has_chat_permission(chat.id, user.id, "btn_ban"):
                text += "/ban [ID/@username] [причина]\n"
            if has_chat_permission(chat.id, user.id, "btn_mute"):
                text += "/mute [ID/@username] [время] [причина]\n/unmute [ID/@username]\n"
            if is_chat_owner(chat.id, user.id) or has_chat_permission(chat.id, user.id, "btn_chat_admin"):
                text += "\n/setadm [ID/@username] [0-5] - Выдать ранг в чате\n/admins - Список админов чата\n"
        if has_bot_permission(user.id, "btn_blacklist"):
            text += "\nЧС:\n/permban [ID] [причина]\n/unperm [ID]\n"
        if has_astats_permission(user.id):
            text += "\n/astats - Статистика жалоб\n"
        if has_hstats_permission(user.id):
            text += "\n/hstats - Статистика вопросов\n"
        if user.id == FOUNDER_ID:
            text += "\n/onlyowner - Режим «только основатель»\n/botadmins - Админы бота\n"
        text += "\nВыберите тип обращения:"
        keyboard = [
            [InlineKeyboardButton("❗️ Жалоба", callback_data="help_report")],
            [InlineKeyboardButton("❓ Вопрос", callback_data="help_question")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "help_report":
        text = "❗️ Жалоба\n━━━━━━━━━━━━━━━━\n\nОтветьте на сообщение нарушителя командой:\n/report <причина>"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="help")]]))
    elif data == "help_question":
        if is_staff(user.id):
            await query.answer("⛔ Админы и агенты не могут задавать вопросы", show_alert=True)
            return
        context.user_data['question_state'] = 'waiting_question'
        text = "❓ Вопрос\n━━━━━━━━━━━━━━━━\n\nНапишите ваш вопрос одним сообщением."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Отмена", callback_data="help")]]))

    # Тикеты
    elif data.startswith("accept_ticket_"):
        ticket_id = int(data.split("_")[-1])
        ticket = db.get_ticket(ticket_id)
        if not ticket or ticket['status'] != 'open':
            await query.answer("❌ Тикет уже принят или закрыт", show_alert=True); return
        db.assign_ticket(ticket_id, user.id, user.username or f"id{user.id}")
        context.user_data['answering_ticket'] = ticket_id
        await query.edit_message_text(f"✅ Тикет #{ticket_id} принят\n\n✏️ Напишите ответ:")
    elif data.startswith("close_ticket_"):
        ticket_id = int(data.split("_")[-1])
        ticket = db.get_ticket(ticket_id)
        if not ticket:
            await query.answer("❌ Тикет не найден", show_alert=True); return
        db.close_ticket(ticket_id, "Закрыт без ответа")
        await query.edit_message_text(f"✅ Тикет #{ticket_id} закрыт")

    # Команды
    elif data == "commands":
        text = "📋 Доступные команды\n━━━━━━━━━━━━━━━━\n\n"
        text += "/profile - Профиль\n"
        text += "/clan - Клан\n"
        text += "/clan_top - Топ кланов\n"
        text += "/help - Помощь\n"
        text += "/report - Жалоба\n"
        text += "/ping - Пинг\n"
        text += "/stats - Профиль игрока\n"
        text += "/id - Узнать ID\n"

        if chat and chat.type != "private":
            mod_commands = ""
            if has_chat_permission(chat.id, user.id, "btn_kick"):
                mod_commands += "/kick [ID/@username] [причина]\n/unban [ID/@username]\n"
            if has_chat_permission(chat.id, user.id, "btn_warn"):
                mod_commands += "/warn [ID/@username] [причина]\n/unwarn [ID/@username]\n"
            if has_chat_permission(chat.id, user.id, "btn_ban"):
                mod_commands += "/ban [ID/@username] [причина]\n"
            if has_chat_permission(chat.id, user.id, "btn_mute"):
                mod_commands += "/mute [ID/@username] [время] [причина]\n/unmute [ID/@username]\n"

            if mod_commands:
                text += "\nМодерация чата:\n" + mod_commands

            if is_chat_owner(chat.id, user.id) or has_chat_permission(chat.id, user.id, "btn_chat_admin"):
                text += "\n/setadm [ID/@username] [0-5] - Выдать ранг в чате\n"
                text += "/admins - Список админов чата\n"

        if has_bot_permission(user.id, "btn_blacklist"):
            text += "\nЧС:\n/permban [ID] [причина]\n/unperm [ID]\n"

        if has_astats_permission(user.id):
            text += "\n/astats - Статистика жалоб\n"

        if has_hstats_permission(user.id):
            text += "\n/hstats - Статистика вопросов\n"

        if user.id == FOUNDER_ID:
            text += "\n/onlyowner - Режим «только основатель»\n"
            text += "/botadmins - Админы бота\n"

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]])
        )

    # Агенты (для пользователей)
    elif data == "agents_list":
        agents = db.get_all_agents()
        text = "🔰 Агенты поддержки\n━━━━━━━━━━━━━━━━\n\n"
        if not agents:
            text += "Нет доступных агентов"
        else:
            for agent in agents:
                text += f"• @{agent['username']} - {db.get_agent_level_name(agent['user_id'])}\n"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]]))

# ==================== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ====================
async def setsuperadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if user.id != FOUNDER_ID:
        await update.message.reply_text("⛔ Только основатель")
        return
    if not context.args:
        await update.message.reply_text("/setsuperadmin [ID]")
        return
    try:
        db.add_super_admin(int(context.args[0]))
        await update.message.reply_text("✅ Супер-админ назначен")
    except ValueError:
        await update.message.reply_text("❌ Введите ID")

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not (has_bot_permission(user.id, "btn_agents_list") or db.get_agent_level(user.id) > 0):
        await update.message.reply_text("⛔ Нет доступа")
        return
    agents = db.get_all_agents()
    text = "🔰 Агенты поддержки\n━━━━━━━━━━━━━━━━\n\n"
    if not agents:
        text += "Нет агентов"
    else:
        for agent in agents:
            text += f"• {agent['first_name']} (@{agent['username']})\n  Уровень: {db.get_agent_level_name(agent['user_id'])}\n\n"
    await update.message.reply_text(text)

async def giverep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_bot_permission(user.id, "btn_give_rep"):
        await update.message.reply_text("⛔ Нет доступа")
        return
    if len(context.args) < 2:
        await update.message.reply_text("/giverep [ID клана] [количество]")
        return
    try:
        clan_id = int(context.args[0])
        rating = int(context.args[1])
        clan = db.get_clan(clan_id)
        if clan:
            db.add_clan_rating(clan_id, rating)
            await update.message.reply_text(f"✅ Клану {clan['name']} +{rating}")
    except ValueError:
        await update.message.reply_text("❌ Введите числа")

async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    if not has_bot_permission(user.id, "btn_blacklist"):
        await update.message.reply_text("⛔ Нет доступа")
        return
    blacklist = db.get_blacklist()
    text = "🚫 Черный список\n━━━━━━━━━━━━━━━━\n\n"
    if not blacklist:
        text += "Пуст"
    else:
        for u in blacklist:
            text += f"• {u['first_name']} (@{u['username']})\n  ID: {u['user_id']}\n  Причина: {u['reason']}\n\n"
    await update.message.reply_text(text)

# ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ONLY_OWNER_MODE
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text

    db.update_user_activity(user.id)

    if db.is_blacklisted(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return

    if ONLY_OWNER_MODE and user.id != FOUNDER_ID:
        return

    # 🆕 АНТИСПАМ ПРОВЕРКА
    if await check_antispam(update, context):
        return

    # 🆕 Изменение лимита антиспама
    if context.user_data.get('changing_antispam_limit'):
        context.user_data['changing_antispam_limit'] = False
        try:
            limit = int(text)
            if limit < 1 or limit > 50:
                await update.message.reply_text("❌ Введите число от 1 до 50!")
                return
            db.save_chat_settings(chat.id, antispam_enabled=1, antispam_limit=limit)
            await update.message.reply_text(
                f"✅ Антиспам настроен! Лимит: <b>{limit} сообщений/секунду</b>",
                parse_mode='HTML'
            )
        except ValueError:
            await update.message.reply_text("❌ Введите число!")
        return

    # 🆕 Изменение текста приветствия
    if context.user_data.get('changing_welcome_text'):
        context.user_data['changing_welcome_text'] = False
        welcome_text = text.strip()
        if len(welcome_text) > 500:
            await update.message.reply_text("❌ Слишком длинное сообщение! Максимум 500 символов.")
            return
        db.save_chat_settings(chat.id, welcome_enabled=1, welcome_text=welcome_text)
        await update.message.reply_text(
            f"✅ Приветствие настроено!\n\nТекст:\n<code>{welcome_text}</code>",
            parse_mode='HTML'
        )
        return

    # Ответ на жалобу
    if context.user_data.get('replying_report'):
        data = context.user_data['replying_report']
        report_id = data['report_id']
        reporter_id = data['reporter_id']
        context.user_data['replying_report'] = None
        try:
            await context.bot.send_message(reporter_id, f"📩 Ответ администрации на вашу жалобу:\n\n{text}")
            db.set_report_answered_by(report_id, user.id)
            await update.message.reply_text("✅ Ответ отправлен пользователю")
        except Exception as e:
            await update.message.reply_text(f"❌ Не удалось отправить ответ: {e}")
        return

    # Выдача награды
    if context.user_data.get('awarding_user'):
        target_id = context.user_data['awarding_user']
        context.user_data['awarding_user'] = None
        db.add_award(target_id, user.id, text)
        await update.message.reply_text(f"🏅 Награда выдана пользователю {target_id}:\n{text}")
        return

    # Ответ на тикет
    if context.user_data.get('answering_ticket'):
        ticket_id = context.user_data['answering_ticket']
        context.user_data['answering_ticket'] = None
        ticket = db.get_ticket(ticket_id)
        if ticket:
            db.close_ticket(ticket_id, text)
            try:
                await context.bot.send_message(ticket['user_id'], f"✅ Ответ на ваш вопрос #{ticket_id}:\n\n{text}")
            except:
                pass
            await update.message.reply_text(f"✅ Ответ отправлен. Тикет #{ticket_id} закрыт.")
        return

    # Создание клана
    if context.user_data.get('creating_clan'):
        context.user_data['creating_clan'] = False
        try:
            clan_id = db.create_clan(text, user.id)
            await update.message.reply_text(f"✅ Клан '{text}' создан! ID: {clan_id}")
        except sqlite3.IntegrityError:
            await update.message.reply_text("❌ Клан с таким названием уже существует")
        return

    # Отправка сообщения в клан
    if context.user_data.get('sending_clan_message'):
        context.user_data['sending_clan_message'] = False
        clan = db.get_user_clan(user.id)
        if clan:
            db.add_clan_message(clan['clan_id'], user.id, text)
            await update.message.reply_text("✅ Сообщение отправлено")
        else:
            await update.message.reply_text("❌ Вы не состоите в клане")
        return

    # Изменение названия ранга чата
    if context.user_data.get('editing_chat_rank') is not None:
        rank_level = context.user_data['editing_chat_rank']
        context.user_data['editing_chat_rank'] = None
        if chat and is_chat_owner(chat.id, user.id):
            db.set_rank_name(chat.id, rank_level, text)
            await update.message.reply_text(f"✅ Название ранга {rank_level} изменено на: {text}")
        else:
            await update.message.reply_text("⛔ У вас нет прав")
        return

    # Изменение названия ранга бота
    if context.user_data.get('editing_bot_rank') is not None:
        rank_level = context.user_data['editing_bot_rank']
        context.user_data['editing_bot_rank'] = None
        db.set_bot_rank_name(rank_level, text)
        await update.message.reply_text(f"✅ Название ранга {rank_level} изменено на: {text}")
        return

    # Изменение названия уровня агента
    if context.user_data.get('editing_agent_level') is not None:
        level = context.user_data['editing_agent_level']
        context.user_data['editing_agent_level'] = None
        db.set_agent_level_name(level, text)
        await update.message.reply_text(f"✅ Название уровня {level} изменено на: {text}")
        return

    # Добавление/удаление админов
    if context.user_data.get('adding_admin'):
        context.user_data['adding_admin'] = False
        try:
            db.add_bot_admin(int(text))
            await update.message.reply_text(f"✅ Пользователь {text} назначен админом бота")
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
        return

    if context.user_data.get('removing_admin'):
        context.user_data['removing_admin'] = False
        try:
            db.remove_bot_admin(int(text))
            await update.message.reply_text(f"✅ Админ {text} удалён")
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
        return

    # Изменение ранга админа
    if context.user_data.get('changing_admin_rank'):
        context.user_data['changing_admin_rank'] = False
        try:
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Введите ID и ранг через пробел")
                return
            admin_id = int(parts[0])
            rank = int(parts[1])
            if rank < 0 or rank > 10:
                await update.message.reply_text("❌ Ранг должен быть от 0 до 10")
                return
            db.set_bot_rank(admin_id, rank)
            await update.message.reply_text(f"✅ Ранг пользователя {admin_id} изменён на: {db.get_bot_rank_name(admin_id)}")
        except ValueError:
            await update.message.reply_text("❌ Введите числовые значения")
        return

    # Супер-админы
    if context.user_data.get('adding_super_admin'):
        context.user_data['adding_super_admin'] = False
        try:
            db.add_super_admin(int(text))
            await update.message.reply_text(f"✅ Супер-админ {text} назначен")
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
        return

    if context.user_data.get('removing_super_admin'):
        context.user_data['removing_super_admin'] = False
        try:
            db.remove_super_admin(int(text))
            await update.message.reply_text(f"✅ Супер-админ {text} удалён")
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
        return

    # Агенты
    if context.user_data.get('adding_agent'):
        context.user_data['adding_agent'] = False
        try:
            db.set_agent_level(int(text), AGENT_LEVEL_1)
            await update.message.reply_text(f"✅ Пользователь {text} назначен агентом поддержки")
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
        return

    if context.user_data.get('removing_agent'):
        context.user_data['removing_agent'] = False
        try:
            db.set_agent_level(int(text), 0)
            await update.message.reply_text(f"✅ Агент {text} удалён")
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID")
        return

    if context.user_data.get('changing_agent_level'):
        context.user_data['changing_agent_level'] = False
        try:
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Введите ID и уровень через пробел")
                return
            agent_id = int(parts[0])
            level = int(parts[1])
            if level < 0 or level > 3:
                await update.message.reply_text("❌ Уровень должен быть от 0 до 3")
                return
            db.set_agent_level(agent_id, level)
            await update.message.reply_text(f"✅ Уровень агента {agent_id} изменён на: {db.get_agent_level_name(agent_id)}")
        except ValueError:
            await update.message.reply_text("❌ Введите числовые значения")
        return

    # Вопрос в поддержку
    if context.user_data.get('question_state') == 'waiting_question':
        context.user_data['question_state'] = None
        ticket_id = db.add_ticket(user.id, user.username or f"id{user.id}", text)

        agents = db.get_all_agents()
        if agents:
            for agent in agents:
                try:
                    keyboard = [[
                        InlineKeyboardButton("✅ Принять", callback_data=f"accept_ticket_{ticket_id}"),
                        InlineKeyboardButton("❌ Закрыть", callback_data=f"close_ticket_{ticket_id}")
                    ]]
                    await context.bot.send_message(
                        agent['user_id'],
                        f"❓ Новый вопрос #{ticket_id}\n👤 От: {user.username or 'Нет'} (ID: {user.id})\n❓ Вопрос: {text}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить тикет агенту {agent['user_id']}: {e}")
        else:
            admins = db.get_all_bot_admins()
            for admin in admins:
                try:
                    keyboard = [[
                        InlineKeyboardButton("✅ Принять", callback_data=f"accept_ticket_{ticket_id}"),
                        InlineKeyboardButton("❌ Закрыть", callback_data=f"close_ticket_{ticket_id}")
                    ]]
                    await context.bot.send_message(
                        admin['user_id'],
                        f"❓ Новый вопрос #{ticket_id} (от пользователя)\n👤 От: {user.username or 'Нет'} (ID: {user.id})\n❓ Вопрос: {text}",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить вопрос админу {admin['user_id']}: {e}")

        await update.message.reply_text("✅ Ваш вопрос отправлен агентам поддержки")
        return

    # Война: шаг 1
    if context.user_data.get('war_state') == 'waiting_target':
        try:
            target_clan_id = int(text)
            target_clan = db.get_clan(target_clan_id)
            if not target_clan:
                await update.message.reply_text("❌ Клан не найден")
                return
            context.user_data['war_target'] = target_clan_id
            context.user_data['war_state'] = 'waiting_rating'
            await update.message.reply_text("Введите сумму рейтинга на кону:")
        except ValueError:
            await update.message.reply_text("❌ Введите числовой ID клана")
        return

    # Война: шаг 2
    elif context.user_data.get('war_state') == 'waiting_rating':
        try:
            rating = int(text)
            target_clan_id = context.user_data.get('war_target')
            target_clan = db.get_clan(target_clan_id)
            context.user_data['war_rating'] = rating
            context.user_data['war_state'] = None
            keyboard = [[
                InlineKeyboardButton("✅ Да", callback_data="war_confirm"),
                InlineKeyboardButton("❌ Нет", callback_data="war_cancel")
            ]]
            await update.message.reply_text(
                f"Точно начать войну против {target_clan['name']} на {rating} рейтинга?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError:
            await update.message.reply_text("❌ Введите числовое значение рейтинга")
        return


# ==================== ПРИВЕТСТВИЕ НОВЫХ УЧАСТНИКОВ ====================
async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветствие новым участникам"""
    chat_id = update.effective_chat.id
    
    settings = db.get_chat_settings(chat_id)
    if not settings or not settings.get("welcome_enabled"):
        return
    
    for member in update.message.new_chat_members:
        text = settings["welcome_text"]
        text = text.replace("{name}", member.full_name)
        text = text.replace("{chat}", update.effective_chat.title)
        
        await update.message.reply_text(text, parse_mode='HTML')


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("clan_top", clan_top_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("clan", clan_command))

    # Модерация
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("unwarn", unwarn_command))

    # ЧС
    application.add_handler(CommandHandler("permban", permban_command))
    application.add_handler(CommandHandler("unperm", unperm_command))

    # Новые команды
    application.add_handler(CommandHandler("setadm", setadm_command))
    application.add_handler(CommandHandler("admins", admins_command))
    application.add_handler(CommandHandler("botadmins", botadmins_command))
    application.add_handler(CommandHandler("astats", astats_command))
    application.add_handler(CommandHandler("hstats", hstats_command))
    application.add_handler(CommandHandler("onlyowner", onlyowner_command))

    # Доп. админ-команды
    application.add_handler(CommandHandler("setrank", setrank_command))
    application.add_handler(CommandHandler("setagentlevel", setagentlevel_command))
    application.add_handler(CommandHandler("setsuperadmin", setsuperadmin_command))
    application.add_handler(CommandHandler("agents", agents_command))
    application.add_handler(CommandHandler("giverep", giverep_command))
    application.add_handler(CommandHandler("blacklist", blacklist_command))

    # Callback и сообщения
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # 🆕 Обработчик новых участников
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        welcome_new_members
    ))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот Fluxy запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()