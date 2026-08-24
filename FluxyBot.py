#==================#
#1 ЧАСТЬ | Импорты  #
#==================#

import asyncio
import random
import requests
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import logging

BOT_TOKEN = "8980577910:AAGJFO588dLcq86neXNAcPUwIW9_xG7UHc8"
SUPER_ADMIN_ID = 8669060906
BOT_USERNAME = "fluxy_cm_bot"

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
WAITING_FOR_REWARD_USER = 32
WAITING_FOR_REWARD_TEXT = 33
WAITING_FOR_TRANSFER_CLAN = 35
WAITING_FOR_RENAME = 36
WAITING_FOR_QUESTION = 37
WAITING_FOR_REPORT_ANSWER = 38
WAITING_FOR_QUESTION_ANSWER = 39

JSONBIN_API_KEY = "$2a$10$oQFi.r.b4KoxCupZTsKdzeH6ZktFfBr12SBHnTXgkmRwGBJr1bRdm"
JSONBIN_BIN_ID = "6a8ac58bda38895dfe06783c"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
JSONBIN_HEADERS = {"X-Master-Key": JSONBIN_API_KEY, "Content-Type": "application/json"}

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.local_file = "backup_local.json"
        self.data = {}
        self.load_data()
        self.ensure_keys()
    
    def load_data(self):
        try:
            with open(self.local_file, 'r') as f:
                self.data = json.load(f)
                print("✅ Локальный файл загружен")
                return
        except:
            pass
        try:
            response = requests.get(JSONBIN_URL, headers=JSONBIN_HEADERS, timeout=5)
            if response.status_code == 200:
                self.data = response.json().get("record", {})
                print("✅ JSONBin загружен")
                return
        except:
            pass
        self.data = {}
    
    def ensure_keys(self):
        defaults = {
            "users": [], "bot_admins": [], "support_agents": [],
            "chats": [], "clans": [], "bot_blacklist": [],
            "access_settings": [], "reports": [], "questions": [],
            "chat_messages": [], "clan_bonus_usage": [], "rewards": [],
            "bot_rank_names": {}, "agent_rank_names": {}, "chat_rank_names": {},
            "clan_requests": [], "clan_messages": [],
        }
        for key, value in defaults.items():
            if key not in self.data:
                self.data[key] = value
    
    def save_data(self):
        try:
            with open(self.local_file, 'w') as f:
                json.dump(self.data, f)
        except:
            pass
        try:
            requests.put(JSONBIN_URL, headers=JSONBIN_HEADERS, json=self.data, timeout=5)
        except:
            pass
    
    def add_user(self, user_id, username, first_name):
        for u in self.data["users"]:
            if u["user_id"] == user_id:
                return
        self.data["users"].append({"user_id": user_id, "username": username or "", "first_name": first_name or "Пользователь", "clan_id": None, "warnings": 0})
        self.save_data()
    
    def get_user(self, user_id):
        for u in self.data["users"]:
            if u["user_id"] == user_id:
                return u
        return None
    
    def get_all_users(self):
        return [u["user_id"] for u in self.data["users"]]
    
    def get_bot_admin_level(self, user_id):
        if user_id == SUPER_ADMIN_ID:
            return 10
        for a in self.data["bot_admins"]:
            if a["user_id"] == user_id:
                return a.get("level", 1)
        return 0
    
    def add_bot_admin(self, user_id, level, added_by):
        for a in self.data["bot_admins"]:
            if a["user_id"] == user_id:
                a["level"] = level
                self.save_data()
                return
        self.data["bot_admins"].append({"user_id": user_id, "level": level, "added_by": added_by})
        self.save_data()
    
    def remove_bot_admin(self, user_id):
        self.data["bot_admins"] = [a for a in self.data["bot_admins"] if a["user_id"] != user_id]
        self.save_data()
    
    def get_all_bot_admins(self):
        result = []
        for a in self.data["bot_admins"]:
            u = self.get_user(a["user_id"])
            result.append({"user_id": a["user_id"], "level": a["level"], "first_name": u["first_name"] if u else "Пользователь"})
        return sorted(result, key=lambda x: x["level"], reverse=True)
    
    def update_bot_admin_level(self, user_id, level):
        for a in self.data["bot_admins"]:
            if a["user_id"] == user_id:
                a["level"] = level
                self.save_data()
                return
    
    def add_agent(self, user_id, level):
        for a in self.data["support_agents"]:
            if a["user_id"] == user_id:
                a["level"] = level
                self.save_data()
                return
        self.data["support_agents"].append({"user_id": user_id, "level": level})
        self.save_data()
    
    def remove_agent(self, user_id):
        self.data["support_agents"] = [a for a in self.data["support_agents"] if a["user_id"] != user_id]
        self.save_data()
    
    def get_agent_level(self, user_id):
        for a in self.data["support_agents"]:
            if a["user_id"] == user_id:
                return a.get("level", 1)
        return 0
    
    def get_all_agents(self):
        result = []
        for a in self.data["support_agents"]:
            u = self.get_user(a["user_id"])
            result.append({"user_id": a["user_id"], "level": a["level"], "first_name": u["first_name"] if u else "Агент"})
        return result
    
    def update_agent_level(self, user_id, level):
        for a in self.data["support_agents"]:
            if a["user_id"] == user_id:
                a["level"] = level
                self.save_data()
                return
    
    def create_clan(self, name, leader_id):
        clan_id = len(self.data["clans"]) + 1
        self.data["clans"].append({"clan_id": clan_id, "name": name, "leader_id": leader_id, "rating": 0, "entry_type": "open", "total_members": 1, "wins": 0, "losses": 0})
        for u in self.data["users"]:
            if u["user_id"] == leader_id:
                u["clan_id"] = clan_id
        self.save_data()
        return clan_id
    
    def get_clan_by_id(self, clan_id):
        for c in self.data["clans"]:
            if c["clan_id"] == clan_id:
                return c
        return None
    
    def get_clan_by_name(self, name):
        for c in self.data["clans"]:
            if c["name"] == name:
                return c
        return None
    
    def get_user_clan(self, user_id):
        u = self.get_user(user_id)
        if u and u.get("clan_id"):
            return self.get_clan_by_id(u["clan_id"])
        return None
    
    def join_clan(self, user_id, clan_id):
        for u in self.data["users"]:
            if u["user_id"] == user_id:
                u["clan_id"] = clan_id
        for c in self.data["clans"]:
            if c["clan_id"] == clan_id:
                c["total_members"] = sum(1 for u in self.data["users"] if u.get("clan_id") == clan_id)
        self.save_data()
    
    def leave_clan(self, user_id):
        for u in self.data["users"]:
            if u["user_id"] == user_id:
                u["clan_id"] = None
        self.save_data()
    
    def get_clan_members(self, clan_id):
        return [u for u in self.data["users"] if u.get("clan_id") == clan_id]
    
    def add_clan_rating(self, clan_id, rating):
        for c in self.data["clans"]:
            if c["clan_id"] == clan_id:
                c["rating"] = c.get("rating", 0) + rating
                self.save_data()
                return
    
    def get_top_clans(self, limit=10):
        return sorted(self.data["clans"], key=lambda x: (x.get("rating", 0), x.get("total_members", 0)), reverse=True)[:limit]
    
    def update_clan_entry_type(self, clan_id, entry_type):
        for c in self.data["clans"]:
            if c["clan_id"] == clan_id:
                c["entry_type"] = entry_type
                self.save_data()
                return
    
    def add_clan_request(self, clan_id, user_id):
        self.data["clan_requests"].append({"request_id": len(self.data["clan_requests"]) + 1, "clan_id": clan_id, "user_id": user_id, "status": "pending"})
        self.save_data()
    
    def get_clan_requests(self, clan_id):
        return [r for r in self.data["clan_requests"] if r["clan_id"] == clan_id and r["status"] == "pending"]
    
    def update_clan_request(self, request_id, status):
        for r in self.data["clan_requests"]:
            if r.get("request_id") == request_id:
                r["status"] = status
                self.save_data()
                return
    
    def declare_war(self, clan1_id, clan2_id, rating_stake):
        winner = random.choice([clan1_id, clan2_id])
        loser = clan2_id if winner == clan1_id else clan1_id
        self.add_clan_rating(winner, rating_stake)
        self.add_clan_rating(loser, -rating_stake)
        c1 = self.get_clan_by_id(clan1_id)
        c2 = self.get_clan_by_id(clan2_id)
        return {"winner_id": winner, "clan1_name": c1["name"], "clan2_name": c2["name"]}
    
    def add_clan_message(self, from_clan, to_clan, from_user, text):
        self.data["clan_messages"].append({"from_clan_id": from_clan, "to_clan_id": to_clan, "from_user_id": from_user, "text": text})
        self.save_data()
    
    def get_clan_messages(self, clan_id):
        return [m for m in self.data["clan_messages"] if m["to_clan_id"] == clan_id]
    
    def add_to_blacklist(self, user_id, reason, added_by):
        self.data["bot_blacklist"].append({"user_id": user_id, "reason": reason})
        self.save_data()
    
    def remove_from_blacklist(self, user_id):
        self.data["bot_blacklist"] = [b for b in self.data["bot_blacklist"] if b["user_id"] != user_id]
        self.save_data()
    
    def is_blacklisted(self, user_id):
        return any(b["user_id"] == user_id for b in self.data["bot_blacklist"])
    
    def get_blacklist(self):
        return self.data["bot_blacklist"]
    
    def add_report(self, user_id, reported_id, reason, link=None):
        rid = len(self.data["reports"]) + 1
        self.data["reports"].append({"report_id": rid, "user_id": user_id, "reported_user_id": reported_id, "reason": reason, "status": "pending", "message_link": link})
        self.save_data()
        return rid
    
    def get_pending_reports(self):
        return [r for r in self.data["reports"] if r["status"] == "pending"]
    
    def update_report_status(self, rid, status, handled_by):
        for r in self.data["reports"]:
            if r["report_id"] == rid:
                r["status"] = status
                self.save_data()
                return
    
    def add_question(self, user_id, text):
        qid = len(self.data["questions"]) + 1
        self.data["questions"].append({"question_id": qid, "user_id": user_id, "text": text, "status": "pending"})
        self.save_data()
        return qid
    
    def get_pending_questions(self):
        return [q for q in self.data["questions"] if q["status"] == "pending"]
    
    def update_question_status(self, qid, status, answered_by, answer=None):
        for q in self.data["questions"]:
            if q["question_id"] == qid:
                q["status"] = status
                q["answer_text"] = answer
                self.save_data()
                return
    
    def add_chat(self, chat_id, title):
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                return
        self.data["chats"].append({"chat_id": chat_id, "title": title or "Чат", "welcome_enabled": 0, "welcome_text": None, "antispam_enabled": 0, "antispam_seconds": 5, "antispam_max_messages": 5})
        self.save_data()
    
    def get_welcome_settings(self, chat_id):
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                return [c.get("welcome_enabled", 0), c.get("welcome_text")]
        return None
    
    def set_welcome_text(self, chat_id, text):
        self.add_chat(chat_id, "Чат")
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                c["welcome_text"] = text
                c["welcome_enabled"] = 1
                self.save_data()
                return
    
    def enable_welcome(self, chat_id, enabled):
        self.add_chat(chat_id, "Чат")
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                c["welcome_enabled"] = 1 if enabled else 0
                self.save_data()
                return
    
    def get_antispam_settings(self, chat_id):
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                return [c.get("antispam_enabled", 0), c.get("antispam_seconds", 5)]
        return None
    
    def enable_antispam(self, chat_id, enabled):
        self.add_chat(chat_id, "Чат")
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                c["antispam_enabled"] = 1 if enabled else 0
                self.save_data()
                return
    
    def set_antispam_seconds(self, chat_id, seconds):
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                c["antispam_seconds"] = seconds
                self.save_data()
                return
    
    def set_antispam_max_messages(self, chat_id, max_msg):
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                c["antispam_max_messages"] = max_msg
                self.save_data()
                return
    
    def get_antispam_max_messages(self, chat_id):
        for c in self.data["chats"]:
            if c["chat_id"] == chat_id:
                return c.get("antispam_max_messages", 5)
        return 5
    
    def get_bot_rank_name(self, level):
        ranks = {0: "Пользователь", 1: "Мл. модератор", 2: "Модератор", 3: "Ст. модератор", 4: "Мл. админ", 5: "Админ", 6: "Ст. админ", 7: "Гл. админ", 8: "Зам. осн.", 9: "Сооснователь", 10: "Основатель"}
        return self.data.get("bot_rank_names", {}).get(str(level), ranks.get(level, f"Ур. {level}"))
    
    def get_chat_rank_name(self, level):
        ranks = {0: "Пользователь", 1: "Мл. модер", 2: "Модер", 3: "Ст. модер", 4: "Мл. админ", 5: "Админ", 6: "Ст. админ", 7: "Гл. админ", 8: "Зам. вл.", 9: "Соосн.", 10: "Владелец"}
        return self.data.get("chat_rank_names", {}).get(str(level), ranks.get(level, f"Ур. {level}"))
    
    def get_agent_rank_name(self, level):
        ranks = {1: "Мл. агент", 2: "Агент", 3: "Ст. агент"}
        return self.data.get("agent_rank_names", {}).get(str(level), ranks.get(level, f"Ур. {level}"))
    
    def update_bot_rank_name(self, level, name):
        self.data["bot_rank_names"][str(level)] = name
        self.save_data()
    
    def update_agent_rank_name(self, level, name):
        self.data["agent_rank_names"][str(level)] = name
        self.save_data()
    
    def update_chat_rank_name(self, level, name):
        self.data["chat_rank_names"][str(level)] = name
        self.save_data()
    
    def get_rank_access(self, rank_type, level):
        result = []
        for s in self.data["access_settings"]:
            if s.get("type") == rank_type and s.get("min_level") == level:
                result.append(s.get("name"))
        return result
    
    def toggle_access(self, rank_type, level, function):
        for s in self.data["access_settings"]:
            if s["type"] == rank_type and s["name"] == function:
                if s.get("min_level") == level:
                    s["min_level"] = 999
                else:
                    s["min_level"] = level
                self.save_data()
                return
        self.data["access_settings"].append({"type": rank_type, "name": function, "min_level": level})
        self.save_data()
    
    def get_total_stats(self):
        return (len(self.data["users"]), len(self.data["chats"]), len(self.data["clans"]), len(self.data["bot_admins"]), len(self.data["support_agents"]), len(self.data["bot_blacklist"]), len(self.data.get("chat_messages", [])))
    
    def add_message(self, user_id, chat_id):
        self.data["chat_messages"].append({"user_id": user_id, "chat_id": chat_id, "message_time": datetime.now().isoformat()})
        self.save_data()
    
    def get_top_messages(self, chat_id, period='all'):
        messages = self.data.get("chat_messages", [])
        if period == 'day':
            cutoff = (datetime.now() - timedelta(days=1)).isoformat()
        elif period == 'week':
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        else:
            cutoff = '2000-01-01'
        filtered = [m for m in messages if m["chat_id"] == chat_id and m["message_time"] > cutoff]
        count = {}
        for m in filtered:
            count[m["user_id"]] = count.get(m["user_id"], 0) + 1
        top = sorted(count.items(), key=lambda x: x[1], reverse=True)[:10]
        result = []
        for uid, cnt in top:
            u = self.get_user(uid)
            result.append((uid, u["first_name"] if u else "Пользователь", cnt))
        return result
    
    def add_reward(self, user_id, from_id, text):
        self.data["rewards"].append({"user_id": user_id, "from_user_id": from_id, "text": text})
        self.save_data()
    
    def get_user_rewards(self, user_id):
        result = []
        for r in self.data.get("rewards", []):
            if r["user_id"] == user_id:
                u = self.get_user(r["from_user_id"])
                result.append({"text": r["text"], "from_name": u["first_name"] if u else "Пользователь"})
        return result
    
    def can_use_clan_bonus(self, user_id, clan_id):
        today = datetime.now().strftime("%Y-%m-%d")
        for u in self.data.get("clan_bonus_usage", []):
            if u.get("clan_id") == clan_id and u.get("user_id") == user_id and u.get("date") == today:
                return False
        return True
    
    def use_clan_bonus(self, user_id, clan_id):
        self.data["clan_bonus_usage"].append({"clan_id": clan_id, "user_id": user_id, "date": datetime.now().strftime("%Y-%m-%d")})
        self.save_data()


db = Database()

def check_bot_access(user_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    return function in db.get_rank_access('bot', db.get_bot_admin_level(user_id))

def check_chat_access(user_id, chat_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    level = db.get_bot_admin_level(user_id)
    if level >= 10:
        return True
    return function in db.get_rank_access('chat', level)

def check_agent_access(user_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    return function in db.get_rank_access('agent', db.get_agent_level(user_id))
    
#==================#
#2 ЧАСТЬ | Keyboards #
#==================#

class Keyboards:
    @staticmethod
    def main_menu():
        keyboard = [
            [InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("🛡 Клан", callback_data="clan_menu")],
            [InlineKeyboardButton("📊 Статистика чата", callback_data="chat_stats")],
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
            [InlineKeyboardButton("📊 Статистика чата", callback_data="chat_stats")],
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
            [InlineKeyboardButton("📊 Статистика чата", callback_data="chat_stats")],
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
            [InlineKeyboardButton("📊 Статистика чата", callback_data="chat_stats")],
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
            [InlineKeyboardButton("🚫 Черный список", callback_data="bot_blacklist")],
            [InlineKeyboardButton("⭐️ Выдать репутацию", callback_data="give_clan_rep")],
            [InlineKeyboardButton("📊 Статистика бота", callback_data="bot_stats")],
            [InlineKeyboardButton("📨 Рассылка", callback_data="broadcast_menu")],
            [InlineKeyboardButton("⚙️ Права рангов бота", callback_data="bot_rank_settings")],
            [InlineKeyboardButton("⚙️ Права агентов", callback_data="agent_settings")],
            [InlineKeyboardButton("📝 Ранги бота", callback_data="bot_rank_names")],
            [InlineKeyboardButton("📝 Ранги агентов", callback_data="agent_rank_names")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def chat_panel():
        keyboard = [
            [InlineKeyboardButton("⚙️ Права рангов чата", callback_data="chat_rank_settings")],
            [InlineKeyboardButton("👥 Админы чата", callback_data="chat_admins_list")],
            [InlineKeyboardButton("📝 Ранги чата", callback_data="chat_rank_names")],
            [InlineKeyboardButton("👋 Приветствие", callback_data="welcome_settings")],
            [InlineKeyboardButton("🚫 Антиспам", callback_data="antispam_settings")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def profile_menu():
        keyboard = [
            [InlineKeyboardButton("🏆 Награды", callback_data="my_rewards")],
            [InlineKeyboardButton("🎁 Выдать награду", callback_data="give_reward_btn")],
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
    def my_clan_menu(is_leader=False):
        keyboard = [
            [InlineKeyboardButton("👥 Участники", callback_data="clan_members")],
            [InlineKeyboardButton("✉️ Сообщения клана", callback_data="clan_messages")],
            [InlineKeyboardButton("⚔ Война", callback_data="declare_war")],
            [InlineKeyboardButton("📋 Заявки", callback_data="clan_requests")],
        ]
        if is_leader:
            keyboard.insert(0, [InlineKeyboardButton("⚙️ Настройки клана", callback_data="clan_settings")])
        else:
            keyboard.append([InlineKeyboardButton("🚪 Выйти", callback_data="leave_clan_btn")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def clan_settings_menu():
        keyboard = [
            [InlineKeyboardButton("🔒 Вход в клан", callback_data="clan_entry")],
            [InlineKeyboardButton("📩 Сообщение клану", callback_data="message_clan")],
            [InlineKeyboardButton("👑 Передать клан", callback_data="transfer_clan")],
            [InlineKeyboardButton("🗑 Удалить клан", callback_data="delete_clan")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_clan")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def clan_members_menu(is_leader=False):
        keyboard = []
        if is_leader:
            keyboard.append([InlineKeyboardButton("👤 Пригласить", callback_data="invite_member")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_clan")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def help_menu():
        keyboard = [
            [InlineKeyboardButton("❗️ Жалоба", callback_data="report_btn")],
            [InlineKeyboardButton("❓ Вопрос", callback_data="question_btn")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def admin_manage_menu():
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Удалить", callback_data="remove_admin")],
            [InlineKeyboardButton("🔄 Уровень", callback_data="change_admin_level")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def agent_manage_menu():
        keyboard = [
            [InlineKeyboardButton("➕ Добавить", callback_data="add_agent")],
            [InlineKeyboardButton("➖ Удалить", callback_data="remove_agent")],
            [InlineKeyboardButton("🔄 Уровень", callback_data="change_agent_level")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def clan_entry_menu():
        keyboard = [
            [InlineKeyboardButton("✅ Открыть", callback_data="entry_open")],
            [InlineKeyboardButton("❌ Закрыть", callback_data="entry_closed")],
            [InlineKeyboardButton("📝 Заявка", callback_data="entry_request")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_clan")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_start():
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]])

    @staticmethod
    def back_to_profile():
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_profile")]])

    @staticmethod
    def back_to_clan():
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_clan")]])

    @staticmethod
    def broadcast_menu():
        keyboard = [
            [InlineKeyboardButton("👥 В ЛС", callback_data="broadcast_pm")],
            [InlineKeyboardButton("💬 В чаты", callback_data="broadcast_chats")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def blacklist_menu():
        keyboard = [
            [InlineKeyboardButton("➕ В ЧС", callback_data="blacklist_add")],
            [InlineKeyboardButton("➖ Из ЧС", callback_data="blacklist_remove")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def welcome_settings_menu(enabled):
        status = "✅ Вкл" if enabled else "❌ Выкл"
        keyboard = [
            [InlineKeyboardButton(f"{status}", callback_data="toggle_welcome")],
            [InlineKeyboardButton("📝 Текст", callback_data="edit_welcome_text")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def antispam_settings_menu(enabled, seconds, max_msg):
        status = "✅ Вкл" if enabled else "❌ Выкл"
        keyboard = [
            [InlineKeyboardButton(f"{status}", callback_data="toggle_antispam")],
            [InlineKeyboardButton(f"⏱ {seconds}с", callback_data="change_antispam_interval")],
            [InlineKeyboardButton(f"📊 {max_msg}", callback_data="change_antispam_messages")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def antispam_interval_menu():
        keyboard = [
            [InlineKeyboardButton("1с", callback_data="set_antispam_1"), InlineKeyboardButton("3с", callback_data="set_antispam_3")],
            [InlineKeyboardButton("5с", callback_data="set_antispam_5"), InlineKeyboardButton("10с", callback_data="set_antispam_10")],
            [InlineKeyboardButton("30с", callback_data="set_antispam_30")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def antispam_messages_menu():
        keyboard = [
            [InlineKeyboardButton("3", callback_data="set_msg_3"), InlineKeyboardButton("5", callback_data="set_msg_5")],
            [InlineKeyboardButton("7", callback_data="set_msg_7"), InlineKeyboardButton("10", callback_data="set_msg_10")],
            [InlineKeyboardButton("15", callback_data="set_msg_15")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def chat_stats_menu():
        keyboard = [
            [InlineKeyboardButton("📊 Топ дня", callback_data="top_day")],
            [InlineKeyboardButton("📊 Топ недели", callback_data="top_week")],
            [InlineKeyboardButton("📊 Весь топ", callback_data="top_all")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def rank_levels_for_access(rank_type):
        keyboard = []
        max_level = 10 if rank_type in ['bot', 'chat'] else 3
        for i in range(1, max_level + 1, 2):
            row = [InlineKeyboardButton(str(i), callback_data=f"rank_access_{rank_type}_{i}")]
            if i + 1 <= max_level:
                row.append(InlineKeyboardButton(str(i+1), callback_data=f"rank_access_{rank_type}_{i+1}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def rank_access_menu(rank_type, level):
        keyboard = []
        if rank_type == 'bot':
            functions = [("manage_admins", "👥 Админы"), ("manage_agents", "🔰 Агенты"), ("blacklist", "🚫 ЧС"), ("give_clan_rep", "⭐️ Репутация"), ("view_chats", "🗂 Чаты"), ("stats", "📊 Статистика"), ("broadcast", "📨 Рассылка"), ("view_reports", "❗️ Жалобы"), ("give_reward", "🎁 Награды")]
        elif rank_type == 'agent':
            functions = [("view_questions", "❓ Вопросы"), ("answer_questions", "✉️ Ответы"), ("hstats", "📊 Статистика")]
        else:
            functions = [("ban", "🔨 Бан"), ("unban", "🔓 Разбан"), ("mute", "🔇 Мут"), ("unmute", "🔊 Размут"), ("warn", "⚠️ Варн"), ("unwarn", "✅ Анварн"), ("setadm", "👑 Админ"), ("welcome_settings", "👋 Приветствие"), ("antispam_settings", "🚫 Антиспам")]
        
        current = db.get_rank_access(rank_type, level)
        for func, name in functions:
            if func in current:
                keyboard.append([InlineKeyboardButton(f"✅ {name}", callback_data=f"toggle_access_{rank_type}_{level}_{func}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {name}", callback_data=f"toggle_access_{rank_type}_{level}_{func}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def rank_levels(rank_type):
        keyboard = []
        max_level = 10 if rank_type in ['bot', 'chat'] else 3
        for i in range(1, max_level + 1, 2):
            row = [InlineKeyboardButton(str(i), callback_data=f"rename_level_{i}")]
            if i + 1 <= max_level:
                row.append(InlineKeyboardButton(str(i+1), callback_data=f"rename_level_{i+1}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")])
        return InlineKeyboardMarkup(keyboard)
        
#==================#
#3 ЧАСТЬ | Handler      #
#==================#

class Handlers:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name)
        
        if db.is_blacklisted(user.id):
            await update.message.reply_text("❌ Вы в черном списке!")
            return
        
        bot_rank = db.get_bot_admin_level(user.id)
        is_owner = False
        
        if update.effective_chat.type != 'private':
            db.add_chat(update.effective_chat.id, update.effective_chat.title or "Чат")
            try:
                admins = await context.bot.get_chat_administrators(update.effective_chat.id)
                for a in admins:
                    if a.status == 'creator' and a.user.id == user.id:
                        is_owner = True
                        break
            except:
                pass
        
        rank_name = db.get_bot_rank_name(bot_rank)
        text = f"👋 Fluxy\n\n🆔 {user.id}\n🎖️ {rank_name}"
        
        if bot_rank >= 1 and is_owner:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu_with_both())
        elif bot_rank >= 1:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu_with_admin())
        elif is_owner:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu_with_chat_admin())
        else:
            await update.message.reply_text(text, reply_markup=Keyboards.main_menu())

    @staticmethod
    async def on_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message and update.message.new_chat_members:
            for m in update.message.new_chat_members:
                if m.id == context.bot.id:
                    db.add_chat(update.effective_chat.id, update.effective_chat.title or "Чат")
                    await update.message.reply_text("✅ Бот активирован!")

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        is_group = update.effective_chat.type != 'private'
        chat_id = update.effective_chat.id
        
        text = """📋 Команды:
━━━━━━━━━━━━━━━━

👤 Основные:
/start, /profile, /ping, /id

🛡 Кланы:
/clan, /clan_top, /clan_bonus
/create_clan, /join_clan, /leave_clan

📝 Прочее:
/report, /stats, /ask"""
        
        if is_group:
            mods = []
            if check_chat_access(user.id, chat_id, 'ban'): mods.append("/ban")
            if check_chat_access(user.id, chat_id, 'unban'): mods.append("/unban")
            if check_chat_access(user.id, chat_id, 'mute'): mods.append("/mute")
            if check_chat_access(user.id, chat_id, 'unmute'): mods.append("/unmute")
            if check_chat_access(user.id, chat_id, 'warn'): mods.append("/warn")
            if check_chat_access(user.id, chat_id, 'unwarn'): mods.append("/unwarn")
            if check_chat_access(user.id, chat_id, 'setadm'): mods.append("/setadm")
            if mods:
                text += "\n\n🔨 Модерация:\n" + ", ".join(mods)
        
        admins_cmds = []
        if check_bot_access(user.id, 'blacklist'): admins_cmds.extend(["/permban", "/unperm"])
        if check_bot_access(user.id, 'broadcast'): admins_cmds.append("/broadcast")
        if check_bot_access(user.id, 'view_reports'): admins_cmds.append("/reports")
        if check_bot_access(user.id, 'give_clan_rep'): admins_cmds.append("/give_rep")
        if admins_cmds:
            text += "\n\n⭐️ Админ:\n" + ", ".join(admins_cmds)
        
        if db.get_bot_admin_level(user.id) >= 10:
            text += "\n\n👑 Основатель:\n/rename_bot_rank, /rename_agent_rank, /rename_chat_rank, /backup"
        
        agent_cmds = []
        if check_agent_access(user.id, 'answer_questions'): agent_cmds.append("/answer_question")
        if check_agent_access(user.id, 'hstats'): agent_cmds.append("/hstats")
        if agent_cmds:
            text += "\n\n🔰 Агент:\n" + ", ".join(agent_cmds)
        
        await update.message.reply_text(text)

    @staticmethod
    async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.add_user(user.id, user.username, user.first_name)
        clan = db.get_user_clan(user.id)
        text = f"👤 Профиль\n\n🆔 {user.id}\n🎖️ {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}\n🛡️ {clan['name'] if clan else 'Нет'}"
        await update.message.reply_text(text, reply_markup=Keyboards.profile_menu())

    @staticmethod
    async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
        import time
        s = time.time()
        msg = await update.message.reply_text("Пинг...")
        await msg.edit_text(f"🏓 {round((time.time()-s)*1000)}ms")

    @staticmethod
    async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.reply_to_message:
            await update.message.reply_text(f"🆔 {update.message.reply_to_message.from_user.id}")
        else:
            await update.message.reply_text(f"🆔 {update.effective_user.id}")

    @staticmethod
    async def clan_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if not clan:
            await update.message.reply_text("❌ Нет клана!")
            return
        if not db.can_use_clan_bonus(user.id, clan['clan_id']):
            await update.message.reply_text("❌ Уже использовали!")
            return
        bonus = len(db.get_clan_members(clan['clan_id']))
        db.add_clan_rating(clan['clan_id'], bonus)
        db.use_clan_bonus(user.id, clan['clan_id'])
        await update.message.reply_text(f"✅ +{bonus} рейтинга!")

    @staticmethod
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте!")
            return
        t = update.message.reply_to_message.from_user
        db.add_user(t.id, t.username, t.first_name)
        clan = db.get_user_clan(t.id)
        ud = db.get_user(t.id)
        await update.message.reply_text(f"👤 {t.first_name}\n🆔 {t.id}\n🎖️ {db.get_bot_rank_name(db.get_bot_admin_level(t.id))}\n🛡️ {clan['name'] if clan else 'Нет'}\n⚠️ {ud.get('warnings', 0) if ud else 0}/3")

    @staticmethod
    async def create_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ /create_clan <имя>")
            return
        name = " ".join(context.args)
        if db.get_clan_by_name(name):
            await update.message.reply_text("❌ Существует!")
            return
        cid = db.create_clan(name, update.effective_user.id)
        await update.message.reply_text(f"✅ Клан «{name}» ID: {cid}")

    @staticmethod
    async def join_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ /join_clan <ID>")
            return
        try:
            cid = int(context.args[0])
            clan = db.get_clan_by_id(cid)
            if clan:
                db.join_clan(update.effective_user.id, cid)
                await update.message.reply_text(f"✅ Вступили в «{clan['name']}»!")
            else:
                await update.message.reply_text("❌ Не найден!")
        except:
            await update.message.reply_text("❌ Неверный ID!")

    @staticmethod
    async def leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        clan = db.get_user_clan(update.effective_user.id)
        if clan:
            db.leave_clan(update.effective_user.id)
            await update.message.reply_text("✅ Вы покинули клан!")
        else:
            await update.message.reply_text("❌ Нет клана!")

    @staticmethod
    async def clan_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if clan:
            is_leader = clan['leader_id'] == user.id
            text = f"🛡 {clan['name']}\n🏆 {clan['rating']}\n👥 {clan['total_members']}"
            await update.message.reply_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
        else:
            await update.message.reply_text("🛡 Кланы:", reply_markup=Keyboards.clan_menu())

    @staticmethod
    async def clan_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        clans = db.get_top_clans(15)
        text = "🏆 Топ кланов:\n\n"
        for i, c in enumerate(clans, 1):
            text += f"{i}. {c['name']} - {c['rating']}🏆\n"
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
        rid = db.add_report(update.effective_user.id, target.id, reason)
        await update.message.reply_text(f"✅ Жалоба #{rid} отправлена!")
        
        for admin in db.get_all_bot_admins():
            try:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Принять", callback_data=f"accept_report_{rid}"), InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_report_btn_{rid}")]])
                await context.bot.send_message(admin["user_id"], f"❗️ Жалоба #{rid}\nОт: {update.effective_user.first_name}\nНа: {target.first_name}\nПричина: {reason}", reply_markup=kb)
            except:
                pass

    @staticmethod
    async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Только в группе!")
            return
        if not check_chat_access(user.id, chat_id, 'ban'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте!")
            return
        target = update.message.reply_to_message.from_user
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            await update.message.reply_text(f"✅ {target.first_name} забанен!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_chat_access(update.effective_user.id, update.effective_chat.id, 'unban'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /unban <ID>")
            return
        try:
            await context.bot.unban_chat_member(update.effective_chat.id, int(context.args[0]))
            await update.message.reply_text("✅ Разбанен!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'mute'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте!")
            return
        target = update.message.reply_to_message.from_user
        try:
            await context.bot.restrict_chat_member(chat_id, target.id, can_send_messages=False)
            await update.message.reply_text(f"✅ {target.first_name} замучен!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_chat_access(update.effective_user.id, update.effective_chat.id, 'unmute'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте!")
            return
        target = update.message.reply_to_message.from_user
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, can_send_messages=True)
            await update.message.reply_text("✅ Размучен!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        if not check_chat_access(user.id, chat_id, 'warn'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте!")
            return
        target = update.message.reply_to_message.from_user
        for u in db.data["users"]:
            if u["user_id"] == target.id:
                u["warnings"] = u.get("warnings", 0) + 1
                db.save_data()
                await update.message.reply_text(f"⚠️ {target.first_name}: {u['warnings']}/3")
                return

    @staticmethod
    async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_chat_access(update.effective_user.id, update.effective_chat.id, 'unwarn'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте!")
            return
        target = update.message.reply_to_message.from_user
        for u in db.data["users"]:
            if u["user_id"] == target.id and u.get("warnings", 0) > 0:
                u["warnings"] -= 1
                db.save_data()
                await update.message.reply_text("✅ Снято!")
                return

    @staticmethod
    async def setadm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_chat_access(update.effective_user.id, update.effective_chat.id, 'setadm'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /setadm <ID> <уровень>")
            return
        try:
            db.add_bot_admin(int(context.args[0]), int(context.args[1]), update.effective_user.id)
            await update.message.reply_text("✅ Назначен!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def permban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_bot_access(update.effective_user.id, 'blacklist'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /permban <ID>")
            return
        try:
            db.add_to_blacklist(int(context.args[0]), "Не указана", update.effective_user.id)
            await update.message.reply_text("✅ В ЧС!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def unperm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_bot_access(update.effective_user.id, 'blacklist'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /unperm <ID>")
            return
        try:
            db.remove_from_blacklist(int(context.args[0]))
            await update.message.reply_text("✅ Из ЧС!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_bot_access(update.effective_user.id, 'broadcast'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if not context.args:
            await update.message.reply_text("❌ /broadcast <текст>")
            return
        text = " ".join(context.args)
        sent = 0
        for uid in db.get_all_users():
            try:
                await context.bot.send_message(uid, f"📨 {text}")
                sent += 1
            except:
                pass
        await update.message.reply_text(f"✅ {sent}")

    @staticmethod
    async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_bot_access(update.effective_user.id, 'view_reports'):
            await update.message.reply_text("❌ Нет прав!")
            return
        reports = db.get_pending_reports()
        if not reports:
            await update.message.reply_text("✅ Нет жалоб!")
            return
        text = "❗️ Жалобы:\n\n"
        for r in reports:
            text += f"#{r['report_id']} - {r['reason']}\n"
        await update.message.reply_text(text)

    @staticmethod
    async def answer_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_bot_access(update.effective_user.id, 'view_reports'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /answer_report <ID> <ответ>")
            return
        try:
            rid = int(context.args[0])
            answer = " ".join(context.args[1:])
            db.update_report_status(rid, 'answered', update.effective_user.id)
            for r in db.data["reports"]:
                if r["report_id"] == rid:
                    await context.bot.send_message(r["user_id"], f"✅ Ответ: {answer}")
                    break
            await update.message.reply_text("✅ Отправлено!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def reject_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ /reject_report <ID>")
            return
        try:
            db.update_report_status(int(context.args[0]), 'rejected', update.effective_user.id)
            await update.message.reply_text("✅ Отклонено!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_agent_access(update.effective_user.id, 'answer_questions'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /answer_question <ID> <ответ>")
            return
        try:
            qid = int(context.args[0])
            answer = " ".join(context.args[1:])
            db.update_question_status(qid, 'answered', update.effective_user.id, answer)
            for q in db.data["questions"]:
                if q["question_id"] == qid:
                    await context.bot.send_message(q["user_id"], f"❓ Ответ: {answer}")
                    break
            await update.message.reply_text("✅ Отправлено!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def reject_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ /reject_question <ID>")
            return
        try:
            db.update_question_status(int(context.args[0]), 'rejected', update.effective_user.id)
            await update.message.reply_text("✅ Отклонено!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def astats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"📊 Уровень: {db.get_bot_admin_level(update.effective_user.id)}")

    @staticmethod
    async def hstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(f"📊 Уровень: {db.get_agent_level(update.effective_user.id)}")

    @staticmethod
    async def give_rep(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not check_bot_access(update.effective_user.id, 'give_clan_rep'):
            await update.message.reply_text("❌ Нет прав!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /give_rep <ID> <кол-во>")
            return
        try:
            db.add_clan_rating(int(context.args[0]), int(context.args[1]))
            await update.message.reply_text("✅ Выдано!")
        except:
            await update.message.reply_text("❌ Ошибка!")

    @staticmethod
    async def rename_bot_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if db.get_bot_admin_level(update.effective_user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /rename_bot_rank <ур> <имя>")
            return
        db.update_bot_rank_name(int(context.args[0]), " ".join(context.args[1:]))
        await update.message.reply_text("✅ Готово!")

    @staticmethod
    async def rename_agent_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if db.get_bot_admin_level(update.effective_user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /rename_agent_rank <ур> <имя>")
            return
        db.update_agent_rank_name(int(context.args[0]), " ".join(context.args[1:]))
        await update.message.reply_text("✅ Готово!")

    @staticmethod
    async def rename_chat_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if db.get_bot_admin_level(update.effective_user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /rename_chat_rank <ур> <имя>")
            return
        db.update_chat_rank_name(int(context.args[0]), " ".join(context.args[1:]))
        await update.message.reply_text("✅ Готово!")

    @staticmethod
    async def accept_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ /accept_request <ID>")
            return
        db.update_clan_request(int(context.args[0]), 'accepted')
        await update.message.reply_text("✅ Принято!")

    @staticmethod
    async def reject_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ /reject_request <ID>")
            return
        db.update_clan_request(int(context.args[0]), 'rejected')
        await update.message.reply_text("✅ Отклонено!")

    @staticmethod
    async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.args:
            await update.message.reply_text("❌ /ask <текст>")
            return
        qid = db.add_question(update.effective_user.id, " ".join(context.args))
        await update.message.reply_text("✅ Вопрос отправлен!")
        for agent in db.get_all_agents():
            try:
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Принять", callback_data=f"accept_question_{qid}"), InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_question_btn_{qid}")]])
                await context.bot.send_message(agent["user_id"], f"❓ Вопрос: {' '.join(context.args)}", reply_markup=kb)
            except:
                pass

    @staticmethod
    async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if db.get_bot_admin_level(update.effective_user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        db.save_data()
        await update.message.reply_text("✅ Сохранено!")

#======================#
#4 ЧАСТЬ | Button_Handler  #
#======================#

@staticmethod
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    chat_id = update.effective_chat.id
    
    if data == "back_to_start":
        bot_rank = db.get_bot_admin_level(user.id)
        if bot_rank >= 1:
            await query.message.edit_text("Главное меню Fluxy", reply_markup=Keyboards.main_menu_with_admin())
        else:
            await query.message.edit_text("Главное меню Fluxy", reply_markup=Keyboards.main_menu())
        return ConversationHandler.END
    
    elif data == "back_to_profile":
        clan = db.get_user_clan(user.id)
        text = f"👤 Профиль\n\n🆔 {user.id}\n🎖️ {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}\n🛡️ {clan['name'] if clan else 'Нет'}"
        await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
        return ConversationHandler.END
    
    elif data == "back_to_clan":
        clan = db.get_user_clan(user.id)
        if clan:
            is_leader = clan['leader_id'] == user.id
            text = f"🛡 {clan['name']}\n🏆 {clan['rating']}\n👥 {clan['total_members']}"
            await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
        return ConversationHandler.END
    
    elif data == "profile":
        clan = db.get_user_clan(user.id)
        text = f"👤 Профиль\n\n🆔 {user.id}\n🎖️ {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}\n🛡️ {clan['name'] if clan else 'Нет'}"
        await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
    
    elif data == "my_rewards":
        rewards = db.get_user_rewards(user.id)
        text = "🏆 Награды:\n\n"
        if not rewards:
            text += "Нет наград"
        for r in rewards:
            text += f"🎁 {r['text']}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.back_to_profile())
    
    elif data == "give_reward_btn":
        context.user_data['giving_reward'] = True
        await query.message.reply_text("Отправьте ID:")
        return WAITING_FOR_REWARD_USER
    
    elif data == "chat_stats":
        await query.message.edit_text("📊 Статистика:", reply_markup=Keyboards.chat_stats_menu())
    
    elif data == "top_day":
        top = db.get_top_messages(chat_id, 'day')
        text = "📊 Топ дня:\n━━━━━━━━━━━━━━━━\n\n"
        if not top:
            text += "Нет данных"
        for i, (uid, name, cnt) in enumerate(top, 1):
            text += f"{i}. {name}\n💬 {cnt}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
    
    elif data == "top_week":
        top = db.get_top_messages(chat_id, 'week')
        text = "📊 Топ недели:\n━━━━━━━━━━━━━━━━\n\n"
        if not top:
            text += "Нет данных"
        for i, (uid, name, cnt) in enumerate(top, 1):
            text += f"{i}. {name}\n💬 {cnt}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
    
    elif data == "top_all":
        top = db.get_top_messages(chat_id, 'all')
        text = "📊 Весь топ:\n━━━━━━━━━━━━━━━━\n\n"
        if not top:
            text += "Нет данных"
        for i, (uid, name, cnt) in enumerate(top, 1):
            text += f"{i}. {name}\n💬 {cnt}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
    
    elif data == "clan_menu":
        clan = db.get_user_clan(user.id)
        if clan:
            is_leader = clan['leader_id'] == user.id
            text = f"🛡 {clan['name']}\n🏆 {clan['rating']}\n👥 {clan['total_members']}"
            await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
        else:
            await query.message.edit_text("🛡 Кланы:", reply_markup=Keyboards.clan_menu())
    
    elif data == "clan_settings":
        clan = db.get_user_clan(user.id)
        if clan and clan['leader_id'] == user.id:
            await query.message.edit_text("⚙️ Настройки:", reply_markup=Keyboards.clan_settings_menu())
    
    elif data == "clan_members":
        clan = db.get_user_clan(user.id)
        if clan:
            is_leader = clan['leader_id'] == user.id
            members = db.get_clan_members(clan['clan_id'])
            text = "👥 Участники:\n\n"
            for m in members:
                text += f"👤 {m['first_name']}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.clan_members_menu(is_leader))
    
    elif data == "clan_requests":
        clan = db.get_user_clan(user.id)
        if clan:
            requests = db.get_clan_requests(clan['clan_id'])
            text = "📋 Заявки:\n\n"
            if not requests:
                text += "Нет"
            for r in requests:
                text += f"🆔 {r['request_id']}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_clan())
    
    elif data == "clan_entry":
        await query.message.edit_text("🔒 Вход:", reply_markup=Keyboards.clan_entry_menu())
    
    elif data == "entry_open":
        clan = db.get_user_clan(user.id)
        db.update_clan_entry_type(clan['clan_id'], 'open')
        await query.message.reply_text("✅ Открыт!")
    
    elif data == "entry_closed":
        clan = db.get_user_clan(user.id)
        db.update_clan_entry_type(clan['clan_id'], 'closed')
        await query.message.reply_text("✅ Закрыт!")
    
    elif data == "entry_request":
        clan = db.get_user_clan(user.id)
        db.update_clan_entry_type(clan['clan_id'], 'request')
        await query.message.reply_text("✅ По заявкам!")
    
    elif data == "declare_war":
        context.user_data['war_clan_id'] = True
        await query.message.reply_text("ID врага:")
        return WAITING_FOR_WAR_CLAN_ID
    
    elif data == "message_clan":
        context.user_data['clan_msg_to'] = True
        await query.message.reply_text("ID клана:")
        return WAITING_FOR_CLAN_MSG_CLAN
    
    elif data == "invite_member":
        context.user_data['waiting_invite'] = True
        await query.message.reply_text("ID:")
        return WAITING_FOR_INVITE_USER
    
    elif data == "transfer_clan":
        context.user_data['transfer_clan'] = True
        await query.message.reply_text("ID нового лидера:")
        return WAITING_FOR_TRANSFER_CLAN
    
    elif data == "delete_clan":
        clan = db.get_user_clan(user.id)
        if clan:
            db.data["clans"] = [c for c in db.data["clans"] if c["clan_id"] != clan["clan_id"]]
            for u in db.data["users"]:
                if u.get("clan_id") == clan["clan_id"]:
                    u["clan_id"] = None
            db.save_data()
            await query.message.edit_text("✅ Удален!", reply_markup=Keyboards.clan_menu())
    
    elif data == "leave_clan_btn":
        db.leave_clan(user.id)
        await query.message.edit_text("✅ Вы вышли!", reply_markup=Keyboards.clan_menu())
        return ConversationHandler.END
    
    elif data == "find_clan_btn":
        context.user_data['waiting_clan_id'] = True
        await query.message.reply_text("ID клана:")
        return WAITING_FOR_CLAN_ID
    
    elif data == "create_clan_btn":
        await query.message.reply_text("/create_clan <имя>")
    
    elif data == "clan_list_btn":
        await query.message.reply_text("/clan_top")
    
    elif data == "admin_panel":
        await query.message.edit_text("⭐️ Админ панель:", reply_markup=Keyboards.admin_panel())
    
    elif data == "admins_list":
        admins = db.get_all_bot_admins()
        text = "👥 Админы:\n\n"
        for a in admins:
            text += f"👤 {a['first_name']}\n📊 {a['level']}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.admin_manage_menu())
    
    elif data == "add_admin":
        context.user_data['action'] = 'add_admin'
        await query.message.reply_text("ID:")
        return WAITING_FOR_ADMIN_ID
    
    elif data == "remove_admin":
        context.user_data['action'] = 'remove_admin'
        await query.message.reply_text("ID:")
        return WAITING_FOR_ADMIN_ID
    
    elif data == "change_admin_level":
        context.user_data['action'] = 'change_admin_level'
        await query.message.reply_text("ID:")
        return WAITING_FOR_ADMIN_ID
    
    elif data == "agents_manage":
        agents = db.get_all_agents()
        text = "🔰 Агенты:\n\n"
        for a in agents:
            text += f"👤 {a['first_name']}\n📊 {a['level']}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.agent_manage_menu())
    
    elif data == "add_agent":
        context.user_data['action'] = 'add_agent'
        await query.message.reply_text("ID:")
        return WAITING_FOR_AGENT_ID
    
    elif data == "remove_agent":
        context.user_data['action'] = 'remove_agent'
        await query.message.reply_text("ID:")
        return WAITING_FOR_AGENT_ID
    
    elif data == "change_agent_level":
        context.user_data['action'] = 'change_agent_level'
        await query.message.reply_text("ID:")
        return WAITING_FOR_AGENT_ID
    
    elif data == "bot_blacklist":
        bl = db.get_blacklist()
        text = "🚫 ЧС:\n\n"
        for b in bl:
            text += f"🆔 {b['user_id']}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.blacklist_menu())
    
    elif data == "blacklist_add":
        context.user_data['action'] = 'blacklist_add'
        await query.message.reply_text("ID:")
        return WAITING_FOR_BLACKLIST_ID
    
    elif data == "blacklist_remove":
        context.user_data['action'] = 'blacklist_remove'
        await query.message.reply_text("ID:")
        return WAITING_FOR_BLACKLIST_ID
    
    elif data == "broadcast_menu":
        await query.message.edit_text("📨 Рассылка:", reply_markup=Keyboards.broadcast_menu())
    
    elif data == "broadcast_pm":
        context.user_data['broadcast_type'] = 'pm'
        await query.message.reply_text("Текст:")
        return WAITING_FOR_BROADCAST_TEXT
    
    elif data == "broadcast_chats":
        context.user_data['broadcast_type'] = 'chats'
        await query.message.reply_text("Текст:")
        return WAITING_FOR_BROADCAST_TEXT
    
    elif data == "bot_stats":
        u, c, cl, a, ag, bl, m = db.get_total_stats()
        text = f"📊 Статистика:\n\n👥 {u}\n💬 {c}\n🛡 {cl}\n👑 {a}\n🔰 {ag}\n🚫 {bl}\n📨 {m}"
        await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
    
    elif data == "bot_rank_settings":
        await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('bot'))
    
    elif data == "agent_settings":
        await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('agent'))
    
    elif data == "chat_rank_settings":
        await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('chat'))
    
    elif data.startswith("rank_access_"):
        parts = data.split("_")
        rt = parts[2]
        lvl = int(parts[3])
        await query.message.edit_text(f"Права уровня {lvl}:", reply_markup=Keyboards.rank_access_menu(rt, lvl))
    
    elif data.startswith("toggle_access_"):
        parts = data.split("_")
        rt = parts[2]
        lvl = int(parts[3])
        func = parts[4]
        db.toggle_access(rt, lvl, func)
        await query.message.edit_text(f"Права уровня {lvl}:", reply_markup=Keyboards.rank_access_menu(rt, lvl))
    
    elif data == "bot_rank_names":
        context.user_data['rename_type'] = 'bot'
        await query.message.edit_text("Уровень:", reply_markup=Keyboards.rank_levels('bot'))
    
    elif data == "agent_rank_names":
        context.user_data['rename_type'] = 'agent'
        await query.message.edit_text("Уровень:", reply_markup=Keyboards.rank_levels('agent'))
    
    elif data == "chat_rank_names":
        context.user_data['rename_type'] = 'chat'
        await query.message.edit_text("Уровень:", reply_markup=Keyboards.rank_levels('chat'))
    
    elif data.startswith("rename_level_"):
        lvl = int(data.replace("rename_level_", ""))
        context.user_data['rename_level'] = lvl
        await query.message.reply_text("Новое имя:")
        return WAITING_FOR_RENAME
    
    elif data == "chat_panel":
        await query.message.edit_text("👑 Чат панель:", reply_markup=Keyboards.chat_panel())
    
    elif data == "chat_admins_list":
        await query.message.edit_text("👥 Админы чата", reply_markup=Keyboards.back_to_start())
    
    elif data == "welcome_settings":
        ws = db.get_welcome_settings(chat_id)
        await query.message.edit_text("👋 Приветствие:", reply_markup=Keyboards.welcome_settings_menu(ws[0] if ws else 0))
    
    elif data == "toggle_welcome":
        ws = db.get_welcome_settings(chat_id)
        db.enable_welcome(chat_id, not (ws[0] if ws else 0))
        ws = db.get_welcome_settings(chat_id)
        await query.message.edit_text("👋 Приветствие:", reply_markup=Keyboards.welcome_settings_menu(ws[0] if ws else 0))
    
    elif data == "edit_welcome_text":
        context.user_data['editing_welcome'] = chat_id
        await query.message.reply_text("Текст:")
        return WAITING_FOR_WELCOME_TEXT
    
    elif data == "antispam_settings":
        aset = db.get_antispam_settings(chat_id)
        await query.message.edit_text("🚫 Антиспам:", reply_markup=Keyboards.antispam_settings_menu(aset[0] if aset else 0, aset[1] if aset else 5, db.get_antispam_max_messages(chat_id)))
    
    elif data == "toggle_antispam":
        aset = db.get_antispam_settings(chat_id)
        db.enable_antispam(chat_id, not (aset[0] if aset else 0))
        aset = db.get_antispam_settings(chat_id)
        await query.message.edit_text("🚫 Антиспам:", reply_markup=Keyboards.antispam_settings_menu(aset[0] if aset else 0, aset[1] if aset else 5, db.get_antispam_max_messages(chat_id)))
    
    elif data == "change_antispam_interval":
        await query.message.edit_text("⏱ Интервал:", reply_markup=Keyboards.antispam_interval_menu())
    
    elif data == "change_antispam_messages":
        await query.message.edit_text("📊 Макс:", reply_markup=Keyboards.antispam_messages_menu())
    
    elif data.startswith("set_antispam_"):
        sec = int(data.replace("set_antispam_", ""))
        db.set_antispam_seconds(chat_id, sec)
        await query.message.edit_text(f"✅ {sec}с", reply_markup=Keyboards.back_to_start())
    
    elif data.startswith("set_msg_"):
        mx = int(data.replace("set_msg_", ""))
        db.set_antispam_max_messages(chat_id, mx)
        await query.message.edit_text(f"✅ {mx}", reply_markup=Keyboards.back_to_start())
    
    elif data == "help_menu":
        await query.message.edit_text("🆘 Помощь:", reply_markup=Keyboards.help_menu())
    
    elif data == "report_btn":
        await query.message.reply_text("Ответьте на сообщение и /report <причина>")
    
    elif data == "question_btn":
        context.user_data['asking_question'] = True
        await query.message.reply_text("Задайте вопрос:")
        return WAITING_FOR_QUESTION
    
    elif data.startswith("accept_report_"):
        rid = int(data.replace("accept_report_", ""))
        context.user_data['answering_report'] = rid
        await query.message.reply_text("Ответ:")
        return WAITING_FOR_REPORT_ANSWER
    
    elif data.startswith("reject_report_btn_"):
        rid = int(data.replace("reject_report_btn_", ""))
        db.update_report_status(rid, 'rejected', user.id)
        await query.message.edit_text("✅ Отклонено!")
        return ConversationHandler.END
    
    elif data.startswith("accept_question_"):
        qid = int(data.replace("accept_question_", ""))
        context.user_data['answering_question'] = qid
        await query.message.reply_text("Ответ:")
        return WAITING_FOR_QUESTION_ANSWER
    
    elif data.startswith("reject_question_btn_"):
        qid = int(data.replace("reject_question_btn_", ""))
        db.update_question_status(qid, 'rejected', user.id)
        await query.message.edit_text("✅ Отклонено!")
        return ConversationHandler.END
    
    elif data == "commands_menu":
        await query.message.edit_text("📋 /start /help /profile /clan", reply_markup=Keyboards.back_to_start())
    
    elif data == "agents_list":
        agents = db.get_all_agents()
        text = "🔰 Агенты:\n\n"
        for a in agents:
            text += f"👤 {a['first_name']}\n━━━━━━━━━━━━━━━━\n"
        await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
    
    return ConversationHandler.END
                
#==================#
#5 ЧАСТЬ | Main           #
#==================#

def main():
    print("🤖 Запуск Fluxy...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Локальные обработчики
    async def welcome_handler(update, context):
        if not update.message or not update.message.new_chat_members:
            return
        chat_id = update.effective_chat.id
        ws = db.get_welcome_settings(chat_id)
        for m in update.message.new_chat_members:
            if m.is_bot:
                continue
            if ws and ws[0] == 1:
                text = ws[1] or "Добро пожаловать!"
                text = text.replace("{name}", m.first_name or "Гость")
                await update.message.reply_text(text)
    
    async def antispam_handler(update, context):
        user = update.effective_user
        chat_id = update.effective_chat.id
        db.add_user(user.id, user.username, user.first_name)
        db.add_message(user.id, chat_id)
    
    async def backup_handler(update, context):
        if db.get_bot_admin_level(update.effective_user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        db.save_data()
        await update.message.reply_text("✅ Сохранено!")
    
    async def button_callback(update, context):
        query = update.callback_query
        await query.answer()
        data = query.data
        user = query.from_user
        chat_id = update.effective_chat.id
        
        if data == "back_to_start":
            bot_rank = db.get_bot_admin_level(user.id)
            if bot_rank >= 1:
                await query.message.edit_text("Главное меню", reply_markup=Keyboards.main_menu_with_admin())
            else:
                await query.message.edit_text("Главное меню", reply_markup=Keyboards.main_menu())
            return ConversationHandler.END
        
        elif data == "profile":
            clan = db.get_user_clan(user.id)
            text = f"👤 Профиль\n\n🆔 {user.id}\n🎖️ {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}\n🛡️ {clan['name'] if clan else 'Нет'}"
            await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
        
        elif data == "back_to_profile":
            clan = db.get_user_clan(user.id)
            text = f"👤 Профиль\n\n🆔 {user.id}"
            await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
            return ConversationHandler.END
        
        elif data == "clan_menu":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan['leader_id'] == user.id
                text = f"🛡 {clan['name']}\n🏆 {clan['rating']}\n👥 {clan['total_members']}"
                await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
            else:
                await query.message.edit_text("🛡 Кланы:", reply_markup=Keyboards.clan_menu())
        
        elif data == "back_to_clan":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan['leader_id'] == user.id
                text = f"🛡 {clan['name']}"
                await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
            return ConversationHandler.END
        
        elif data == "help_menu":
            await query.message.edit_text("🆘 Помощь:", reply_markup=Keyboards.help_menu())
        
        elif data == "report_btn":
            await query.message.reply_text("Ответьте на сообщение и /report <причина>")
        
        elif data == "question_btn":
            context.user_data['asking_question'] = True
            await query.message.reply_text("Задайте вопрос:")
            return WAITING_FOR_QUESTION
        
        elif data == "commands_menu":
            await query.message.edit_text("📋 /start /help /profile /clan", reply_markup=Keyboards.back_to_start())
        
        elif data == "agents_list":
            agents = db.get_all_agents()
            text = "🔰 Агенты:\n\n"
            for a in agents:
                text += f"👤 {a['first_name']}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "chat_stats":
            await query.message.edit_text("📊 Статистика:", reply_markup=Keyboards.chat_stats_menu())
        
        elif data == "top_day":
            top = db.get_top_messages(chat_id, 'day')
            text = "📊 Топ дня:\n\n"
            for i, (uid, name, cnt) in enumerate(top, 1):
                text += f"{i}. {name} - {cnt}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "top_week":
            top = db.get_top_messages(chat_id, 'week')
            text = "📊 Топ недели:\n\n"
            for i, (uid, name, cnt) in enumerate(top, 1):
                text += f"{i}. {name} - {cnt}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "top_all":
            top = db.get_top_messages(chat_id, 'all')
            text = "📊 Весь топ:\n\n"
            for i, (uid, name, cnt) in enumerate(top, 1):
                text += f"{i}. {name} - {cnt}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "admin_panel":
            await query.message.edit_text("⭐️ Админ панель:", reply_markup=Keyboards.admin_panel())
        
        elif data == "admins_list":
            admins = db.get_all_bot_admins()
            text = "👥 Админы:\n\n"
            for a in admins:
                text += f"👤 {a['first_name']} - {a['level']}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.admin_manage_menu())
        
        elif data == "add_admin":
            context.user_data['action'] = 'add_admin'
            await query.message.reply_text("ID:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "remove_admin":
            context.user_data['action'] = 'remove_admin'
            await query.message.reply_text("ID:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "change_admin_level":
            context.user_data['action'] = 'change_admin_level'
            await query.message.reply_text("ID:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "agents_manage":
            agents = db.get_all_agents()
            text = "🔰 Агенты:\n\n"
            for a in agents:
                text += f"👤 {a['first_name']} - {a['level']}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.agent_manage_menu())
        
        elif data == "add_agent":
            context.user_data['action'] = 'add_agent'
            await query.message.reply_text("ID:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "remove_agent":
            context.user_data['action'] = 'remove_agent'
            await query.message.reply_text("ID:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "change_agent_level":
            context.user_data['action'] = 'change_agent_level'
            await query.message.reply_text("ID:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "bot_blacklist":
            bl = db.get_blacklist()
            text = "🚫 ЧС:\n\n"
            for b in bl:
                text += f"🆔 {b['user_id']}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.blacklist_menu())
        
        elif data == "blacklist_add":
            context.user_data['action'] = 'blacklist_add'
            await query.message.reply_text("ID:")
            return WAITING_FOR_BLACKLIST_ID
        
        elif data == "blacklist_remove":
            context.user_data['action'] = 'blacklist_remove'
            await query.message.reply_text("ID:")
            return WAITING_FOR_BLACKLIST_ID
        
        elif data == "broadcast_menu":
            await query.message.edit_text("📨 Рассылка:", reply_markup=Keyboards.broadcast_menu())
        
        elif data == "broadcast_pm":
            context.user_data['broadcast_type'] = 'pm'
            await query.message.reply_text("Текст:")
            return WAITING_FOR_BROADCAST_TEXT
        
        elif data == "broadcast_chats":
            context.user_data['broadcast_type'] = 'chats'
            await query.message.reply_text("Текст:")
            return WAITING_FOR_BROADCAST_TEXT
        
        elif data == "bot_stats":
            u, c, cl, a, ag, bl, m = db.get_total_stats()
            text = f"📊 Статистика:\n\n👥 {u}\n💬 {c}\n🛡 {cl}\n👑 {a}\n🔰 {ag}\n🚫 {bl}\n📨 {m}"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "bot_rank_settings":
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('bot'))
        
        elif data == "agent_settings":
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('agent'))
        
        elif data == "chat_rank_settings":
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('chat'))
        
        elif data.startswith("rank_access_"):
            parts = data.split("_")
            rt = parts[2]
            lvl = int(parts[3])
            await query.message.edit_text(f"Права уровня {lvl}:", reply_markup=Keyboards.rank_access_menu(rt, lvl))
        
        elif data.startswith("toggle_access_"):
            parts = data.split("_")
            rt = parts[2]
            lvl = int(parts[3])
            func = parts[4]
            db.toggle_access(rt, lvl, func)
            await query.message.edit_text(f"Права уровня {lvl}:", reply_markup=Keyboards.rank_access_menu(rt, lvl))
        
        elif data == "bot_rank_names":
            context.user_data['rename_type'] = 'bot'
            await query.message.edit_text("Уровень:", reply_markup=Keyboards.rank_levels('bot'))
        
        elif data == "agent_rank_names":
            context.user_data['rename_type'] = 'agent'
            await query.message.edit_text("Уровень:", reply_markup=Keyboards.rank_levels('agent'))
        
        elif data == "chat_rank_names":
            context.user_data['rename_type'] = 'chat'
            await query.message.edit_text("Уровень:", reply_markup=Keyboards.rank_levels('chat'))
        
        elif data.startswith("rename_level_"):
            lvl = int(data.replace("rename_level_", ""))
            context.user_data['rename_level'] = lvl
            await query.message.reply_text("Новое имя:")
            return WAITING_FOR_RENAME
        
        elif data == "chat_panel":
            await query.message.edit_text("👑 Чат панель:", reply_markup=Keyboards.chat_panel())
        
        elif data == "welcome_settings":
            ws = db.get_welcome_settings(chat_id)
            await query.message.edit_text("👋 Приветствие:", reply_markup=Keyboards.welcome_settings_menu(ws[0] if ws else 0))
        
        elif data == "toggle_welcome":
            ws = db.get_welcome_settings(chat_id)
            db.enable_welcome(chat_id, not (ws[0] if ws else 0))
            ws = db.get_welcome_settings(chat_id)
            await query.message.edit_text("👋 Приветствие:", reply_markup=Keyboards.welcome_settings_menu(ws[0] if ws else 0))
        
        elif data == "edit_welcome_text":
            context.user_data['editing_welcome'] = chat_id
            await query.message.reply_text("Текст:")
            return WAITING_FOR_WELCOME_TEXT
        
        elif data == "antispam_settings":
            aset = db.get_antispam_settings(chat_id)
            await query.message.edit_text("🚫 Антиспам:", reply_markup=Keyboards.antispam_settings_menu(aset[0] if aset else 0, aset[1] if aset else 5, db.get_antispam_max_messages(chat_id)))
        
        elif data == "toggle_antispam":
            aset = db.get_antispam_settings(chat_id)
            db.enable_antispam(chat_id, not (aset[0] if aset else 0))
            aset = db.get_antispam_settings(chat_id)
            await query.message.edit_text("🚫 Антиспам:", reply_markup=Keyboards.antispam_settings_menu(aset[0] if aset else 0, aset[1] if aset else 5, db.get_antispam_max_messages(chat_id)))
        
        elif data == "change_antispam_interval":
            await query.message.edit_text("⏱ Интервал:", reply_markup=Keyboards.antispam_interval_menu())
        
        elif data == "change_antispam_messages":
            await query.message.edit_text("📊 Макс:", reply_markup=Keyboards.antispam_messages_menu())
        
        elif data.startswith("set_antispam_"):
            sec = int(data.replace("set_antispam_", ""))
            db.set_antispam_seconds(chat_id, sec)
            await query.message.edit_text(f"✅ {sec}с", reply_markup=Keyboards.back_to_start())
        
        elif data.startswith("set_msg_"):
            mx = int(data.replace("set_msg_", ""))
            db.set_antispam_max_messages(chat_id, mx)
            await query.message.edit_text(f"✅ {mx}", reply_markup=Keyboards.back_to_start())
        
        elif data.startswith("accept_report_"):
            rid = int(data.replace("accept_report_", ""))
            context.user_data['answering_report'] = rid
            await query.message.reply_text("Ответ:")
            return WAITING_FOR_REPORT_ANSWER
        
        elif data.startswith("reject_report_btn_"):
            rid = int(data.replace("reject_report_btn_", ""))
            db.update_report_status(rid, 'rejected', user.id)
            await query.message.edit_text("✅ Отклонено!")
            return ConversationHandler.END
        
        elif data.startswith("accept_question_"):
            qid = int(data.replace("accept_question_", ""))
            context.user_data['answering_question'] = qid
            await query.message.reply_text("Ответ:")
            return WAITING_FOR_QUESTION_ANSWER
        
        elif data.startswith("reject_question_btn_"):
            qid = int(data.replace("reject_question_btn_", ""))
            db.update_question_status(qid, 'rejected', user.id)
            await query.message.edit_text("✅ Отклонено!")
            return ConversationHandler.END
        
        elif data == "leave_clan_btn":
            db.leave_clan(user.id)
            await query.message.edit_text("✅ Вы вышли!", reply_markup=Keyboards.clan_menu())
            return ConversationHandler.END
        
        elif data == "delete_clan":
            clan = db.get_user_clan(user.id)
            if clan:
                db.data["clans"] = [c for c in db.data["clans"] if c["clan_id"] != clan["clan_id"]]
                for u in db.data["users"]:
                    if u.get("clan_id") == clan["clan_id"]:
                        u["clan_id"] = None
                db.save_data()
                await query.message.edit_text("✅ Удален!", reply_markup=Keyboards.clan_menu())
        
        elif data == "transfer_clan":
            context.user_data['transfer_clan'] = True
            await query.message.reply_text("ID нового лидера:")
            return WAITING_FOR_TRANSFER_CLAN
        
        elif data == "invite_member":
            context.user_data['waiting_invite'] = True
            await query.message.reply_text("ID:")
            return WAITING_FOR_INVITE_USER
        
        elif data == "message_clan":
            context.user_data['clan_msg_to'] = True
            await query.message.reply_text("ID клана:")
            return WAITING_FOR_CLAN_MSG_CLAN
        
        elif data == "declare_war":
            context.user_data['war_clan_id'] = True
            await query.message.reply_text("ID врага:")
            return WAITING_FOR_WAR_CLAN_ID
        
        elif data == "clan_entry":
            await query.message.edit_text("🔒 Вход:", reply_markup=Keyboards.clan_entry_menu())
        
        elif data == "entry_open":
            clan = db.get_user_clan(user.id)
            db.update_clan_entry_type(clan['clan_id'], 'open')
            await query.message.reply_text("✅ Открыт!")
        
        elif data == "entry_closed":
            clan = db.get_user_clan(user.id)
            db.update_clan_entry_type(clan['clan_id'], 'closed')
            await query.message.reply_text("✅ Закрыт!")
        
        elif data == "entry_request":
            clan = db.get_user_clan(user.id)
            db.update_clan_entry_type(clan['clan_id'], 'request')
            await query.message.reply_text("✅ По заявкам!")
        
        elif data == "find_clan_btn":
            context.user_data['waiting_clan_id'] = True
            await query.message.reply_text("ID клана:")
            return WAITING_FOR_CLAN_ID
        
        elif data == "clan_members":
            clan = db.get_user_clan(user.id)
            if clan:
                members = db.get_clan_members(clan['clan_id'])
                text = "👥 Участники:\n\n"
                for m in members:
                    text += f"👤 {m['first_name']}\n"
                await query.message.edit_text(text, reply_markup=Keyboards.back_to_clan())
        
        return ConversationHandler.END
    
    commands = {
        "start": Handlers.start, "help": Handlers.help_command,
        "profile": Handlers.profile, "ping": Handlers.ping,
        "id": Handlers.get_id, "clan": Handlers.clan_menu_command,
        "clan_top": Handlers.clan_top_command, "clan_bonus": Handlers.clan_bonus,
        "stats": Handlers.stats, "create_clan": Handlers.create_clan,
        "join_clan": Handlers.join_clan, "leave_clan": Handlers.leave_clan,
        "report": Handlers.report, "ban": Handlers.ban,
        "unban": Handlers.unban, "mute": Handlers.mute,
        "unmute": Handlers.unmute, "warn": Handlers.warn,
        "unwarn": Handlers.unwarn, "setadm": Handlers.setadm,
        "permban": Handlers.permban, "unperm": Handlers.unperm,
        "broadcast": Handlers.broadcast, "reports": Handlers.reports,
        "ask": Handlers.ask, "backup": backup_handler,
    }
    
    for cmd, handler in commands.items():
        application.add_handler(CommandHandler(cmd, handler))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler), group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, antispam_handler), group=1)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()