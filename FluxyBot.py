import logging
import time
import random
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8980577910:AAGJFO588dLcq86neXNAcPUwIW9_xG7UHc8"
FOUNDER_ID = 8669060906
ONLY_OWNER_MODE = False

JSONBIN_API_KEY = "$2a$10$oQFi.r.b4KoxCupZTsKdzeH6ZktFfBr12SBHnTXgkmRwGBJr1bRdm"
JSONBIN_BIN_ID = "6a89a097f5f4af5e29354f5f"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
JSONBIN_HEADERS = {"X-Master-Key": JSONBIN_API_KEY, "Content-Type": "application/json"}

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
CHAT_RANK_5 = 5
CHAT_RANK_6 = 6
CHAT_RANK_7 = 7
CHAT_RANK_8 = 8
CHAT_RANK_9 = 9
CHAT_RANK_OWNER = 10

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
    "btn_rank_names": "📝 Названия рангов",
    "btn_rank_perms": "⚙️ Права рангов",
    "btn_super_admins": "👑 Супер-админы",
}

class Database:
    def __init__(self):
        self.data = self.load()
        if not self.data:
            self.data = {
                "users": {}, "clans": {}, "clan_members": {},
                "warnings": {}, "bans": {}, "mutes": {},
                "chat_settings": {}, "chat_members": {}, "clan_applications": {},
                "bot_rank_permissions": {
                    "1": ["btn_commands"],
                    "2": ["btn_commands", "btn_admins_list"],
                    "3": ["btn_commands", "btn_admins_list", "btn_agents_list"],
                    "4": ["btn_commands", "btn_admins_list", "btn_agents_list", "btn_blacklist"],
                    "5": ["btn_commands", "btn_admins_list", "btn_agents_list", "btn_blacklist", "btn_give_rep"],
                    "6": ["btn_commands", "btn_admins_list", "btn_agents_list", "btn_blacklist", "btn_give_rep", "btn_chats"],
                    "7": ["btn_commands", "btn_admins_list", "btn_agents_list", "btn_blacklist", "btn_give_rep", "btn_chats", "btn_ranks"],
                    "8": ["btn_admin_panel", "btn_admins_list", "btn_agents_list", "btn_blacklist", "btn_give_rep", "btn_commands", "btn_chats", "btn_ranks", "btn_rank_names", "btn_rank_perms"],
                    "9": ["btn_admin_panel", "btn_admins_list", "btn_agents_list", "btn_blacklist", "btn_give_rep", "btn_commands", "btn_chats", "btn_ranks", "btn_rank_names", "btn_rank_perms", "btn_super_admins"]
                }
            }
            self.save()

    def load(self):
        try:
            response = requests.get(JSONBIN_URL, headers=JSONBIN_HEADERS)
            if response.status_code == 200:
                return response.json().get("record", {})
        except:
            pass
        return {}

    def save(self):
        try:
            requests.put(JSONBIN_URL, json=self.data, headers=JSONBIN_HEADERS)
        except:
            pass

    def get_user(self, user_id):
        return self.data["users"].get(str(user_id))

    def add_user(self, user_id, username, first_name):
        if not self.get_user(user_id):
            self.data["users"][str(user_id)] = {
                "username": username or "Нет",
                "first_name": first_name or "Нет",
                "bot_rank": 0,
                "agent_level": 0,
                "clan_id": None
            }
            self.save()

    def get_bot_rank(self, user_id):
        if user_id == FOUNDER_ID:
            return BOT_RANK_FOUNDER
        user = self.get_user(user_id)
        return user.get("bot_rank", 0) if user else 0

    def set_bot_rank(self, user_id, rank):
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["bot_rank"] = rank
            self.save()

    def get_bot_rank_name(self, user_id):
        names = {0:"Пользователь",1:"Ранг 1",2:"Ранг 2",3:"Ранг 3",4:"Ранг 4",5:"Ранг 5",6:"Ранг 6",7:"Ранг 7",8:"Админ бота",9:"Высший админ",10:"Основатель бота"}
        return names.get(self.get_bot_rank(user_id), "Пользователь")

    def get_bot_rank_permissions(self, rank_level):
        return self.data.get("bot_rank_permissions", {}).get(str(rank_level), [])

    def add_bot_rank_permission(self, rank_level, permission):
        if "bot_rank_permissions" not in self.data:
            self.data["bot_rank_permissions"] = {}
        if str(rank_level) not in self.data["bot_rank_permissions"]:
            self.data["bot_rank_permissions"][str(rank_level)] = []
        if permission not in self.data["bot_rank_permissions"][str(rank_level)]:
            self.data["bot_rank_permissions"][str(rank_level)].append(permission)
            self.save()

    def remove_bot_rank_permission(self, rank_level, permission):
        if "bot_rank_permissions" in self.data:
            if str(rank_level) in self.data["bot_rank_permissions"]:
                if permission in self.data["bot_rank_permissions"][str(rank_level)]:
                    self.data["bot_rank_permissions"][str(rank_level)].remove(permission)
                    self.save()

    def has_bot_permission(self, user_id, permission):
        rank = self.get_bot_rank(user_id)
        if rank >= 10:
            return True
        perms = self.get_bot_rank_permissions(rank)
        return permission in perms

    def get_agent_level(self, user_id):
        user = self.get_user(user_id)
        return user.get("agent_level", 0) if user else 0

    def set_agent_level(self, user_id, level):
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["agent_level"] = level
            self.save()

    def get_agent_level_name(self, user_id):
        names = {0:"Не агент",1:"Агент поддержки",2:"Главный агент",3:"ГС агентов"}
        return names.get(self.get_agent_level(user_id), "Не агент")

    def get_all_agents(self):
        agents = []
        for uid, data in self.data["users"].items():
            if data.get("agent_level", 0) > 0:
                agents.append({"user_id": int(uid), "username": data.get("username"), "first_name": data.get("first_name")})
        return agents

    def get_all_bot_admins(self):
        admins = [{"user_id": FOUNDER_ID, "username": "Основатель", "first_name": "Основатель"}]
        for uid, data in self.data["users"].items():
            if data.get("bot_rank", 0) >= 1 and int(uid) != FOUNDER_ID:
                admins.append({"user_id": int(uid), "username": data.get("username"), "first_name": data.get("first_name")})
        return admins

    def is_super_admin(self, user_id):
        return user_id == FOUNDER_ID or self.get_bot_rank(user_id) >= 9

    def get_chat_member_rank(self, chat_id, user_id):
        return self.data["chat_members"].get(f"{chat_id}:{user_id}", 0)

    def set_chat_member_rank(self, chat_id, user_id, rank):
        self.data["chat_members"][f"{chat_id}:{user_id}"] = rank
        self.save()

    def has_chat_permission(self, chat_id, user_id, permission):
        rank = self.get_chat_member_rank(chat_id, user_id)
        if rank >= 10:
            return True
        perms = {
            1: ["btn_chat_admin"],
            2: ["btn_chat_admin", "btn_kick"],
            3: ["btn_chat_admin", "btn_kick", "btn_warn"],
            4: ["btn_chat_admin", "btn_kick", "btn_warn", "btn_mute"],
            6: ["btn_chat_admin", "btn_kick", "btn_warn", "btn_mute", "btn_ban"]
        }
        return permission in perms.get(rank, [])

    def get_all_chat_admins(self, chat_id):
        admins = []
        for key, r in self.data["chat_members"].items():
            if r >= 1 and key.startswith(f"{chat_id}:"):
                uid = int(key.split(":")[1])
                user = self.get_user(uid)
                admins.append({"user_id": uid, "chat_rank": r, "username": user.get("username") if user else "Нет", "first_name": user.get("first_name") if user else "Нет"})
        return sorted(admins, key=lambda x: -x["chat_rank"])

    def add_warning(self, chat_id, user_id, warned_by, reason):
        warn_id = str(len(self.data["warnings"]) + 1)
        self.data["warnings"][warn_id] = {"chat_id": chat_id, "user_id": user_id, "reason": reason, "warn_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        self.save()

    def add_ban(self, chat_id, user_id, banned_by, reason):
        ban_id = str(len(self.data["bans"]) + 1)
        self.data["bans"][ban_id] = {"chat_id": chat_id, "user_id": user_id, "reason": reason, "ban_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        self.save()

    def add_mute(self, chat_id, user_id, muted_by, reason, unmute_date):
        mute_id = str(len(self.data["mutes"]) + 1)
        self.data["mutes"][mute_id] = {"chat_id": chat_id, "user_id": user_id, "reason": reason, "mute_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "unmute_date": unmute_date}
        self.save()

    def remove_warning(self, chat_id, user_id):
        for key in list(self.data["warnings"].keys()):
            if self.data["warnings"][key]["chat_id"] == chat_id and self.data["warnings"][key]["user_id"] == user_id:
                del self.data["warnings"][key]
        self.save()

    def remove_ban(self, chat_id, user_id):
        for key in list(self.data["bans"].keys()):
            if self.data["bans"][key]["chat_id"] == chat_id and self.data["bans"][key]["user_id"] == user_id:
                del self.data["bans"][key]
        self.save()

    def remove_mute(self, chat_id, user_id):
        for key in list(self.data["mutes"].keys()):
            if self.data["mutes"][key]["chat_id"] == chat_id and self.data["mutes"][key]["user_id"] == user_id:
                del self.data["mutes"][key]
        self.save()

    def create_clan(self, name, leader_id):
        clan_id = str(len(self.data["clans"]) + 1)
        self.data["clans"][clan_id] = {"name": name, "leader_id": leader_id, "rating": 0, "join_enabled": 1}
        self.data["clan_members"][str(leader_id)] = {"clan_id": int(clan_id), "role": "leader"}
        if str(leader_id) in self.data["users"]:
            self.data["users"][str(leader_id)]["clan_id"] = int(clan_id)
        self.save()
        return int(clan_id)

    def get_clan(self, clan_id):
        return self.data["clans"].get(str(clan_id))

    def get_user_clan(self, user_id):
        user = self.get_user(user_id)
        if user and user.get("clan_id"):
            return self.get_clan(user["clan_id"])
        return None

    def get_clan_member(self, user_id):
        return self.data["clan_members"].get(str(user_id))

    def get_clan_members(self, clan_id):
        members = []
        for uid, data in self.data["clan_members"].items():
            if data["clan_id"] == clan_id:
                user = self.get_user(int(uid))
                members.append({"user_id": int(uid), "role": data.get("role", "member"), "username": user.get("username") if user else "Нет", "first_name": user.get("first_name") if user else "Нет"})
        return members

    def get_clan_members_count(self, clan_id):
        return len([d for d in self.data["clan_members"].values() if d["clan_id"] == clan_id])

    def set_clan_join_enabled(self, clan_id, mode):
        if str(clan_id) in self.data["clans"]:
            self.data["clans"][str(clan_id)]["join_enabled"] = mode
            self.save()

    def get_top_clans(self, limit=10):
        clans = []
        for cid, data in self.data["clans"].items():
            clans.append({"clan_id": int(cid), "name": data["name"], "rating": data.get("rating", 0)})
        clans.sort(key=lambda x: -x["rating"])
        return clans[:limit]

    def add_clan_rating(self, clan_id, rating):
        if str(clan_id) in self.data["clans"]:
            self.data["clans"][str(clan_id)]["rating"] = self.data["clans"][str(clan_id)].get("rating", 0) + rating
            self.save()

    def get_chat_settings(self, chat_id):
        return self.data["chat_settings"].get(str(chat_id))

    def save_chat_settings(self, chat_id, **kwargs):
        if str(chat_id) not in self.data["chat_settings"]:
            self.data["chat_settings"][str(chat_id)] = {}
        for key, value in kwargs.items():
            self.data["chat_settings"][str(chat_id)][key] = value
        self.save()

    def add_to_blacklist(self, user_id, reason):
        if "black_list" not in self.data:
            self.data["black_list"] = {}
        self.data["black_list"][str(user_id)] = reason
        self.save()

    def remove_from_blacklist(self, user_id):
        if "black_list" in self.data and str(user_id) in self.data["black_list"]:
            del self.data["black_list"][str(user_id)]
            self.save()

    def is_blacklisted(self, user_id):
        return "black_list" in self.data and str(user_id) in self.data["black_list"]

    def get_blacklist(self):
        if "black_list" not in self.data:
            return []
        result = []
        for uid, reason in self.data["black_list"].items():
            user = self.get_user(int(uid))
            result.append({"user_id": int(uid), "reason": reason, "username": user.get("username") if user else "Нет", "first_name": user.get("first_name") if user else "Нет"})
        return result

    def add_award(self, user_id, awarded_by, award_text):
        if "awards" not in self.data:
            self.data["awards"] = []
        self.data["awards"].append({"user_id": user_id, "awarded_by": awarded_by, "award_text": award_text, "award_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
        self.save()

    def get_user_awards(self, user_id):
        if "awards" not in self.data:
            return []
        awards = [a for a in self.data["awards"] if a["user_id"] == user_id]
        result = []
        for a in awards:
            user = self.get_user(a["awarded_by"])
            result.append({"award_text": a["award_text"], "award_date": a["award_date"], "awarded_by_username": user.get("username") if user else "Нет"})
        return result

    def add_ticket(self, user_id, user_username, question):
        if "tickets" not in self.data:
            self.data["tickets"] = []
        ticket_id = len(self.data["tickets"]) + 1
        self.data["tickets"].append({"id": ticket_id, "user_id": user_id, "question": question, "status": "open"})
        self.save()
        return ticket_id

    def get_ticket(self, ticket_id):
        if "tickets" in self.data:
            for t in self.data["tickets"]:
                if t["id"] == ticket_id:
                    return t
        return None

    def assign_ticket(self, ticket_id, agent_id, agent_username):
        if "tickets" in self.data:
            for t in self.data["tickets"]:
                if t["id"] == ticket_id:
                    t["status"] = "in_progress"
                    t["agent_id"] = agent_id
                    self.save()
                    break

    def close_ticket(self, ticket_id, answer):
        if "tickets" in self.data:
            for t in self.data["tickets"]:
                if t["id"] == ticket_id:
                    t["status"] = "closed"
                    t["answer"] = answer
                    self.save()
                    break

    def add_report(self, reporter_id, reporter_username, target_id, target_username, reason, chat_id, chat_title, message_link):
        if "reports" not in self.data:
            self.data["reports"] = []
        report_id = len(self.data["reports"]) + 1
        self.data["reports"].append({"id": report_id, "reporter_id": reporter_id, "target_id": target_id, "reason": reason, "answered_by": None})
        self.save()
        return report_id

    def set_report_answered_by(self, report_id, admin_id):
        if "reports" in self.data:
            for r in self.data["reports"]:
                if r["id"] == report_id:
                    r["answered_by"] = admin_id
                    self.save()
                    break

    def get_admin_reply_count(self, admin_id):
        if "reports" not in self.data:
            return 0
        return len([r for r in self.data["reports"] if r.get("answered_by") == admin_id])

    def get_agent_reply_count(self, agent_id):
        if "tickets" not in self.data:
            return 0
        return len([t for t in self.data["tickets"] if t.get("agent_id") == agent_id and t.get("status") == "closed"])

    def can_get_daily_bonus(self, clan_id):
        if "daily_bonus" not in self.data:
            self.data["daily_bonus"] = {}
        today = datetime.now().strftime('%Y-%m-%d')
        return self.data["daily_bonus"].get(str(clan_id)) != today

    def give_daily_bonus(self, clan_id):
        if "daily_bonus" not in self.data:
            self.data["daily_bonus"] = {}
        self.data["daily_bonus"][str(clan_id)] = datetime.now().strftime('%Y-%m-%d')
        self.save()

    def get_bot_stats(self):
        users_count = len(self.data["users"])
        clans_count = len(self.data["clans"])
        chats_count = len(set(key.split(":")[0] for key in self.data["chat_members"].keys()))
        return {"users": users_count, "chats": chats_count, "clans": clans_count, "active_today": users_count}

    def update_user_activity(self, user_id):
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["last_activity"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def add_chat_member(self, chat_id, user_id, chat_rank=0):
        if f"{chat_id}:{user_id}" not in self.data["chat_members"]:
            self.data["chat_members"][f"{chat_id}:{user_id}"] = chat_rank

    def add_chat(self, chat_id, chat_type, chat_title):
        if "chats" not in self.data:
            self.data["chats"] = {}
        self.data["chats"][str(chat_id)] = {"chat_type": chat_type, "chat_title": chat_title}
        self.save()

    def get_all_chats(self):
        if "chats" not in self.data:
            return []
        result = []
        for cid, data in self.data["chats"].items():
            result.append({"chat_id": int(cid), "chat_type": data.get("chat_type"), "chat_title": data.get("chat_title")})
        return result

    def get_all_super_admins(self):
        return [{"user_id": int(uid), "username": d.get("username"), "first_name": d.get("first_name")} for uid, d in self.data["users"].items() if d.get("bot_rank", 0) >= 9]

    def add_bot_admin(self, user_id):
        if str(user_id) not in self.data["users"]:
            self.data["users"][str(user_id)] = {"username": "Неизвестный", "first_name": "Пользователь", "bot_rank": 1, "agent_level": 0, "clan_id": None}
        self.data["users"][str(user_id)]["bot_rank"] = 1
        self.save()

    def remove_bot_admin(self, user_id):
        if str(user_id) in self.data["users"]:
            self.data["users"][str(user_id)]["bot_rank"] = 0
            self.save()

    def get_user_by_username(self, username):
        username = username.replace('@', '')
        for uid, data in self.data["users"].items():
            if data.get("username") == username:
                return {"user_id": int(uid), **data}
        return None

db = Database()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def has_bot_permission(user_id: int, permission: str) -> bool:
    return db.has_bot_permission(user_id, permission)

def is_super_admin(user_id: int) -> bool:
    return db.is_super_admin(user_id)

def is_chat_owner(chat_id: int, user_id: int) -> bool:
    return db.get_chat_member_rank(chat_id, user_id) >= CHAT_RANK_OWNER

def has_chat_permission(chat_id: int, user_id: int, permission: str) -> bool:
    return db.has_chat_permission(chat_id, user_id, permission)

def is_blacklisted_check(user_id: int) -> bool:
    return db.is_blacklisted(user_id)

def format_clan_info(clan: Dict) -> str:
    if not clan:
        return "Вы не состоите в клане"
    return f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan.get('clan_id', 'Нет')}
🛡 Название: {clan.get('name', 'Нет')}
🏆 Рейтинг: {clan.get('rating', 0)}

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
            await update.effective_message.reply_text(f"🚫 <b>{update.effective_user.full_name}</b> исключён за спам!", parse_mode='HTML')
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
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    target_id = await get_target_user_id(update, context)
    if target_id:
        await update.message.reply_text(f"🆔 ID пользователя: {target_id}")
    else:
        await update.message.reply_text("Использование: /id [ID или @username]\nИли ответьте на сообщение")

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    start_time = time.time()
    msg = await update.message.reply_text("📡 Измеряю пинг...")
    end_time = time.time()
    ping = round((end_time - start_time) * 1000)
    await msg.edit_text(f"🏓 Понг!\n⏱️ Пинг: {ping} мс")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке бота")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("Использование: /stats [ID или @username]\nИли ответьте на сообщение")
        return
    target_user_data = db.get_user(target_id)
    if not target_user_data:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    clan = db.get_user_clan(target_id)
    clan_name = clan['name'] if clan else "Нет клана"
    text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

👤 Имя: {target_user_data.get('first_name', 'Нет')}
🔗 Username: @{target_user_data.get('username', 'Нет')}
🆔 ID: {target_id}

🎖️ Ранг: {db.get_bot_rank_name(target_id)}
🛡️ Клан: {clan_name}

━━━━━━━━━━━━━━━━"""
    if chat and chat.type != "private" and has_chat_permission(chat.id, user.id, "btn_warn"):
        text += "\n\n⚠️ Наказания:\n"
        warnings = [w for w in db.data.get("warnings", {}).values() if w.get("chat_id") == chat.id and w.get("user_id") == target_id]
        bans = [b for b in db.data.get("bans", {}).values() if b.get("chat_id") == chat.id and b.get("user_id") == target_id]
        if warnings:
            text += "Предупреждения:\n"
            for w in warnings:
                text += f"  • {w.get('reason')}\n"
        if bans:
            text += "Баны:\n"
            for b in bans:
                text += f"  • {b.get('reason')}\n"
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
    if is_super_admin(target_id):
        await update.message.reply_text("⛔ Нельзя")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    if update.message.reply_to_message:
        reason = ' '.join(context.args) if context.args else "Не указана"
    db.add_to_blacklist(target_id, reason)
    await update.message.reply_text(f"🚫 Пользователь {target_id} в ЧС\nПричина: {reason}")

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
    await update.message.reply_text(f"✅ Пользователь {target_id} удален из ЧС")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
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
        await update.message.reply_text(f"✅ Пользователь {target_id} кикнут")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_warn"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/warn [ID/@username] [причина]")
        return
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    if update.message.reply_to_message:
        reason = ' '.join(context.args) if context.args else "Не указана"
    db.add_warning(chat.id, target_id, user.id, reason)
    await update.message.reply_text(f"⚠️ Пользователь {target_id} предупреждён\nПричина: {reason}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_ban"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/ban [ID/@username] [причина]")
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

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    if not has_chat_permission(chat.id, user.id, "btn_mute"):
        await update.message.reply_text("⛔ Нет прав")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/mute [ID/@username] [минуты]")
        return
    minutes = 60
    if context.args:
        if context.args[-1].isdigit():
            minutes = int(context.args[-1])
    try:
        unmute_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_id, permissions=ChatPermissions(can_send_messages=False), until_date=unmute_time)
        db.add_mute(chat.id, target_id, user.id, "Мут", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        await update.message.reply_text(f"🔇 Пользователь {target_id} замучен на {minutes} мин")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
        return
    target_id = await get_target_user_id(update, context)
    if not target_id:
        await update.message.reply_text("/unmute [ID/@username]")
        return
    try:
        await context.bot.restrict_chat_member(chat_id=chat.id, user_id=target_id, permissions=ChatPermissions(can_send_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        db.remove_mute(chat.id, target_id)
        await update.message.reply_text(f"🔊 Пользователь {target_id} размучен")
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
        await update.message.reply_text(f"✅ Пользователь {target_id} разбанен")
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
    await update.message.reply_text(f"✅ Предупреждение снято")

async def setadm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if is_blacklisted_check(user.id):
        await update.message.reply_text("❌ Вы в черном списке")
        return
    if not chat or chat.type == "private":
        await update.message.reply_text("⛔ Только для групп")
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
            await update.message.reply_text("❌ Укажите ранг: /setadm 5")
            return
    else:
        if len(context.args) >= 2 and context.args[1].isdigit():
            rank = int(context.args[1])
        else:
            await update.message.reply_text("/setadm [ID/@username] [ранг 0-10]")
            return
    db.set_chat_member_rank(chat.id, target_id, rank)
    await update.message.reply_text(f"✅ Пользователь {target_id} получил ранг {rank}")

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
    sent = 0
    for uid in db.data["users"].keys():
        try:
            await context.bot.send_message(int(uid), f"📣 Рассылка:\n\n{text}")
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
                    db.set_chat_member_rank(chat.id, admin.user.id, CHAT_RANK_OWNER)
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
    text = """❓ Помощь
━━━━━━━━━━━━━━━━

/start - Запуск
/help - Помощь
/ping - Пинг
/id - ID
/stats - Профиль
/profile - Профиль
/clan - Клан
/clan_top - Топ кланов
/report - Жалоба
/clan_bonus - Бонус
"""
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
        await update.message.reply_text("Ответьте на сообщение нарушителя: /report <причина>")
        return
    target = update.message.reply_to_message.from_user
    reason = ' '.join(context.args) if context.args else "Не указана"
    db.add_report(user.id, user.username or "Нет", target.id, target.username or "Нет", reason, update.effective_chat.id, "Чат", "Нет")
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
    clan_id = int(clan.get('clan_id', 0))
    if not db.can_get_daily_bonus(clan_id):
        await update.message.reply_text("❌ Бонус уже получен!")
        return
    count = db.get_clan_members_count(clan_id)
    db.give_daily_bonus(clan_id)
    db.add_clan_rating(clan_id, count)
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
        if str(clan_id) in db.data["clans"]:
            del db.data["clans"][str(clan_id)]
            db.save()
            await update.message.reply_text("✅ Клан удалён!")
        else:
            await update.message.reply_text("❌ Не найдено")
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
        if has_bot_permission(user.id, "btn_blacklist"):
            row.append(InlineKeyboardButton("🚫 ЧС", callback_data="black_list"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_give_rep"):
            row.append(InlineKeyboardButton("⭐️ Репутация", callback_data="give_rep"))
        if has_bot_permission(user.id, "btn_commands"):
            row.append(InlineKeyboardButton("📣 Рассылка", callback_data="broadcast"))
        if row: keyboard.append(row)
        row = []
        if has_bot_permission(user.id, "btn_commands"):
            row.append(InlineKeyboardButton("📊 Статистика", callback_data="bot_stats"))
        if has_bot_permission(user.id, "btn_rank_perms"):
            row.append(InlineKeyboardButton("⚙️ Права рангов", callback_data="bot_rank_permissions"))
        if row: keyboard.append(row)
        row = []
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
            text += f"• {admin['first_name']} (@{admin['username']})\n  Ранг: {db.get_bot_rank_name(admin['user_id'])}\n  ID: {admin['user_id']}\n\n"
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

    elif data == "black_list":
        blacklist = db.get_blacklist()
        text = "🚫 Черный список\n━━━━━━━━━━━━━━━━\n\n"
        if not blacklist:
            text += "Пуст"
        else:
            for u in blacklist:
                text += f"• {u['first_name']} (@{u['username']})\n  ID: {u['user_id']}\n  Причина: {u['reason']}\n\n"
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
        text = f"⚙️ Права ранга {rank_level}\n━━━━━━━━━━━━━━━━\n\nНажмите для переключения:\n\n"
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
        text = f"⚙️ Права ранга {rank_level}\n━━━━━━━━━━━━━━━━\n\nНажмите для переключения:\n\n"
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
            text += f"• {admin['first_name']} (@{admin['username']})\n  ID: {admin['user_id']}\n\n"
        await query.edit_message_text(text)

    elif data == "profile":
        clan = db.get_user_clan(user.id)
        text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(user.id)}
🛡️ Клан: {clan['name'] if clan else 'Нет'}

━━━━━━━━━━━━━━━━"""
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
        members = db.get_clan_members(int(clan.get('clan_id', 0)))
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
                chance = calculate_war_win_chance(user_clan.get('rating', 0), target_clan.get('rating', 0))
                roll = random.randint(1, 100)
                if roll <= chance:
                    db.add_clan_rating(int(user_clan.get('clan_id', 0)), rating)
                    db.add_clan_rating(target_clan_id, -rating)
                    await query.edit_message_text(f"⚔ Победа! +{rating} рейтинга!")
                else:
                    db.add_clan_rating(int(user_clan.get('clan_id', 0)), -rating)
                    db.add_clan_rating(target_clan_id, rating)
                    await query.edit_message_text(f"💀 Поражение! -{rating} рейтинга")
        context.user_data['war_target'] = None
        context.user_data['war_rating'] = None
        context.user_data['war_state'] = None

    elif data == "war_cancel":
        context.user_data['war_state'] = None
        await query.edit_message_text("❌ Война отменена")

    elif data == "help":
        text = "❓ Помощь\n\n/start /help /ping /id /stats /profile /clan /clan_top /report /clan_bonus"
        await query.edit_message_text(text)

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
        sent = 0
        for uid in db.data["users"].keys():
            try:
                await context.bot.send_message(int(uid), f"📣 Рассылка:\n\n{text}")
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
                if clan.get('join_enabled') == 1:
                    db.data["clan_members"][str(user.id)] = {"clan_id": clan_id, "role": "member"}
                    if str(user.id) in db.data["users"]:
                        db.data["users"][str(user.id)]["clan_id"] = clan_id
                    db.save()
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

    if context.user_data.get('question_state') == 'waiting_question':
        context.user_data['question_state'] = None
        db.add_ticket(user.id, user.username or "Нет", text)
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
    application.add_handler(CommandHandler("setrank", setrank_command))
    application.add_handler(CommandHandler("blacklist", blacklist_command))
    application.add_handler(CommandHandler("giverep", giverep_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот Fluxy запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()