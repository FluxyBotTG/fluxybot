import logging
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8980577910:AAGJFO588dLcq86neXNAcPUwIW9_xG7UHc8"
FOUNDER_ID = 8669060906

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

message_history = {}

def calculate_war_win_chance(clan1_rating, clan2_rating):
    diff = clan1_rating - clan2_rating
    bonus = (diff // 1000) * 5
    chance = 50 + bonus
    return max(10, min(90, chance))

BOT_BUTTON_PERMISSIONS = {
    "btn_admin_panel": "⭐️ Админ панель",
    "btn_admins_list": "👥 Админы бота",
    "btn_agents_list": "🔰 Агенты",
    "btn_blacklist": "🚫 ЧС",
    "btn_give_rep": "⭐️ Репутация",
    "btn_commands": "📋 Команды",
    "btn_chats": "🗂 Чаты",
    "btn_ranks": "📊 Ранги",
    "btn_rank_perms": "⚙️ Права рангов",
    "btn_super_admins": "👑 Супер-админы",
}

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
                reason TEXT,
                warn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
                reason TEXT,
                ban_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS mutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                user_id INTEGER,
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
            CREATE TABLE IF NOT EXISTS clan_applications (
                user_id INTEGER,
                clan_id INTEGER,
                PRIMARY KEY (user_id, clan_id)
            );
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter_id INTEGER,
                target_id INTEGER,
                reason TEXT,
                chat_id INTEGER,
                answered_by INTEGER,
                report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT,
                status TEXT DEFAULT 'open',
                agent_id INTEGER,
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
                welcome_text TEXT DEFAULT 'Привет, {name}!'
            );
            CREATE TABLE IF NOT EXISTS clan_daily_bonus (
                clan_id INTEGER,
                bonus_date TEXT,
                PRIMARY KEY (clan_id, bonus_date)
            );
        ''')
        self.init_default_data()
        self.conn.commit()

    def init_default_data(self):
        for lvl, name in {0:"Пользователь",1:"Ранг 1",2:"Ранг 2",3:"Ранг 3",4:"Ранг 4",5:"Ранг 5",6:"Ранг 6",7:"Ранг 7",8:"Админ бота",9:"Высший админ",10:"Основатель бота"}.items():
            self.cursor.execute("INSERT OR IGNORE INTO bot_rank_names VALUES (?, ?)", (lvl, name))
        for rank, perms in {1:["btn_commands"],2:["btn_commands","btn_admins_list"],3:["btn_commands","btn_admins_list","btn_blacklist"],4:["btn_commands","btn_admins_list","btn_blacklist","btn_give_rep"],5:["btn_commands","btn_admins_list","btn_blacklist","btn_give_rep","btn_rank_perms"],6:["btn_commands","btn_admins_list","btn_blacklist","btn_give_rep","btn_rank_perms","btn_super_admins"],7:["btn_commands","btn_admins_list","btn_blacklist","btn_give_rep","btn_rank_perms","btn_super_admins"],8:["btn_admin_panel","btn_admins_list","btn_blacklist","btn_give_rep","btn_commands","btn_rank_perms","btn_super_admins"],9:["btn_admin_panel","btn_admins_list","btn_blacklist","btn_give_rep","btn_commands","btn_rank_perms","btn_super_admins"]}.items():
            for p in perms:
                self.cursor.execute("INSERT OR IGNORE INTO bot_rank_permissions VALUES (?, ?)", (rank, p))
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
            return 10
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

    def get_bot_rank_permissions(self, rank_level):
        self.cursor.execute("SELECT permission FROM bot_rank_permissions WHERE rank_level = ?", (rank_level,))
        return [row[0] for row in self.cursor.fetchall()]

    def add_bot_rank_permission(self, rank_level, permission):
        self.cursor.execute("INSERT OR IGNORE INTO bot_rank_permissions VALUES (?, ?)", (rank_level, permission))
        self.conn.commit()

    def remove_bot_rank_permission(self, rank_level, permission):
        self.cursor.execute("DELETE FROM bot_rank_permissions WHERE rank_level = ? AND permission = ?", (rank_level, permission))
        self.conn.commit()

    def has_bot_permission(self, user_id, permission):
        rank = self.get_bot_rank(user_id)
        if rank >= 10:
            return True
        return permission in self.get_bot_rank_permissions(rank)

    def get_agent_level(self, user_id):
        user = self.get_user(user_id)
        return user['agent_level'] if user else 0

    def set_agent_level(self, user_id, level):
        self.cursor.execute("UPDATE users SET agent_level = ? WHERE user_id = ?", (level, user_id))
        self.conn.commit()

    def get_agent_level_name(self, user_id):
        names = {0:"Не агент",1:"Агент поддержки",2:"Главный агент",3:"ГС агентов"}
        return names.get(self.get_agent_level(user_id), "Не агент")

    def get_all_agents(self):
        self.cursor.execute("SELECT user_id, username, first_name FROM users WHERE agent_level > 0")
        return [{'user_id': r[0], 'username': r[1] or 'Нет', 'first_name': r[2] or 'Нет'} for r in self.cursor.fetchall()]

    def get_all_bot_admins(self):
        admins = [{'user_id': FOUNDER_ID, 'username': 'Основатель', 'first_name': 'Основатель'}]
        self.cursor.execute("SELECT user_id, username, first_name FROM users WHERE bot_rank >= 1 AND user_id != ?", (FOUNDER_ID,))
        for row in self.cursor.fetchall():
            admins.append({'user_id': row[0], 'username': row[1] or 'Нет', 'first_name': row[2] or 'Нет'})
        return admins

    def is_super_admin(self, user_id):
        return user_id == FOUNDER_ID or self.get_bot_rank(user_id) >= 9

    def add_super_admin(self, user_id):
        self.set_bot_rank(user_id, 9)

    def remove_super_admin(self, user_id):
        self.set_bot_rank(user_id, 0)

    def get_chat_member_rank(self, chat_id, user_id):
        self.cursor.execute("SELECT chat_rank FROM chat_members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def set_chat_member_rank(self, chat_id, user_id, rank):
        self.cursor.execute("INSERT OR REPLACE INTO chat_members VALUES (?, ?, ?)", (chat_id, user_id, rank))
        self.conn.commit()

    def has_chat_permission(self, chat_id, user_id, permission):
        rank = self.get_chat_member_rank(chat_id, user_id)
        if rank >= 10:
            return True
        perms = {1: ["btn_chat_admin"], 2: ["btn_chat_admin", "btn_kick"], 3: ["btn_chat_admin", "btn_kick", "btn_warn"], 4: ["btn_chat_admin", "btn_kick", "btn_warn", "btn_mute"], 6: ["btn_chat_admin", "btn_kick", "btn_warn", "btn_mute", "btn_ban"]}
        return permission in perms.get(rank, [])

    def get_all_chat_admins(self, chat_id):
        self.cursor.execute("SELECT cm.user_id, cm.chat_rank, u.username, u.first_name FROM chat_members cm LEFT JOIN users u ON cm.user_id = u.user_id WHERE cm.chat_id = ? AND cm.chat_rank >= 1", (chat_id,))
        return [{'user_id': r[0], 'chat_rank': r[1], 'username': r[2] or 'Нет', 'first_name': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    def add_warning(self, chat_id, user_id, reason):
        self.cursor.execute("INSERT INTO warnings (chat_id, user_id, reason) VALUES (?, ?, ?)", (chat_id, user_id, reason))
        self.conn.commit()

    def remove_warning(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        self.conn.commit()

    def add_ban(self, chat_id, user_id, reason):
        self.cursor.execute("INSERT INTO bans (chat_id, user_id, reason) VALUES (?, ?, ?)", (chat_id, user_id, reason))
        self.conn.commit()

    def remove_ban(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM bans WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        self.conn.commit()

    def add_mute(self, chat_id, user_id, reason, unmute_date):
        self.cursor.execute("INSERT INTO mutes (chat_id, user_id, reason, unmute_date) VALUES (?, ?, ?, ?)", (chat_id, user_id, reason, unmute_date))
        self.conn.commit()

    def remove_mute(self, chat_id, user_id):
        self.cursor.execute("DELETE FROM mutes WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        self.conn.commit()

    def create_clan(self, name, leader_id):
        self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (leader_id,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (leader_id, 'Неизвестный', 'Пользователь'))
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
        self.cursor.execute("SELECT cm.user_id, cm.role, u.username, u.first_name FROM clan_members cm LEFT JOIN users u ON cm.user_id = u.user_id WHERE cm.clan_id = ?", (clan_id,))
        return [{'user_id': r[0], 'role': r[1], 'username': r[2] or 'Нет', 'first_name': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    def get_clan_members_count(self, clan_id):
        self.cursor.execute("SELECT COUNT(*) FROM clan_members WHERE clan_id = ?", (clan_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def set_clan_join_enabled(self, clan_id, mode):
        self.cursor.execute("UPDATE clans SET join_enabled = ? WHERE clan_id = ?", (mode, clan_id))
        self.conn.commit()

    def get_top_clans(self, limit=10):
        self.cursor.execute("SELECT clan_id, name, rating FROM clans ORDER BY rating DESC LIMIT ?", (limit,))
        return [{'clan_id': r[0], 'name': r[1], 'rating': r[2]} for r in self.cursor.fetchall()]

    def add_clan_rating(self, clan_id, rating):
        self.cursor.execute("UPDATE clans SET rating = rating + ? WHERE clan_id = ?", (rating, clan_id))
        self.conn.commit()

    def get_chat_settings(self, chat_id):
        self.cursor.execute("SELECT * FROM chat_settings WHERE chat_id = ?", (chat_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def save_chat_settings(self, chat_id, **kwargs):
        self.cursor.execute("SELECT chat_id FROM chat_settings WHERE chat_id = ?", (chat_id,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO chat_settings (chat_id) VALUES (?)", (chat_id,))
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE chat_settings SET {key} = ? WHERE chat_id = ?", (value, chat_id))
        self.conn.commit()

    def add_to_blacklist(self, user_id, reason):
        self.cursor.execute("INSERT OR REPLACE INTO black_list VALUES (?, ?)", (user_id, reason))
        self.conn.commit()

    def remove_from_blacklist(self, user_id):
        self.cursor.execute("DELETE FROM black_list WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def is_blacklisted(self, user_id):
        self.cursor.execute("SELECT 1 FROM black_list WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone() is not None

    def get_blacklist(self):
        self.cursor.execute("SELECT bl.user_id, bl.reason, u.username, u.first_name FROM black_list bl LEFT JOIN users u ON bl.user_id = u.user_id")
        return [{'user_id': r[0], 'reason': r[1], 'username': r[2] or 'Нет', 'first_name': r[3] or 'Нет'} for r in self.cursor.fetchall()]

    def add_award(self, user_id, awarded_by, award_text):
        self.cursor.execute("INSERT INTO awards (user_id, awarded_by, award_text) VALUES (?, ?, ?)", (user_id, awarded_by, award_text))
        self.conn.commit()

    def get_user_awards(self, user_id):
        self.cursor.execute("SELECT a.award_text, a.award_date, u.username FROM awards a LEFT JOIN users u ON a.awarded_by = u.user_id WHERE a.user_id = ?", (user_id,))
        return [{'award_text': r[0], 'award_date': r[1], 'awarded_by_username': r[2] or 'Нет'} for r in self.cursor.fetchall()]

    def add_ticket(self, user_id, question):
        self.cursor.execute("INSERT INTO support_tickets (user_id, question) VALUES (?, ?)", (user_id, question))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_ticket(self, ticket_id):
        self.cursor.execute("SELECT * FROM support_tickets WHERE id = ?", (ticket_id,))
        result = self.cursor.fetchone()
        if result:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, result))
        return None

    def close_ticket(self, ticket_id, answer):
        self.cursor.execute("UPDATE support_tickets SET status='closed', answer=?, closed_date=CURRENT_TIMESTAMP WHERE id=?", (answer, ticket_id))
        self.conn.commit()

    def add_report(self, reporter_id, target_id, reason, chat_id):
        self.cursor.execute("INSERT INTO reports (reporter_id, target_id, reason, chat_id) VALUES (?, ?, ?, ?)", (reporter_id, target_id, reason, chat_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def set_report_answered_by(self, report_id, admin_id):
        self.cursor.execute("UPDATE reports SET answered_by = ? WHERE id = ?", (admin_id, report_id))
        self.conn.commit()

    def get_admin_reply_count(self, admin_id):
        self.cursor.execute("SELECT COUNT(*) FROM reports WHERE answered_by = ?", (admin_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def can_get_daily_bonus(self, clan_id):
        today = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute("SELECT 1 FROM clan_daily_bonus WHERE clan_id = ? AND bonus_date = ?", (clan_id, today))
        return self.cursor.fetchone() is None

    def give_daily_bonus(self, clan_id):
        today = datetime.now().strftime('%Y-%m-%d')
        self.cursor.execute("INSERT INTO clan_daily_bonus VALUES (?, ?)", (clan_id, today))
        self.conn.commit()

    def get_bot_stats(self):
        users_count = self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        chats_count = self.cursor.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        clans_count = self.cursor.execute("SELECT COUNT(*) FROM clans").fetchone()[0]
        today = datetime.now().strftime('%Y-%m-%d')
        active_today = self.cursor.execute("SELECT COUNT(*) FROM users WHERE last_activity LIKE ?", (f"{today}%",)).fetchone()[0]
        return {'users': users_count, 'chats': chats_count, 'clans': clans_count, 'active_today': active_today}

    def add_chat_member(self, chat_id, user_id, chat_rank=0):
        self.cursor.execute("INSERT OR IGNORE INTO chat_members VALUES (?, ?, ?)", (chat_id, user_id, chat_rank))
        self.conn.commit()

    def add_chat(self, chat_id, chat_type, chat_title):
        self.cursor.execute("INSERT OR REPLACE INTO chats VALUES (?, ?, ?)", (chat_id, chat_type, chat_title))
        self.conn.commit()

    def get_all_chats(self):
        self.cursor.execute("SELECT chat_id, chat_type, chat_title FROM chats")
        return [{'chat_id': r[0], 'chat_type': r[1], 'chat_title': r[2]} for r in self.cursor.fetchall()]

    def get_all_super_admins(self):
        self.cursor.execute("SELECT user_id, username, first_name FROM users WHERE bot_rank >= 9")
        return [{'user_id': r[0], 'username': r[1] or 'Нет', 'first_name': r[2] or 'Нет'} for r in self.cursor.fetchall()]

    def add_bot_admin(self, user_id):
        self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)", (user_id, 'Неизвестный', 'Пользователь'))
        self.set_bot_rank(user_id, 1)
        self.conn.commit()

    def remove_bot_admin(self, user_id):
        self.set_bot_rank(user_id, 0)
        self.conn.commit()

db = Database()

def has_bot_permission(user_id: int, permission: str) -> bool:
    return db.has_bot_permission(user_id, permission)

def is_super_admin(user_id: int) -> bool:
    return db.is_super_admin(user_id)

def is_chat_owner(chat_id: int, user_id: int) -> bool:
    return db.get_chat_member_rank(chat_id, user_id) >= 10

def has_chat_permission(chat_id: int, user_id: int, permission: str) -> bool:
    return db.has_chat_permission(chat_id, user_id, permission)

def is_blacklisted_check(user_id: int) -> bool:
    return db.is_blacklisted(user_id)

def format_clan_info(clan: Dict) -> str:
    if not clan:
        return "Вы не состоите в клане"
    return f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan['clan_id']}
🛡 Название: {clan['name']}
🏆 Рейтинг: {clan['rating']}

━━━━━━━━━━━━━━━━"""

async def get_target_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    if context.args:
        arg = context.args[0]
        if arg.isdigit():
            return int(arg)
        username = arg.replace('@', '')
        user = db.get_user_by_username(username)
        if user:
            return user['user_id']
        chat = update.effective_chat
        if chat and chat.type != "private":
            try:
                member = await context.bot.get_chat_member(chat.id, username)
                if member:
                    return member.user.id
            except:
                pass
    return None

async def check_antispam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    settings = db.get_chat_settings(chat_id)
    if not settings or not settings.get("antispam_enabled"):
        return False
    now = time.time()
    limit = settings.get("antispam_limit", 5)
    key = (chat_id, user_id)
    timestamps = message_history.get(key, [])
    timestamps = [t for t in timestamps if now - t < 1]
    if len(timestamps) >= limit:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            await update.effective_message.reply_text(f"🚫 {update.effective_user.full_name} исключён за спам!")
            message_history[key] = []
        except:
            pass
        return True
    timestamps.append(now)
    message_history[key] = timestamps
    return False
    
    # ==================== КОМАНДЫ ====================
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    target_id = await get_target_user_id(update, context)
    if target_id:
        await update.message.reply_text(f"🆔 ID: {target_id}")
    else:
        await update.message.reply_text("/id [ID/@username] или ответьте на сообщение")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    start_time = time.time()
    msg = await update.message.reply_text("📡 Измеряю...")
    ping = round((time.time() - start_time) * 1000)
    await msg.edit_text(f"🏓 Пинг: {ping} мс")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/stats [ID/@username]")
        return
    target_user_data = db.get_user(target_id)
    if not target_user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    clan = db.get_user_clan(target_id)
    text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

👤 Имя: {target_user_data.get('first_name', 'Нет')}
🔗 Username: @{target_user_data.get('username', 'Нет')}
🆔 ID: {target_id}

🎖️ Ранг: {db.get_bot_rank_name(target_id)}
🛡️ Клан: {clan['name'] if clan else 'Нет'}

━━━━━━━━━━━━━━━━"""
    if chat and chat.type != "private" and has_chat_permission(chat.id, user.id, "btn_warn"):
        text += "\n⚠️ Наказания:\n"
        warnings = db.cursor.execute("SELECT reason FROM warnings WHERE chat_id=? AND user_id=?", (chat.id, target_id)).fetchall()
        bans = db.cursor.execute("SELECT reason FROM bans WHERE chat_id=? AND user_id=?", (chat.id, target_id)).fetchall()
        if warnings:
            for w in warnings:
                text += f"  • {w[0]}\n"
        if bans:
            for b in bans:
                text += f"  • {b[0]}\n"
        if not warnings and not bans:
            text += "Нет наказаний\n"
    keyboard = [
        [InlineKeyboardButton("🏅 Выдать награду", callback_data=f"give_award_{target_id}")],
        [InlineKeyboardButton("🏆 Награды", callback_data=f"show_awards_{target_id}")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def permban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_bot_permission(user.id, "btn_blacklist"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/permban [ID/@username] [причина]")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    db.add_to_blacklist(target_id, reason)
    await update.message.reply_text(f"🚫 {target_id} в ЧС\nПричина: {reason}")

async def unperm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_bot_permission(user.id, "btn_blacklist"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/unperm [ID/@username]")
        return
    db.remove_from_blacklist(target_id)
    await update.message.reply_text(f"✅ {target_id} удален из ЧС")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_chat_permission(chat.id, user.id, "btn_kick"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/kick [ID/@username]")
        return
    try:
        await context.bot.ban_chat_member(chat.id, target_id)
        await context.bot.unban_chat_member(chat.id, target_id)
        await update.message.reply_text(f"✅ {target_id} кикнут")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_chat_permission(chat.id, user.id, "btn_warn"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/warn [ID/@username] [причина]")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    db.add_warning(chat.id, target_id, reason)
    await update.message.reply_text(f"⚠️ {target_id} предупреждён\nПричина: {reason}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_chat_permission(chat.id, user.id, "btn_ban"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/ban [ID/@username] [причина]")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    try:
        await context.bot.ban_chat_member(chat.id, target_id)
        db.add_ban(chat.id, target_id, reason)
        await update.message.reply_text(f"🔨 {target_id} забанен\nПричина: {reason}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_chat_permission(chat.id, user.id, "btn_mute"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/mute [ID/@username] [минуты]")
        return
    minutes = 60
    if context.args and context.args[-1].isdigit():
        minutes = int(context.args[-1])
    try:
        unmute_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_id, permissions=ChatPermissions(can_send_messages=False), until_date=unmute_time)
        db.add_mute(chat.id, target_id, "Мут", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        await update.message.reply_text(f"🔇 {target_id} замучен на {minutes} мин")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/unmute [ID/@username]")
        return
    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_id, permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        db.remove_mute(chat.id, target_id)
        await update.message.reply_text(f"🔊 {target_id} размучен")
    except:
        await update.message.reply_text("❌ Ошибка")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/unban [ID/@username]")
        return
    try:
        await context.bot.unban_chat_member(chat.id, target_id)
        db.remove_ban(chat.id, target_id)
        await update.message.reply_text(f"✅ {target_id} разбанен")
    except:
        await update.message.reply_text("❌ Ошибка")

async def unwarn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/unwarn [ID/@username]")
        return
    db.remove_warning(chat.id, target_id)
    await update.message.reply_text("✅ Предупреждение снято")

async def setadm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not (is_chat_owner(chat.id, user.id) or is_super_admin(user.id)):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    if update.message.reply_to_message:
        if len(context.args) >= 1 and context.args[0].isdigit():
            rank = int(context.args[0])
        else:
            await update.message.reply_text("❌ /setadm 5")
            return
    else:
        if len(context.args) >= 2 and context.args[1].isdigit():
            rank = int(context.args[1])
        else:
            await update.message.reply_text("/setadm [ID/@username] [ранг 0-10]")
            return
    db.set_chat_member_rank(chat.id, target_id, rank)
    await update.message.reply_text(f"✅ {target_id} получил ранг {rank}")

async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    admins = db.get_all_chat_admins(chat.id)
    text = "👥 Админы чата\n━━━━━━━━━━━━━━━━\n\n"
    for admin in admins:
        text += f"• {admin['first_name']} (@{admin['username']})\n  Ранг: {admin['chat_rank']}\n\n"
    await update.message.reply_text(text)

async def astats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_bot_permission(user.id, "btn_commands"):
        await update.message.reply_text("⛔ Нет прав")
        return
    admins = db.get_all_bot_admins()
    text = "📊 Статистика жалоб\n━━━━━━━━━━━━━━━━\n\n"
    for admin in admins:
        count = db.get_admin_reply_count(admin['user_id'])
        text += f"• {admin['first_name']}: {count}\n"
    await update.message.reply_text(text)

async def message_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_bot_permission(user.id, "btn_commands"):
        await update.message.reply_text("⛔ Нет прав")
        return
    if not context.args:
        await update.message.reply_text("/message_bot [текст]")
        return
    text = ' '.join(context.args)
    users = db.cursor.execute("SELECT user_id FROM users").fetchall()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(u[0], f"📣 Рассылка:\n\n{text}")
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Отправлено: {sent}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    chat = update.effective_chat
    db.add_user(user.id, user.username, user.first_name)
    if chat:
        db.add_chat(chat.id, chat.type, chat.title or "ЛС")
        db.add_chat_member(chat.id, user.id)
    if chat and chat.type != "private":
        try:
            admins = await context.bot.get_chat_administrators(chat.id)
            for admin in admins:
                if admin.status == 'creator':
                    db.set_chat_member_rank(chat.id, admin.user.id, 10)
                    break
        except:
            pass
    text = f"""👋 Добро пожаловать в Fluxy!
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(user.id)}

━━━━━━━━━━━━━━━━"""
    keyboard = []
    if has_bot_permission(user.id, "btn_admin_panel"):
        keyboard.append([InlineKeyboardButton("⭐️ Админ панель бота", callback_data="admin_panel")])
    if chat and chat.type != "private":
        if has_chat_permission(chat.id, user.id, "btn_chat_admin"):
            keyboard.append([InlineKeyboardButton("👑 Админ панель чата", callback_data="chat_admin_panel")])
    keyboard.append([InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")])
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="help"), InlineKeyboardButton("📋 Команды", callback_data="commands")])
    keyboard.append([InlineKeyboardButton("➕ Добавить в чат", url="https://t.me/fluxy_cm_bot?startgroup=true")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    text = "❓ Помощь\n\n/start /help /ping /id /stats /profile /clan /clan_top /report /clan_bonus /message_bot"
    keyboard = [
        [InlineKeyboardButton("❗️ Жалоба", callback_data="help_report")],
        [InlineKeyboardButton("❓ Вопрос", callback_data="help_question")],
        [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответьте на сообщение: /report <причина>")
        return
    target = update.message.reply_to_message.from_user
    reason = ' '.join(context.args) if context.args else "Не указана"
    db.add_report(user.id, target.id, reason, update.effective_chat.id)
    await update.message.reply_text("✅ Жалоба отправлена")

async def clan_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    top_clans = db.get_top_clans()
    text = "🏆 Топ кланов\n━━━━━━━━━━━━━━━━\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, clan in enumerate(top_clans[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} {clan['name']} — {clan['rating']}\n"
    await update.message.reply_text(text)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    clan = db.get_user_clan(user.id)
    text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(user.id)}
🛡️ Клан: {clan['name'] if clan else 'Нет'}

━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text)

async def clan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    clan = db.get_user_clan(user.id)
    if not clan:
        keyboard = [
            [InlineKeyboardButton("➕ Создать клан", callback_data="create_clan")],
            [InlineKeyboardButton("🔍 Найти клан", callback_data="find_clan")],
            [InlineKeyboardButton("📋 Список кланов", callback_data="clan_list")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
        ]
        await update.message.reply_text("Вы не состоите в клане", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        keyboard = [
            [InlineKeyboardButton("👥 Участники", callback_data="clan_members")],
            [InlineKeyboardButton("⚔ Война", callback_data="clan_war")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
        ]
        await update.message.reply_text(format_clan_info(clan), reply_markup=InlineKeyboardMarkup(keyboard))

async def clan_bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    clan = db.get_user_clan(user.id)
    if not clan:
        await update.message.reply_text("❌ Вы не в клане")
        return
    if not db.can_get_daily_bonus(clan['clan_id']):
        await update.message.reply_text("❌ Бонус уже получен!")
        return
    count = db.get_clan_members_count(clan['clan_id'])
    db.give_daily_bonus(clan['clan_id'])
    db.add_clan_rating(clan['clan_id'], count)
    await update.message.reply_text(f"✅ Клан получил +{count} рейтинга!")

async def delclan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not is_super_admin(user.id):
        await update.message.reply_text("⛔ Только супер-админ")
        return
    if not context.args:
        await update.message.reply_text("/delclan [ID]")
        return
    try:
        clan_id = int(context.args[0])
        db.cursor.execute("DELETE FROM clans WHERE clan_id = ?", (clan_id,))
        db.cursor.execute("DELETE FROM clan_members WHERE clan_id = ?", (clan_id,))
        db.cursor.execute("UPDATE users SET clan_id = NULL WHERE clan_id = ?", (clan_id,))
        db.conn.commit()
        await update.message.reply_text("✅ Клан удалён!")
    except:
        await update.message.reply_text("❌ Введите ID")

async def setrank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
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
        db.set_bot_rank(target_id, rank)
        await update.message.reply_text(f"✅ Ранг: {rank}")
    except:
        await update.message.reply_text("❌ Введите числа")

async def setagentlevel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
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
        db.set_agent_level(target_id, level)
        await update.message.reply_text(f"✅ Уровень: {level}")
    except:
        await update.message.reply_text("❌ Введите числа")

async def setsuperadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
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
    except:
        await update.message.reply_text("❌ Введите ID")

async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_bot_permission(user.id, "btn_agents_list"):
        await update.message.reply_text("⛔ Нет доступа")
        return
    agents = db.get_all_agents()
    text = "🔰 Агенты поддержки\n━━━━━━━━━━━━━━━━\n\n"
    for agent in agents:
        text += f"• {agent['first_name']} (@{agent['username']})\n\n"
    await update.message.reply_text(text)

async def blacklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not has_bot_permission(user.id, "btn_blacklist"):
        await update.message.reply_text("⛔ Нет доступа")
        return
    blacklist = db.get_blacklist()
    text = "🚫 Черный список\n━━━━━━━━━━━━━━━━\n\n"
    for u in blacklist:
        text += f"• {u['first_name']} (@{u['username']})\n  ID: {u['user_id']}\n  Причина: {u['reason']}\n\n"
    await update.message.reply_text(text)

async def giverep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
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
        db.add_clan_rating(clan_id, rating)
        await update.message.reply_text(f"✅ +{rating} рейтинга")
    except:
        await update.message.reply_text("❌ Введите числа")
        
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    chat = query.message.chat if query.message else None
    data = query.data

    if db.is_blacklisted(user.id):
        await query.edit_message_text("❌ Вы в черном списке")
        return

    if data.startswith("give_award_"):
        target_id = int(data.split("_")[-1])
        context.user_data['awarding_user'] = target_id
        await query.edit_message_text("✏️ Введите текст награды:")
    elif data == "cancel_award":
        context.user_data['awarding_user'] = None
        await query.edit_message_text("❌ Отменено")
    elif data.startswith("show_awards_"):
        target_id = int(data.split("_")[-1])
        awards = db.get_user_awards(target_id)
        if not awards:
            await query.edit_message_text("🏅 Наград нет")
            return
        text = "🏅 Награды\n━━━━━━━━━━━━━━━━\n\n"
        for award in awards:
            text += f"🏅 {award['award_text']}\n  От: @{award['awarded_by_username']}\n  {award['award_date']}\n\n"
        await query.edit_message_text(text)

    elif data == "start_menu":
        text = f"""👋 Добро пожаловать в Fluxy!
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(user.id)}

━━━━━━━━━━━━━━━━"""
        keyboard = []
        if has_bot_permission(user.id, "btn_admin_panel"):
            keyboard.append([InlineKeyboardButton("⭐️ Админ панель бота", callback_data="admin_panel")])
        if chat and chat.type != "private":
            if has_chat_permission(chat.id, user.id, "btn_chat_admin"):
                keyboard.append([InlineKeyboardButton("👑 Админ панель чата", callback_data="chat_admin_panel")])
        keyboard.append([InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")])
        keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="help"), InlineKeyboardButton("📋 Команды", callback_data="commands")])
        keyboard.append([InlineKeyboardButton("➕ Добавить в чат", url="https://t.me/fluxy_cm_bot?startgroup=true")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_panel":
        if not has_bot_permission(user.id, "btn_admin_panel"):
            await query.edit_message_text("⛔ Нет доступа")
            return
        text = "⭐️ Админ панель бота\n━━━━━━━━━━━━━━━━"
        keyboard = []
        row = []
        if has_bot_permission(user.id, "btn_admins_list"):
            row.append(InlineKeyboardButton("👥 Админы", callback_data="bot_admins_list"))
        if has_bot_permission(user.id, "btn_agents_list"):
            row.append(InlineKeyboardButton("🔰 Агенты", callback_data="list_agents"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_blacklist"):
            row.append(InlineKeyboardButton("🚫 ЧС", callback_data="black_list"))
        if has_bot_permission(user.id, "btn_give_rep"):
            row.append(InlineKeyboardButton("⭐️ Репутация", callback_data="give_rep"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_commands"):
            row.append(InlineKeyboardButton("📣 Рассылка", callback_data="broadcast"))
        if has_bot_permission(user.id, "btn_commands"):
            row.append(InlineKeyboardButton("📊 Статистика", callback_data="bot_stats"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_rank_perms"):
            row.append(InlineKeyboardButton("⚙️ Права рангов", callback_data="bot_rank_permissions"))
        if has_bot_permission(user.id, "btn_super_admins"):
            row.append(InlineKeyboardButton("👑 Супер-админы", callback_data="super_admins_list"))
        row.append(InlineKeyboardButton("⬅️ Выход", callback_data="start_menu"))
        keyboard.append(row)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "broadcast":
        context.user_data['broadcasting'] = True
        await query.edit_message_text("📣 Отправьте текст рассылки:")

    elif data == "bot_stats":
        stats = db.get_bot_stats()
        text = f"""📊 Статистика
━━━━━━━━━━━━━━━━

👥 Пользователей: {stats['users']}
💬 Чатов: {stats['chats']}
🛡 Кланов: {stats['clans']}
⚡ За день: {stats['active_today']}"""
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]]))

    elif data == "bot_admins_list":
        admins = db.get_all_bot_admins()
        text = "👥 Админы бота\n━━━━━━━━━━━━━━━━\n\n"
        for admin in admins:
            text += f"• {admin['first_name']} (@{admin['username']})\n  ID: {admin['user_id']}\n\n"
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data="add_admin"), InlineKeyboardButton("➖ Удалить", callback_data="remove_admin")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_admin":
        context.user_data['adding_admin'] = True
        await query.edit_message_text("Введите ID:")
    elif data == "remove_admin":
        context.user_data['removing_admin'] = True
        await query.edit_message_text("Введите ID:")

    elif data == "list_agents":
        agents = db.get_all_agents()
        text = "🔰 Агенты\n━━━━━━━━━━━━━━━━\n\n"
        for agent in agents:
            text += f"• {agent['first_name']} (@{agent['username']})\n\n"
        keyboard = [
            [InlineKeyboardButton("➕ Назначить", callback_data="add_agent"), InlineKeyboardButton("➖ Удалить", callback_data="remove_agent")],
            [InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_agent":
        context.user_data['adding_agent'] = True
        await query.edit_message_text("Введите ID:")
    elif data == "remove_agent":
        context.user_data['removing_agent'] = True
        await query.edit_message_text("Введите ID:")

    elif data == "black_list":
        blacklist = db.get_blacklist()
        text = "🚫 Черный список\n━━━━━━━━━━━━━━━━\n\n"
        for u in blacklist:
            text += f"• {u['first_name']} (@{u['username']})\n  Причина: {u['reason']}\n\n"
        await query.edit_message_text(text)

    elif data == "give_rep":
        await query.edit_message_text("Используйте: /giverep [ID клана] [количество]")

    elif data == "bot_rank_permissions":
        if not has_bot_permission(user.id, "btn_rank_perms"): return
        text = "⚙️ Права рангов\n━━━━━━━━━━━━━━━━\n\nВыберите ранг (1-9):"
        keyboard = []
        for level in range(1, 10):
            keyboard.append([InlineKeyboardButton(f"Ранг {level}", callback_data=f"edit_bot_perms_{level}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("edit_bot_perms_"):
        rank_level = int(data.split("_")[-1])
        perms = db.get_bot_rank_permissions(rank_level)
        text = f"⚙️ Права ранга {rank_level}\n━━━━━━━━━━━━━━━━\n\n"
        keyboard = []
        for perm, desc in BOT_BUTTON_PERMISSIONS.items():
            if perm in perms:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="bot_rank_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("toggle_bot_perm_"):
        parts = data.split("_")
        rank_level = int(parts[3])
        permission = "_".join(parts[4:])
        perms = db.get_bot_rank_permissions(rank_level)
        if permission in perms:
            db.remove_bot_rank_permission(rank_level, permission)
        else:
            db.add_bot_rank_permission(rank_level, permission)
        perms = db.get_bot_rank_permissions(rank_level)
        text = f"⚙️ Права ранга {rank_level}\n━━━━━━━━━━━━━━━━\n\n"
        keyboard = []
        for perm, desc in BOT_BUTTON_PERMISSIONS.items():
            if perm in perms:
                keyboard.append([InlineKeyboardButton(f"✅ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {desc}", callback_data=f"toggle_bot_perm_{rank_level}_{perm}")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="bot_rank_permissions")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "super_admins_list":
        admins = db.get_all_super_admins()
        text = "👑 Супер-админы\n━━━━━━━━━━━━━━━━\n\n"
        text += f"• Основатель (ID: {FOUNDER_ID})\n\n"
        for admin in admins:
            text += f"• {admin['first_name']} (@{admin['username']})\n\n"
        keyboard = []
        if user.id == FOUNDER_ID:
            keyboard.append([InlineKeyboardButton("➕ Добавить", callback_data="add_super_admin"), InlineKeyboardButton("➖ Удалить", callback_data="remove_super_admin")])
        keyboard.append([InlineKeyboardButton("⬅️ Выход", callback_data="admin_panel")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "add_super_admin":
        context.user_data['adding_super_admin'] = True
        await query.edit_message_text("Введите ID:")
    elif data == "remove_super_admin":
        context.user_data['removing_super_admin'] = True
        await query.edit_message_text("Введите ID:")

    elif data == "profile":
        clan = db.get_user_clan(user.id)
        text = f"👤 Профиль\n━━━━━━━━━━━━━━━━\n\n🆔 ID: {user.id}\n🎖️ Ранг: {db.get_bot_rank_name(user.id)}\n🛡️ Клан: {clan['name'] if clan else 'Нет'}"
        await query.edit_message_text(text)

    elif data == "clan_menu":
        clan = db.get_user_clan(user.id)
        if not clan:
            keyboard = [
                [InlineKeyboardButton("➕ Создать клан", callback_data="create_clan")],
                [InlineKeyboardButton("🔍 Найти клан", callback_data="find_clan")],
                [InlineKeyboardButton("📋 Список кланов", callback_data="clan_list")],
                [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
            ]
            await query.edit_message_text("Вы не состоите в клане", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [
                [InlineKeyboardButton("👥 Участники", callback_data="clan_members")],
                [InlineKeyboardButton("⚔ Война", callback_data="clan_war")],
                [InlineKeyboardButton("⬅️ Выход", callback_data="start_menu")]
            ]
            await query.edit_message_text(format_clan_info(clan), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "create_clan":
        context.user_data['creating_clan'] = True
        await query.edit_message_text("Введите название клана:")

    elif data == "find_clan":
        context.user_data['finding_clan'] = True
        await query.edit_message_text("Напишите ID клана:")

    elif data == "clan_list":
        clans = db.get_top_clans(20)
        text = "📋 Список кланов\n━━━━━━━━━━━━━━━━\n\n"
        for i, clan in enumerate(clans, 1):
            text += f"{i}. {clan['name']}\n  ID: {clan['clan_id']}\n  🏆 {clan['rating']}\n\n"
        await query.edit_message_text(text)

    elif data == "clan_members":
        clan = db.get_user_clan(user.id)
        if not clan: return
        members = db.get_clan_members(clan['clan_id'])
        text = f"👥 Участники клана {clan['name']}\n━━━━━━━━━━━━━━━━\n\n"
        for member in members:
            role = "Лидер" if member['role'] == 'leader' else "Участник"
            text += f"• {member['first_name']} (@{member['username']}) - {role}\n\n"
        await query.edit_message_text(text)

    elif data == "clan_war":
        clan = db.get_user_clan(user.id)
        if not clan: return
        context.user_data['war_state'] = 'waiting_target'
        await query.edit_message_text("Введите ID клана противника:")

    elif data == "war_confirm":
        target_clan_id = context.user_data.get('war_target')
        rating = context.user_data.get('war_rating')
        if target_clan_id and rating:
            target_clan = db.get_clan(target_clan_id)
            user_clan = db.get_user_clan(user.id)
            if target_clan and user_clan:
                chance = calculate_war_win_chance(user_clan['rating'], target_clan['rating'])
                roll = random.randint(1, 100)
                if roll <= chance:
                    db.add_clan_rating(user_clan['clan_id'], rating)
                    db.add_clan_rating(target_clan_id, -rating)
                    await query.edit_message_text(f"⚔ Победа! +{rating} рейтинга!")
                else:
                    db.add_clan_rating(user_clan['clan_id'], -rating)
                    db.add_clan_rating(target_clan_id, rating)
                    await query.edit_message_text(f"💀 Поражение! -{rating} рейтинга")
        context.user_data['war_target'] = None
        context.user_data['war_rating'] = None
        context.user_data['war_state'] = None

    elif data == "war_cancel":
        context.user_data['war_state'] = None
        await query.edit_message_text("❌ Война отменена")

    elif data == "help":
        await query.edit_message_text("❓ Помощь\n\n/start /help /ping /id /stats /profile /clan /clan_top /report /clan_bonus /message_bot")

    elif data == "help_report":
        await query.edit_message_text("Ответьте на сообщение: /report <причина>")

    elif data == "help_question":
        context.user_data['question_state'] = 'waiting_question'
        await query.edit_message_text("Напишите ваш вопрос:")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text

    db.update_user_activity(user.id)

    if db.is_blacklisted(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return

    if await check_antispam(update, context):
        return

    if context.user_data.get('broadcasting'):
        context.user_data['broadcasting'] = False
        users = db.cursor.execute("SELECT user_id FROM users").fetchall()
        sent = 0
        for u in users:
            try:
                await context.bot.send_message(u[0], f"📣 Рассылка:\n\n{text}")
                sent += 1
            except:
                pass
        await update.message.reply_text(f"✅ Отправлено: {sent}")
        return

    if context.user_data.get('creating_clan'):
        context.user_data['creating_clan'] = False
        try:
            clan_id = db.create_clan(text, user.id)
            await update.message.reply_text(f"✅ Клан '{text}' создан! ID: {clan_id}")
        except:
            await update.message.reply_text("❌ Клан уже существует")
        return

    if context.user_data.get('finding_clan'):
        context.user_data['finding_clan'] = False
        try:
            clan_id = int(text)
            clan = db.get_clan(clan_id)
            if clan:
                if clan['join_enabled'] == 1:
                    db.cursor.execute("INSERT OR REPLACE INTO clan_members VALUES (?, ?, 'member')", (user.id, clan_id))
                    db.cursor.execute("UPDATE users SET clan_id = ? WHERE user_id = ?", (clan_id, user.id))
                    db.conn.commit()
                    await update.message.reply_text(f"✅ Вы вступили в клан {clan['name']}!")
                else:
                    await update.message.reply_text("❌ Вход запрещён")
            else:
                await update.message.reply_text("❌ Клан не найден")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    if context.user_data.get('awarding_user'):
        target_id = context.user_data['awarding_user']
        context.user_data['awarding_user'] = None
        db.add_award(target_id, user.id, text)
        await update.message.reply_text("🏅 Награда выдана!")
        return

    if context.user_data.get('adding_admin'):
        context.user_data['adding_admin'] = False
        try:
            db.add_bot_admin(int(text))
            await update.message.reply_text("✅ Админ назначен!")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    if context.user_data.get('removing_admin'):
        context.user_data['removing_admin'] = False
        try:
            db.remove_bot_admin(int(text))
            await update.message.reply_text("✅ Админ удалён!")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    if context.user_data.get('adding_agent'):
        context.user_data['adding_agent'] = False
        try:
            db.set_agent_level(int(text), 1)
            await update.message.reply_text("✅ Агент назначен!")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    if context.user_data.get('removing_agent'):
        context.user_data['removing_agent'] = False
        try:
            db.set_agent_level(int(text), 0)
            await update.message.reply_text("✅ Агент удалён!")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    if context.user_data.get('adding_super_admin'):
        context.user_data['adding_super_admin'] = False
        try:
            db.add_super_admin(int(text))
            await update.message.reply_text("✅ Супер-админ назначен!")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    if context.user_data.get('removing_super_admin'):
        context.user_data['removing_super_admin'] = False
        try:
            db.remove_super_admin(int(text))
            await update.message.reply_text("✅ Супер-админ удалён!")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    if context.user_data.get('question_state') == 'waiting_question':
        context.user_data['question_state'] = None
        db.add_ticket(user.id, text)
        await update.message.reply_text("✅ Вопрос отправлен!")
        return

    if context.user_data.get('war_state') == 'waiting_target':
        try:
            target_clan_id = int(text)
            if not db.get_clan(target_clan_id):
                await update.message.reply_text("❌ Клан не найден")
                return
            context.user_data['war_target'] = target_clan_id
            context.user_data['war_state'] = 'waiting_rating'
            await update.message.reply_text("Введите сумму рейтинга:")
        except:
            await update.message.reply_text("❌ Введите ID")
        return

    elif context.user_data.get('war_state') == 'waiting_rating':
        try:
            rating = int(text)
            context.user_data['war_rating'] = rating
            context.user_data['war_state'] = None
            keyboard = [[InlineKeyboardButton("✅ Да", callback_data="war_confirm"), InlineKeyboardButton("❌ Нет", callback_data="war_cancel")]]
            await update.message.reply_text(f"Начать войну на {rating} рейтинга?", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            await update.message.reply_text("❌ Введите число")
        return


async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    settings = db.get_chat_settings(chat_id)
    if not settings or not settings.get("welcome_enabled"):
        return
    for member in update.message.new_chat_members:
        text = settings.get("welcome_text", "Привет!")
        text = text.replace("{name}", member.full_name)
        text = text.replace("{chat}", update.effective_chat.title)
        await update.message.reply_text(text)


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("clan_top", clan_top_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("clan", clan_command))
    application.add_handler(CommandHandler("clan_bonus", clan_bonus_command))
    application.add_handler(CommandHandler("delclan", delclan_command))
    application.add_handler(CommandHandler("message_bot", message_bot_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("unwarn", unwarn_command))
    application.add_handler(CommandHandler("permban", permban_command))
    application.add_handler(CommandHandler("unperm", unperm_command))
    application.add_handler(CommandHandler("setadm", setadm_command))
    application.add_handler(CommandHandler("admins", admins_command))
    application.add_handler(CommandHandler("astats", astats_command))
    application.add_handler(CommandHandler("setrank", setrank_command))
    application.add_handler(CommandHandler("setagentlevel", setagentlevel_command))
    application.add_handler(CommandHandler("setsuperadmin", setsuperadmin_command))
    application.add_handler(CommandHandler("agents", agents_command))
    application.add_handler(CommandHandler("blacklist", blacklist_command))
    application.add_handler(CommandHandler("giverep", giverep_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот Fluxy запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()