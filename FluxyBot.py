#==================#
#1 ЧАСТЬ | Импорты  #
#==================#

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
WAITING_FOR_ACCESS_LEVEL = 34
WAITING_FOR_TRANSFER_CLAN = 35
WAITING_FOR_RENAME = 36
WAITING_FOR_QUESTION = 37
WAITING_FOR_REPORT_ANSWER = 38
WAITING_FOR_QUESTION_ANSWER = 39

JSONBIN_API_KEY = "$2a$10$oQFi.r.b4KoxCupZTsKdzeH6ZktFfBr12SBHnTXgkmRwGBJr1bRdm"
JSONBIN_BIN_ID = "6a8ac58bda38895dfe06783c"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
JSONBIN_HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY,
    "Content-Type": "application/json"
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
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
                print("✅ Загружено из локального файла")
                return
        except:
            pass
        try:
            response = requests.get(JSONBIN_URL, headers=JSONBIN_HEADERS, timeout=5)
            if response.status_code == 200:
                self.data = response.json().get("record", {})
                print("✅ Загружено из JSONBin")
                return
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
        self.data = {}
    
    def ensure_keys(self):
        defaults = {
            "users": [], "bot_admins": [], "support_agents": [],
            "chats": [], "clans": [], "bot_blacklist": [],
            "access_settings": [], "reports": [], "questions": [],
            "chat_messages": [], "clan_bonus_usage": [], "rewards": [],
            "bot_rank_names": {}, "agent_rank_names": {}, "chat_rank_names": {},
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
    
    # Пользователи
    def add_user(self, user_id, username, first_name):
        for user in self.data["users"]:
            if user["user_id"] == user_id:
                return
        self.data["users"].append({
            "user_id": user_id, "username": username or "",
            "first_name": first_name or "Пользователь",
            "clan_id": None, "warnings": 0,
            "registration_date": datetime.now().isoformat()
        })
        self.save_data()
    
    def get_user(self, user_id):
        for user in self.data["users"]:
            if user["user_id"] == user_id:
                return user
        return None
    
    def get_all_users(self):
        return [u["user_id"] for u in self.data["users"]]
    
    # Админы
    def get_bot_admin_level(self, user_id):
        if user_id == SUPER_ADMIN_ID:
            return 10
        for admin in self.data["bot_admins"]:
            if admin["user_id"] == user_id:
                return admin.get("level", 1)
        return 0
    
    def add_bot_admin(self, user_id, level, added_by):
        for admin in self.data["bot_admins"]:
            if admin["user_id"] == user_id:
                admin["level"] = level
                self.save_data()
                return
        self.data["bot_admins"].append({
            "user_id": user_id, "level": level,
            "added_by": added_by, "added_date": datetime.now().isoformat()
        })
        self.save_data()
    
    def remove_bot_admin(self, user_id):
        self.data["bot_admins"] = [a for a in self.data["bot_admins"] if a["user_id"] != user_id]
        self.save_data()
    
    def get_all_bot_admins(self):
        result = []
        for admin in self.data["bot_admins"]:
            user = self.get_user(admin["user_id"])
            result.append({
                "user_id": admin["user_id"], "level": admin["level"],
                "first_name": user["first_name"] if user else "Пользователь"
            })
        return sorted(result, key=lambda x: x["level"], reverse=True)
    
    def update_bot_admin_level(self, user_id, level):
        for admin in self.data["bot_admins"]:
            if admin["user_id"] == user_id:
                admin["level"] = level
                self.save_data()
                return
    
    # Агенты
    def add_agent(self, user_id, level):
        for agent in self.data["support_agents"]:
            if agent["user_id"] == user_id:
                agent["level"] = level
                self.save_data()
                return
        self.data["support_agents"].append({
            "user_id": user_id, "level": level,
            "status": "offline", "answered_questions": 0
        })
        self.save_data()
    
    def remove_agent(self, user_id):
        self.data["support_agents"] = [a for a in self.data["support_agents"] if a["user_id"] != user_id]
        self.save_data()
    
    def get_agent_level(self, user_id):
        for agent in self.data["support_agents"]:
            if agent["user_id"] == user_id:
                return agent.get("level", 1)
        return 0
    
    def get_all_agents(self):
        result = []
        for agent in self.data["support_agents"]:
            user = self.get_user(agent["user_id"])
            result.append({
                "user_id": agent["user_id"], "level": agent["level"],
                "status": agent.get("status", "offline"),
                "answered_questions": agent.get("answered_questions", 0),
                "first_name": user["first_name"] if user else "Агент"
            })
        return result
    
    def update_agent_level(self, user_id, level):
        for agent in self.data["support_agents"]:
            if agent["user_id"] == user_id:
                agent["level"] = level
                self.save_data()
                return
    
    # Кланы
    def create_clan(self, name, leader_id):
        clan_id = len(self.data["clans"]) + 1
        self.data["clans"].append({
            "clan_id": clan_id, "name": name, "leader_id": leader_id,
            "rating": 0, "entry_type": "open",
            "created_date": datetime.now().isoformat(),
            "total_members": 1, "wins": 0, "losses": 0
        })
        for user in self.data["users"]:
            if user["user_id"] == leader_id:
                user["clan_id"] = clan_id
        self.save_data()
        return clan_id
    
    def get_clan_by_id(self, clan_id):
        for clan in self.data["clans"]:
            if clan["clan_id"] == clan_id:
                return clan
        return None
    
    def get_clan_by_name(self, name):
        for clan in self.data["clans"]:
            if clan["name"] == name:
                return clan
        return None
    
    def get_user_clan(self, user_id):
        user = self.get_user(user_id)
        if user and user.get("clan_id"):
            return self.get_clan_by_id(user["clan_id"])
        return None
    
    def join_clan(self, user_id, clan_id):
        for user in self.data["users"]:
            if user["user_id"] == user_id:
                user["clan_id"] = clan_id
        for clan in self.data["clans"]:
            if clan["clan_id"] == clan_id:
                clan["total_members"] = sum(1 for u in self.data["users"] if u.get("clan_id") == clan_id)
        self.save_data()
    
    def leave_clan(self, user_id):
        for user in self.data["users"]:
            if user["user_id"] == user_id:
                clan_id = user.get("clan_id")
                user["clan_id"] = None
                if clan_id:
                    for clan in self.data["clans"]:
                        if clan["clan_id"] == clan_id:
                            clan["total_members"] = sum(1 for u in self.data["users"] if u.get("clan_id") == clan_id)
        self.save_data()
    
    def get_clan_members(self, clan_id):
        return [u for u in self.data["users"] if u.get("clan_id") == clan_id]
    
    def add_clan_rating(self, clan_id, rating):
        for clan in self.data["clans"]:
            if clan["clan_id"] == clan_id:
                clan["rating"] = clan.get("rating", 0) + rating
                self.save_data()
                return
    
    def get_top_clans(self, limit=10):
        for clan in self.data["clans"]:
            clan["total_members"] = sum(1 for u in self.data["users"] if u.get("clan_id") == clan["clan_id"])
        return sorted(self.data["clans"], key=lambda x: (x.get("rating", 0), x.get("total_members", 0)), reverse=True)[:limit]
    
    def update_clan_entry_type(self, clan_id, entry_type):
        for clan in self.data["clans"]:
            if clan["clan_id"] == clan_id:
                clan["entry_type"] = entry_type
                self.save_data()
                return
    
    def add_clan_request(self, clan_id, user_id):
        self.data.setdefault("clan_requests", []).append({
            "request_id": len(self.data.get("clan_requests", [])) + 1,
            "clan_id": clan_id, "user_id": user_id,
            "date": datetime.now().isoformat(), "status": "pending"
        })
        self.save_data()
    
    def get_clan_requests(self, clan_id):
        return [r for r in self.data.get("clan_requests", []) if r["clan_id"] == clan_id and r["status"] == "pending"]
    
    def update_clan_request(self, request_id, status):
        for req in self.data.get("clan_requests", []):
            if req.get("request_id") == request_id:
                req["status"] = status
                self.save_data()
                return
    
    def declare_war(self, clan1_id, clan2_id, rating_stake):
        clan1 = self.get_clan_by_id(clan1_id)
        clan2 = self.get_clan_by_id(clan2_id)
        if not clan1 or not clan2:
            return None
        winner_id = random.choice([clan1_id, clan2_id])
        loser_id = clan2_id if winner_id == clan1_id else clan1_id
        self.add_clan_rating(winner_id, rating_stake)
        self.add_clan_rating(loser_id, -rating_stake)
        return {"winner_id": winner_id, "clan1_name": clan1["name"], "clan2_name": clan2["name"]}
    
    def add_clan_message(self, from_clan_id, to_clan_id, from_user_id, text):
        self.data.setdefault("clan_messages", []).append({
            "from_clan_id": from_clan_id, "to_clan_id": to_clan_id,
            "from_user_id": from_user_id, "text": text,
            "date": datetime.now().isoformat()
        })
        self.save_data()
    
    def get_clan_messages(self, clan_id):
        return [m for m in self.data.get("clan_messages", []) if m["to_clan_id"] == clan_id]
    
    # Черный список
    def add_to_blacklist(self, user_id, reason, added_by):
        self.data["bot_blacklist"].append({
            "user_id": user_id, "reason": reason,
            "date": datetime.now().isoformat(), "added_by": added_by
        })
        self.save_data()
    
    def remove_from_blacklist(self, user_id):
        self.data["bot_blacklist"] = [b for b in self.data["bot_blacklist"] if b["user_id"] != user_id]
        self.save_data()
    
    def is_blacklisted(self, user_id):
        return any(b["user_id"] == user_id for b in self.data["bot_blacklist"])
    
    def get_blacklist(self):
        return self.data["bot_blacklist"]
    
    # Жалобы
    def add_report(self, user_id, reported_user_id, reason, message_link=None):
        report_id = len(self.data["reports"]) + 1
        self.data["reports"].append({
            "report_id": report_id, "user_id": user_id,
            "reported_user_id": reported_user_id, "reason": reason,
            "date": datetime.now().isoformat(), "status": "pending",
            "message_link": message_link
        })
        self.save_data()
        return report_id
    
    def get_pending_reports(self):
        return [r for r in self.data["reports"] if r["status"] == "pending"]
    
    def update_report_status(self, report_id, status, handled_by):
        for report in self.data["reports"]:
            if report["report_id"] == report_id:
                report["status"] = status
                report["handled_by"] = handled_by
                self.save_data()
                return
    
    # Вопросы
    def add_question(self, user_id, text):
        question_id = len(self.data["questions"]) + 1
        self.data["questions"].append({
            "question_id": question_id, "user_id": user_id,
            "text": text, "date": datetime.now().isoformat(), "status": "pending"
        })
        self.save_data()
        return question_id
    
    def get_pending_questions(self):
        return [q for q in self.data["questions"] if q["status"] == "pending"]
    
    def update_question_status(self, question_id, status, answered_by, answer_text=None):
        for question in self.data["questions"]:
            if question["question_id"] == question_id:
                question["status"] = status
                question["answered_by"] = answered_by
                question["answer_text"] = answer_text
                self.save_data()
                return
    
    # Чаты
    def add_chat(self, chat_id, title):
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                chat["title"] = title or "Чат"
                self.save_data()
                return
        self.data["chats"].append({
            "chat_id": chat_id, "title": title or "Чат",
            "welcome_enabled": 0, "welcome_text": None,
            "antispam_enabled": 0, "antispam_seconds": 5, "antispam_max_messages": 5
        })
        self.save_data()
    
    def get_all_chats(self):
        return self.data["chats"]
    
    def get_welcome_settings(self, chat_id):
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                return [chat.get("welcome_enabled", 0), chat.get("welcome_text")]
        return None
    
    def set_welcome_text(self, chat_id, text):
        self.add_chat(chat_id, "Чат")
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                chat["welcome_text"] = text
                chat["welcome_enabled"] = 1
                self.save_data()
                return
    
    def enable_welcome(self, chat_id, enabled):
        self.add_chat(chat_id, "Чат")
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                chat["welcome_enabled"] = 1 if enabled else 0
                self.save_data()
                return
    
    def get_antispam_settings(self, chat_id):
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                return [chat.get("antispam_enabled", 0), chat.get("antispam_seconds", 5)]
        return None
    
    def enable_antispam(self, chat_id, enabled):
        self.add_chat(chat_id, "Чат")
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                chat["antispam_enabled"] = 1 if enabled else 0
                self.save_data()
                return
    
    def set_antispam_seconds(self, chat_id, seconds):
        self.add_chat(chat_id, "Чат")
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                chat["antispam_seconds"] = seconds
                self.save_data()
                return
    
    def set_antispam_max_messages(self, chat_id, max_messages):
        self.add_chat(chat_id, "Чат")
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                chat["antispam_max_messages"] = max_messages
                self.save_data()
                return
    
    def get_antispam_max_messages(self, chat_id):
        for chat in self.data["chats"]:
            if chat["chat_id"] == chat_id:
                return chat.get("antispam_max_messages", 5)
        return 5
    
    # Ранги
    def get_bot_rank_name(self, level):
        ranks = {0: "Пользователь", 1: "Младший модератор", 2: "Модератор", 3: "Старший модератор", 4: "Младший админ", 5: "Админ", 6: "Старший админ", 7: "Главный админ", 8: "Заместитель основателя", 9: "Сооснователь", 10: "Основатель бота"}
        return self.data.get("bot_rank_names", {}).get(str(level), ranks.get(level, f"Уровень {level}"))
    
    def get_chat_rank_name(self, level):
        ranks = {0: "Пользователь", 1: "Младший модератор", 2: "Модератор", 3: "Старший модератор", 4: "Младший админ", 5: "Админ", 6: "Старший админ", 7: "Главный админ", 8: "Заместитель владельца", 9: "Сооснователь", 10: "Владелец"}
        return self.data.get("chat_rank_names", {}).get(str(level), ranks.get(level, f"Уровень {level}"))
    
    def get_agent_rank_name(self, level):
        ranks = {1: "Младший агент", 2: "Агент", 3: "Старший агент"}
        return self.data.get("agent_rank_names", {}).get(str(level), ranks.get(level, f"Уровень {level}"))
    
    def update_bot_rank_name(self, level, name):
        self.data["bot_rank_names"][str(level)] = name
        self.save_data()
    
    def update_agent_rank_name(self, level, name):
        self.data["agent_rank_names"][str(level)] = name
        self.save_data()
    
    def update_chat_rank_name(self, level, name):
        self.data["chat_rank_names"][str(level)] = name
        self.save_data()
    
    # НОВАЯ СИСТЕМА ПРАВ
    def get_rank_access(self, rank_type, level):
        result = []
        for setting in self.data.get("access_settings", []):
            if setting.get("type") == rank_type and setting.get("min_level") == level:
                result.append(setting.get("name"))
        return result
    
    def toggle_access(self, rank_type, level, function):
        for setting in self.data["access_settings"]:
            if setting["type"] == rank_type and setting["name"] == function:
                if setting.get("min_level") == level:
                    setting["min_level"] = 999
                else:
                    setting["min_level"] = level
                self.save_data()
                return
        self.data["access_settings"].append({
            "type": rank_type, "name": function, "min_level": level
        })
        self.save_data()
    
    def set_access_level(self, setting_type, setting_name, min_level):
        for setting in self.data["access_settings"]:
            if setting["type"] == setting_type and setting["name"] == setting_name:
                setting["min_level"] = min_level
                self.save_data()
                return
        self.data["access_settings"].append({
            "type": setting_type, "name": setting_name, "min_level": min_level
        })
        self.save_data()
    
    def get_access_level(self, setting_type, setting_name):
        for setting in self.data["access_settings"]:
            if setting["type"] == setting_type and setting["name"] == setting_name:
                return setting["min_level"]
        return 10
    
    # Статистика
    def get_total_stats(self):
        return (
            len(self.data["users"]), len(self.data["chats"]),
            len(self.data["clans"]), len(self.data["bot_admins"]),
            len(self.data["support_agents"]), len(self.data["bot_blacklist"]),
            len(self.data.get("chat_messages", []))
        )
    
    def add_message(self, user_id, chat_id):
        self.data.setdefault("chat_messages", []).append({
            "user_id": user_id, "chat_id": chat_id,
            "message_time": datetime.now().isoformat()
        })
    
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
        for user_id, msg_count in top:
            user = self.get_user(user_id)
            result.append((user_id, user["first_name"] if user else "Пользователь", msg_count))
        return result
    
    # Награды
    def add_reward(self, user_id, from_user_id, text):
        self.data.setdefault("rewards", []).append({
            "user_id": user_id, "from_user_id": from_user_id,
            "text": text, "date": datetime.now().isoformat()
        })
        self.save_data()
    
    def get_user_rewards(self, user_id):
        rewards = []
        for reward in self.data.get("rewards", []):
            if reward["user_id"] == user_id:
                from_user = self.get_user(reward["from_user_id"])
                rewards.append({
                    "text": reward["text"],
                    "from_name": from_user["first_name"] if from_user else "Пользователь",
                    "date": reward["date"]
                })
        return rewards
    
    # Бонус клана
    def can_use_clan_bonus(self, user_id, clan_id):
        today = datetime.now().strftime("%Y-%m-%d")
        for usage in self.data.get("clan_bonus_usage", []):
            if usage.get("clan_id") == clan_id and usage.get("user_id") == user_id and usage.get("date") == today:
                return False
        return True
    
    def use_clan_bonus(self, user_id, clan_id):
        today = datetime.now().strftime("%Y-%m-%d")
        self.data.setdefault("clan_bonus_usage", []).append({
            "clan_id": clan_id, "user_id": user_id, "date": today
        })
        self.save_data()


db = Database()

def check_bot_access(user_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_bot_admin_level(user_id)
    return function in db.get_rank_access('bot', user_level)

def check_chat_access(user_id, chat_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_bot_admin_level(user_id)
    if user_level >= 10:
        return True
    return function in db.get_rank_access('chat', user_level)

def check_agent_access(user_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_agent_level(user_id)
    return function in db.get_rank_access('agent', user_level)
    
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
            [InlineKeyboardButton("🚫 Черный список бота", callback_data="bot_blacklist")],
            [InlineKeyboardButton("⭐️ Выдать репутацию клану", callback_data="give_clan_rep")],
            [InlineKeyboardButton("📊 Статистика бота", callback_data="bot_stats")],
            [InlineKeyboardButton("👑 Супер админ", callback_data="super_admin")],
            [InlineKeyboardButton("📨 Рассылка", callback_data="broadcast_menu")],
            [InlineKeyboardButton("⚙️ Права рангов", callback_data="bot_rank_settings")],
            [InlineKeyboardButton("⚙️ Права уровней АП", callback_data="agent_settings")],
            [InlineKeyboardButton("📝 Названия рангов бота", callback_data="bot_rank_names")],
            [InlineKeyboardButton("📝 Названия уровней АП", callback_data="agent_rank_names")],
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
            [InlineKeyboardButton("⚔ Обьявить войну", callback_data="declare_war")],
            [InlineKeyboardButton("📋 Заявки", callback_data="clan_requests")],
        ]
        if is_leader:
            keyboard.insert(0, [InlineKeyboardButton("⚙️ Настройки клана", callback_data="clan_settings")])
        else:
            keyboard.append([InlineKeyboardButton("🚪 Выйти из клана", callback_data="leave_clan_btn")])
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
            keyboard.append([InlineKeyboardButton("👤 Пригласить участника", callback_data="invite_member")])
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
            [InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Удалить админа", callback_data="remove_admin")],
            [InlineKeyboardButton("🔄 Изменить уровень", callback_data="change_admin_level")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def agent_manage_menu():
        keyboard = [
            [InlineKeyboardButton("➕ Добавить агента", callback_data="add_agent")],
            [InlineKeyboardButton("➖ Удалить агента", callback_data="remove_agent")],
            [InlineKeyboardButton("🔄 Изменить уровень", callback_data="change_agent_level")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def clan_entry_menu():
        keyboard = [
            [InlineKeyboardButton("✅ Разрешить", callback_data="entry_open")],
            [InlineKeyboardButton("❌ Запретить", callback_data="entry_closed")],
            [InlineKeyboardButton("📝 Заявка", callback_data="entry_request")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_clan")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_start():
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_profile():
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_profile")]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_clan():
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_clan")]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def broadcast_menu():
        keyboard = [
            [InlineKeyboardButton("👥 Рассылка в ЛС", callback_data="broadcast_pm")],
            [InlineKeyboardButton("💬 Рассылка по чатам", callback_data="broadcast_chats")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def blacklist_menu():
        keyboard = [
            [InlineKeyboardButton("➕ Добавить в ЧС", callback_data="blacklist_add")],
            [InlineKeyboardButton("➖ Удалить из ЧС", callback_data="blacklist_remove")],
            [InlineKeyboardButton("📋 Список ЧС", callback_data="blacklist_list")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def welcome_settings_menu(welcome_enabled):
        status = "✅ Включено" if welcome_enabled else "❌ Выключено"
        keyboard = [
            [InlineKeyboardButton(f"Статус: {status}", callback_data="toggle_welcome")],
            [InlineKeyboardButton("📝 Изменить текст", callback_data="edit_welcome_text")],
            [InlineKeyboardButton("👁 Показать приветствие", callback_data="show_welcome")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max_messages):
        status = "✅ Включено" if antispam_enabled else "❌ Выключено"
        keyboard = [
            [InlineKeyboardButton(f"Статус: {status}", callback_data="toggle_antispam")],
            [InlineKeyboardButton(f"⏱ Интервал: {antispam_seconds} сек", callback_data="change_antispam_interval")],
            [InlineKeyboardButton(f"📊 Макс. сообщений: {antispam_max_messages}", callback_data="change_antispam_messages")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
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
    def super_admin_menu():
        keyboard = [
            [InlineKeyboardButton("📋 Все команды", callback_data="all_commands")],
            [InlineKeyboardButton("📝 Ранги бота", callback_data="bot_rank_names")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)

    # НОВАЯ СИСТЕМА ПРАВ
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
            functions = [
                ("manage_admins", "👥 Управление админами"),
                ("manage_agents", "🔰 Управление агентами"),
                ("blacklist", "🚫 Черный список"),
                ("give_clan_rep", "⭐️ Выдача репутации"),
                ("view_chats", "🗂 Просмотр чатов"),
                ("stats", "📊 Статистика"),
                ("broadcast", "📨 Рассылка"),
                ("view_reports", "❗️ Просмотр жалоб"),
                ("give_reward", "🎁 Выдача наград"),
            ]
        elif rank_type == 'agent':
            functions = [
                ("view_questions", "❓ Просмотр вопросов"),
                ("answer_questions", "✉️ Ответ на вопросы"),
                ("hstats", "📊 Статистика агента"),
            ]
        else:
            functions = [
                ("ban", "🔨 Бан"),
                ("unban", "🔓 Разбан"),
                ("mute", "🔇 Мут"),
                ("unmute", "🔊 Размут"),
                ("warn", "⚠️ Предупреждение"),
                ("unwarn", "✅ Снятие предупреждения"),
                ("setadm", "👑 Назначение админов"),
                ("welcome_settings", "👋 Приветствие"),
                ("antispam_settings", "🚫 Антиспам"),
            ]
        
        current_access = db.get_rank_access(rank_type, level)
        
        for func, display_name in functions:
            if func in current_access:
                keyboard.append([InlineKeyboardButton(f"✅ {display_name}", callback_data=f"toggle_access_{rank_type}_{level}_{func}")])
            else:
                keyboard.append([InlineKeyboardButton(f"❌ {display_name}", callback_data=f"toggle_access_{rank_type}_{level}_{func}")])
        
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
                    await update.message.reply_text(f"✅ Бот активирован!\n📝 Напишите /start")

    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        bot_level = db.get_bot_admin_level(user.id)
        
        text = """📋 Справка по командам:
━━━━━━━━━━━━━━━━

👤 Основные:
/start - Главное меню
/profile - Профиль
/ping - Проверить пинг
/id - Показать ID

🛡 Кланы:
/clan - Меню клана
/clan_top - Топ кланов
/clan_bonus - Бонус клана
/create_clan - Создать клан
/join_clan - Вступить в клан
/leave_clan - Покинуть клан

📝 Прочее:
/report - Отправить жалобу
/stats - Статистика
/ask - Задать вопрос"""
        
        if bot_level >= 1:
            text += """

🔨 Модерация:
/ban, /unban, /mute, /unmute
/warn, /unwarn, /setadm"""
        
        if bot_level >= 10:
            text += """

👑 Основатель:
/backup - Резервное копирование"""
        
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
🛡️ Клан: {clan['name'] if clan else 'Нет'}
🏆 Рейтинг: {clan['rating'] if clan else 0}"""
        
        await update.message.reply_text(text, reply_markup=Keyboards.profile_menu())

    @staticmethod
    async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
        import time
        start_time = time.time()
        msg = await update.message.reply_text("Измеряю пинг...")
        end_time = time.time()
        ping = round((end_time - start_time) * 1000)
        await msg.edit_text(f"🏓 Понг!\n⏱ Пинг: {ping}ms")

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
        
        if not db.can_use_clan_bonus(user.id, clan['clan_id']):
            await update.message.reply_text("❌ Вы уже использовали бонус сегодня!")
            return
        
        members = db.get_clan_members(clan['clan_id'])
        bonus = len(members)
        db.add_clan_rating(clan['clan_id'], bonus)
        db.use_clan_bonus(user.id, clan['clan_id'])
        await update.message.reply_text(f"✅ Клан получил +{bonus} рейтинга!")

    @staticmethod
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        
        target = update.message.reply_to_message.from_user
        db.add_user(target.id, target.username, target.first_name)
        clan = db.get_user_clan(target.id)
        user_data = db.get_user(target.id)
        
        text = f"""👤 {target.first_name}
━━━━━━━━━━━━━━━━

🆔 ID: {target.id}
🎖️ Ранг: {db.get_bot_rank_name(db.get_bot_admin_level(target.id))}
🛡️ Клан: {clan['name'] if clan else 'Нет'}
⚠️ Варны: {user_data.get('warnings', 0) if user_data else 0}/3"""
        
        await update.message.reply_text(text)

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
        if clan['entry_type'] == 'closed':
            await update.message.reply_text("❌ Вход закрыт!")
            return
        if clan['entry_type'] == 'request':
            db.add_clan_request(clan_id, user.id)
            await update.message.reply_text("✅ Заявка отправлена!")
            return
        
        db.join_clan(user.id, clan_id)
        await update.message.reply_text(f"✅ Вы вступили в «{clan['name']}»!")

    @staticmethod
    async def leave_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        if not clan:
            await update.message.reply_text("❌ Вы не в клане!")
            return
        if clan['leader_id'] == user.id:
            await update.message.reply_text("❌ Лидер не может покинуть клан!")
            return
        
        db.leave_clan(user.id)
        await update.message.reply_text(f"✅ Вы покинули «{clan['name']}»!")

    @staticmethod
    async def clan_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        clan = db.get_user_clan(user.id)
        
        if clan:
            is_leader = clan['leader_id'] == user.id
            text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan['clan_id']}
🛡 Название: {clan['name']}
🏆 Рейтинг: {clan['rating']}
👥 Участников: {clan['total_members']}"""
            await update.message.reply_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
        else:
            await update.message.reply_text("🛡 Кланы\n\nВыберите действие:", reply_markup=Keyboards.clan_menu())

    @staticmethod
    async def clan_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        clans = db.get_top_clans(15)
        text = "🏆 Топ 15 кланов:\n━━━━━━━━━━━━━━━━\n\n"
        
        if not clans:
            text += "Пока нет кланов"
        
        for i, clan in enumerate(clans, 1):
            text += f"{i}. 🛡 {clan['name']}\n   🆔 ID: {clan['clan_id']}\n   🏆 Рейтинг: {clan['rating']}\n   👥 Участников: {clan['total_members']}\n━━━━━━━━━━━━━━━━\n"
        
        await update.message.reply_text(text)

    @staticmethod
    async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте на сообщение нарушителя!")
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
        
        report_id = db.add_report(update.effective_user.id, target.id, reason, message_link)
        
        await update.message.reply_text(f"✅ Жалоба отправлена!\n\n👤 Нарушитель: {target.first_name}\n🆔 ID: {target.id}\n📝 Причина: {reason}")
        
        admins = db.get_all_bot_admins()
        for admin in admins:
            try:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Принять", callback_data=f"accept_report_{report_id}"),
                     InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_report_btn_{report_id}")]
                ])
                await context.bot.send_message(
                    admin["user_id"],
                    f"❗️ Новая жалоба!\n\n👤 От: {update.effective_user.first_name}\n🎯 На: {target.first_name}\n🆔 ID нарушителя: {target.id}\n📝 Причина: {reason}\n🔗 Ссылка: {message_link}",
                    reply_markup=keyboard
                )
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
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        
        if update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
        else:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        
        try:
            await context.bot.ban_chat_member(chat_id, target.id)
            await update.message.reply_text(f"✅ {target.first_name} забанен!")
        except:
            await update.message.reply_text("❌ Не удалось забанить!")

    @staticmethod
    async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        if not check_chat_access(user.id, chat_id, 'unban'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        
        if not context.args:
            await update.message.reply_text("❌ /unban <ID>")
            return
        
        try:
            target_id = int(context.args[0])
            await context.bot.unban_chat_member(chat_id, target_id)
            await update.message.reply_text(f"✅ Разбанен!")
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
        else:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        
        try:
            until_date = datetime.now() + timedelta(minutes=60)
            await context.bot.restrict_chat_member(chat_id, target.id, until_date=until_date, can_send_messages=False)
            await update.message.reply_text(f"✅ {target.first_name} замучен на 60 минут!")
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
        else:
            await update.message.reply_text("❌ Ответьте на сообщение!")
            return
        
        try:
            await context.bot.restrict_chat_member(chat_id, target.id, can_send_messages=True)
            await update.message.reply_text(f"✅ {target.first_name} размучен!")
        except:
            await update.message.reply_text("❌ Не удалось!")

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
        user_data = db.get_user(target.id)
        warnings = user_data.get('warnings', 0) + 1 if user_data else 1
        
        for u in db.data["users"]:
            if u["user_id"] == target.id:
                u["warnings"] = warnings
                db.save_data()
                break
        
        await update.message.reply_text(f"⚠️ {target.first_name} получил предупреждение!\n📊 Варнов: {warnings}/3")

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
        for u in db.data["users"]:
            if u["user_id"] == target.id and u.get("warnings", 0) > 0:
                u["warnings"] -= 1
                db.save_data()
                break
        
        await update.message.reply_text(f"✅ Предупреждение снято!")

    @staticmethod
    async def setadm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        if not check_chat_access(user.id, chat_id, 'setadm'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ /setadm <ID> <уровень>")
            return
        
        try:
            target_id = int(context.args[0])
            level = int(context.args[1])
            db.add_bot_admin(target_id, level, user.id)
            await update.message.reply_text(f"✅ Назначен админом уровня {level}!")
        except:
            await update.message.reply_text("❌ Неверные аргументы!")

    @staticmethod
    async def permban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not check_bot_access(user.id, 'blacklist'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        
        if not context.args:
            await update.message.reply_text("❌ /permban <ID>")
            return
        
        try:
            target_id = int(context.args[0])
            db.add_to_blacklist(target_id, "Не указана", user.id)
            await update.message.reply_text(f"✅ {target_id} в ЧС!")
        except:
            await update.message.reply_text("❌ Неверный ID!")

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
            db.remove_from_blacklist(target_id)
            await update.message.reply_text(f"✅ Удален из ЧС!")
        except:
            await update.message.reply_text("❌ Неверный ID!")

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
        
        for user_id in users:
            try:
                await context.bot.send_message(user_id, f"📨 {text}")
                sent += 1
            except:
                pass
        
        await update.message.reply_text(f"✅ Отправлено: {sent}")

    @staticmethod
    async def reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not check_bot_access(user.id, 'view_reports'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        
        reports = db.get_pending_reports()
        if not reports:
            await update.message.reply_text("✅ Нет жалоб!")
            return
        
        text = "❗️ Жалобы:\n\n"
        for r in reports:
            text += f"🆔 #{r['report_id']}\n📝 {r['reason']}\n━━━━━━━━━━━━━━━━\n"
        
        await update.message.reply_text(text)

    @staticmethod
    async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not context.args:
            await update.message.reply_text("❌ /ask <текст>")
            return
        
        question = " ".join(context.args)
        question_id = db.add_question(user.id, question)
        await update.message.reply_text("✅ Вопрос отправлен!")
        
        agents = db.get_all_agents()
        for agent in agents:
            try:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Принять", callback_data=f"accept_question_{question_id}"),
                     InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_question_btn_{question_id}")]
                ])
                await context.bot.send_message(agent["user_id"], f"❓ Вопрос от {user.first_name}:\n{question}", reply_markup=keyboard)
            except:
                pass

    @staticmethod
    async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if db.get_bot_admin_level(user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        
        db.save_data()
        await update.message.reply_text("✅ Данные сохранены!")

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
        
        # Навигация
        if data == "back_to_start":
            user_id = user.id
            bot_rank_level = db.get_bot_admin_level(user_id)
            is_chat_owner = False
            
            if update.effective_chat.type != 'private':
                try:
                    admins = await context.bot.get_chat_administrators(chat_id)
                    for admin in admins:
                        if admin.status == 'creator' and admin.user.id == user_id:
                            is_chat_owner = True
                            break
                except:
                    pass
            
            if bot_rank_level >= 1 and is_chat_owner:
                await query.message.edit_text("Главное меню Fluxy", reply_markup=Keyboards.main_menu_with_both())
            elif bot_rank_level >= 1:
                await query.message.edit_text("Главное меню Fluxy", reply_markup=Keyboards.main_menu_with_admin())
            elif is_chat_owner:
                await query.message.edit_text("Главное меню Fluxy", reply_markup=Keyboards.main_menu_with_chat_admin())
            else:
                await query.message.edit_text("Главное меню Fluxy", reply_markup=Keyboards.main_menu())
            return ConversationHandler.END
        
        elif data == "back_to_profile":
            clan = db.get_user_clan(user.id)
            text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}
🛡️ Клан: {clan['name'] if clan else 'Нет'}"""
            await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
            return ConversationHandler.END
        
        elif data == "back_to_clan":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan['leader_id'] == user.id
                text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan['clan_id']}
🛡 Название: {clan['name']}
🏆 Рейтинг: {clan['rating']}
👥 Участников: {clan['total_members']}"""
                await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
            return ConversationHandler.END
        
        # Профиль
        elif data == "profile":
            clan = db.get_user_clan(user.id)
            text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}
🛡️ Клан: {clan['name'] if clan else 'Нет'}"""
            await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
        
        elif data == "my_rewards":
            rewards = db.get_user_rewards(user.id)
            text = "🏆 Ваши награды:\n━━━━━━━━━━━━━━━━\n\n"
            if not rewards:
                text += "Нет наград"
            for reward in rewards:
                text += f"🎁 {reward['text']}\n👤 От: {reward['from_name']}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_profile())
        
        elif data == "give_reward_btn":
            context.user_data['giving_reward'] = True
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_REWARD_USER
        
        # Статистика
        elif data == "chat_stats":
            await query.message.edit_text("📊 Статистика чата:", reply_markup=Keyboards.chat_stats_menu())
        
        elif data == "top_day":
            top = db.get_top_messages(chat_id, 'day')
            text = "📊 Топ дня:\n━━━━━━━━━━━━━━━━\n\n"
            if not top:
                text += "Нет данных"
            for i, (uid, name, count) in enumerate(top, 1):
                text += f"{i}. {name}\n💬 {count}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "top_week":
            top = db.get_top_messages(chat_id, 'week')
            text = "📊 Топ недели:\n━━━━━━━━━━━━━━━━\n\n"
            if not top:
                text += "Нет данных"
            for i, (uid, name, count) in enumerate(top, 1):
                text += f"{i}. {name}\n💬 {count}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "top_all":
            top = db.get_top_messages(chat_id, 'all')
            text = "📊 Весь топ:\n━━━━━━━━━━━━━━━━\n\n"
            if not top:
                text += "Нет данных"
            for i, (uid, name, count) in enumerate(top, 1):
                text += f"{i}. {name}\n💬 {count}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        # Клан
        elif data == "clan_menu":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan['leader_id'] == user.id
                text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan['clan_id']}
🛡 Название: {clan['name']}
🏆 Рейтинг: {clan['rating']}
👥 Участников: {clan['total_members']}"""
                await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
            else:
                await query.message.edit_text("🛡 Кланы:", reply_markup=Keyboards.clan_menu())
        
        elif data == "clan_settings":
            clan = db.get_user_clan(user.id)
            if clan and clan['leader_id'] == user.id:
                await query.message.edit_text("⚙️ Настройки клана:", reply_markup=Keyboards.clan_settings_menu())
        
        elif data == "clan_requests":
            clan = db.get_user_clan(user.id)
            if clan and clan['leader_id'] == user.id:
                requests = db.get_clan_requests(clan['clan_id'])
                text = "📋 Заявки:\n━━━━━━━━━━━━━━━━\n\n"
                if not requests:
                    text += "Нет заявок"
                for req in requests:
                    text += f"🆔 {req['request_id']}\n👤 ID: {req['user_id']}\n━━━━━━━━━━━━━━━━\n"
                await query.message.edit_text(text, reply_markup=Keyboards.back_to_clan())
        
        elif data == "clan_members":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan['leader_id'] == user.id
                members = db.get_clan_members(clan['clan_id'])
                text = f"👥 Участники:\n━━━━━━━━━━━━━━━━\n\n"
                for m in members:
                    text += f"👤 {m['first_name']}\n🆔 {m['user_id']}\n━━━━━━━━━━━━━━━━\n"
                await query.message.edit_text(text, reply_markup=Keyboards.clan_members_menu(is_leader))
        
        elif data == "clan_entry":
            clan = db.get_user_clan(user.id)
            if clan and clan['leader_id'] == user.id:
                await query.message.edit_text("🔒 Тип входа:", reply_markup=Keyboards.clan_entry_menu())
        
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
            clan = db.get_user_clan(user.id)
            if clan and clan['leader_id'] == user.id:
                context.user_data['war_clan_id'] = True
                await query.message.reply_text("Отправьте ID врага:")
                return WAITING_FOR_WAR_CLAN_ID
        
        elif data == "message_clan":
            clan = db.get_user_clan(user.id)
            if clan and clan['leader_id'] == user.id:
                context.user_data['clan_msg_to'] = True
                await query.message.reply_text("Отправьте ID клана:")
                return WAITING_FOR_CLAN_MSG_CLAN
        
        elif data == "invite_member":
            clan = db.get_user_clan(user.id)
            if clan:
                context.user_data['waiting_invite'] = True
                await query.message.reply_text("Отправьте ID:")
                return WAITING_FOR_INVITE_USER
        
        elif data == "transfer_clan":
            clan = db.get_user_clan(user.id)
            if clan and clan['leader_id'] == user.id:
                context.user_data['transfer_clan'] = True
                await query.message.reply_text("Отправьте ID нового лидера:")
                return WAITING_FOR_TRANSFER_CLAN
        
        elif data == "delete_clan":
            clan = db.get_user_clan(user.id)
            if clan and clan['leader_id'] == user.id:
                db.data["clans"] = [c for c in db.data["clans"] if c["clan_id"] != clan["clan_id"]]
                for u in db.data["users"]:
                    if u.get("clan_id") == clan["clan_id"]:
                        u["clan_id"] = None
                db.save_data()
                await query.message.edit_text("✅ Клан удален!", reply_markup=Keyboards.clan_menu())
        
        elif data == "leave_clan_btn":
            clan = db.get_user_clan(user.id)
            if clan:
                if clan['leader_id'] == user.id:
                    await query.message.reply_text("❌ Лидер не может выйти!")
                else:
                    db.leave_clan(user.id)
                    await query.message.edit_text("✅ Вы вышли из клана!", reply_markup=Keyboards.clan_menu())
            return ConversationHandler.END
        
        elif data == "find_clan_btn":
            context.user_data['waiting_clan_id'] = True
            await query.message.reply_text("Отправьте ID клана:")
            return WAITING_FOR_CLAN_ID
        
        elif data == "create_clan_btn":
            await query.message.reply_text("/create_clan <название>")
        
        elif data == "clan_list_btn":
            await query.message.reply_text("/clan_top")
        
        # Админ панель
        elif data == "admin_panel":
            await query.message.edit_text("⭐️ Админ панель:", reply_markup=Keyboards.admin_panel())
        
        elif data == "admins_list":
            admins = db.get_all_bot_admins()
            text = "👥 Админы:\n━━━━━━━━━━━━━━━━\n\n"
            for admin in admins:
                text += f"👤 {admin['first_name']}\n🆔 {admin['user_id']}\n📊 {admin['level']}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.admin_manage_menu())
        
        elif data == "add_admin":
            context.user_data['action'] = 'add_admin'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "remove_admin":
            context.user_data['action'] = 'remove_admin'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "change_admin_level":
            context.user_data['action'] = 'change_admin_level'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "agents_manage":
            agents = db.get_all_agents()
            text = "🔰 Агенты:\n━━━━━━━━━━━━━━━━\n\n"
            for agent in agents:
                text += f"👤 {agent['first_name']}\n🆔 {agent['user_id']}\n📊 {agent['level']}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.agent_manage_menu())
        
        elif data == "add_agent":
            context.user_data['action'] = 'add_agent'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "remove_agent":
            context.user_data['action'] = 'remove_agent'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "change_agent_level":
            context.user_data['action'] = 'change_agent_level'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "bot_blacklist":
            blacklist = db.get_blacklist()
            text = "🚫 ЧС:\n━━━━━━━━━━━━━━━━\n\n"
            for b in blacklist:
                text += f"🆔 {b['user_id']}: {b['reason']}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.blacklist_menu())
        
        elif data == "blacklist_add":
            context.user_data['action'] = 'blacklist_add'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_BLACKLIST_ID
        
        elif data == "blacklist_remove":
            context.user_data['action'] = 'blacklist_remove'
            await query.message.reply_text("Отправьте ID:")
            return WAITING_FOR_BLACKLIST_ID
        
        elif data == "broadcast_menu":
            await query.message.edit_text("📨 Рассылка:", reply_markup=Keyboards.broadcast_menu())
        
        elif data == "broadcast_pm":
            context.user_data['broadcast_type'] = 'pm'
            await query.message.reply_text("Отправьте текст:")
            return WAITING_FOR_BROADCAST_TEXT
        
        elif data == "broadcast_chats":
            context.user_data['broadcast_type'] = 'chats'
            await query.message.reply_text("Отправьте текст:")
            return WAITING_FOR_BROADCAST_TEXT
        
        elif data == "bot_stats":
            users, chats, clans, admins, agents, blacklist, messages = db.get_total_stats()
            text = f"""📊 Статистика:
━━━━━━━━━━━━━━━━

👥 Пользователей: {users}
💬 Чатов: {chats}
🛡 Кланов: {clans}
👑 Админов: {admins}
🔰 Агентов: {agents}
🚫 В ЧС: {blacklist}
📨 Сообщений: {messages}"""
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        # НОВАЯ СИСТЕМА ПРАВ
        elif data == "bot_rank_settings":
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('bot'))
        
        elif data == "agent_settings":
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('agent'))
        
        elif data == "chat_rank_settings":
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels_for_access('chat'))
        
        elif data.startswith("rank_access_"):
            parts = data.split("_")
            rank_type = parts[2]
            level = int(parts[3])
            await query.message.edit_text(f"Права уровня {level}:", reply_markup=Keyboards.rank_access_menu(rank_type, level))
        
        elif data.startswith("toggle_access_"):
            parts = data.split("_")
            rank_type = parts[2]
            level = int(parts[3])
            function = parts[4]
            db.toggle_access(rank_type, level, function)
            await query.message.edit_text(f"Права уровня {level}:", reply_markup=Keyboards.rank_access_menu(rank_type, level))
        
        # Ранги
        elif data == "bot_rank_names":
            context.user_data['rename_type'] = 'bot'
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels('bot'))
        
        elif data == "agent_rank_names":
            context.user_data['rename_type'] = 'agent'
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels('agent'))
        
        elif data == "chat_rank_names":
            context.user_data['rename_type'] = 'chat'
            await query.message.edit_text("Выберите уровень:", reply_markup=Keyboards.rank_levels('chat'))
        
        elif data.startswith("rename_level_"):
            level = int(data.replace("rename_level_", ""))
            context.user_data['rename_level'] = level
            await query.message.reply_text(f"Новое название для {level}:")
            return WAITING_FOR_RENAME
        
        # Админ панель чата
        elif data == "chat_panel":
            await query.message.edit_text("👑 Админ панель чата:", reply_markup=Keyboards.chat_panel())
        
        elif data == "chat_admins_list":
            admins = db.get_all_bot_admins()
            text = "👥 Админы:\n━━━━━━━━━━━━━━━━\n\n"
            for admin in admins:
                text += f"👤 {admin['first_name']}\n📊 {admin['level']}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "welcome_settings":
            ws = db.get_welcome_settings(chat_id)
            enabled = ws[0] if ws else 0
            await query.message.edit_text("👋 Приветствие:", reply_markup=Keyboards.welcome_settings_menu(enabled))
        
        elif data == "toggle_welcome":
            ws = db.get_welcome_settings(chat_id)
            db.enable_welcome(chat_id, not (ws[0] if ws else 0))
            ws = db.get_welcome_settings(chat_id)
            await query.message.edit_text("👋 Приветствие:", reply_markup=Keyboards.welcome_settings_menu(ws[0] if ws else 0))
        
        elif data == "edit_welcome_text":
            context.user_data['editing_welcome'] = chat_id
            await query.message.reply_text("Отправьте текст:")
            return WAITING_FOR_WELCOME_TEXT
        
        elif data == "antispam_settings":
            aset = db.get_antispam_settings(chat_id)
            enabled = aset[0] if aset else 0
            seconds = aset[1] if aset else 5
            max_msg = db.get_antispam_max_messages(chat_id)
            await query.message.edit_text("🚫 Антиспам:", reply_markup=Keyboards.antispam_settings_menu(enabled, seconds, max_msg))
        
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
            seconds = int(data.replace("set_antispam_", ""))
            db.set_antispam_seconds(chat_id, seconds)
            await query.message.edit_text(f"✅ Интервал: {seconds}с", reply_markup=Keyboards.back_to_start())
        
        elif data.startswith("set_msg_"):
            max_msg = int(data.replace("set_msg_", ""))
            db.set_antispam_max_messages(chat_id, max_msg)
            await query.message.edit_text(f"✅ Макс: {max_msg}", reply_markup=Keyboards.back_to_start())
        
        # Помощь
        elif data == "help_menu":
            await query.message.edit_text("🆘 Помощь:", reply_markup=Keyboards.help_menu())
        
        elif data == "report_btn":
            await query.message.reply_text("Ответьте на сообщение нарушителя и напишите /report <причина>")
        
        elif data == "question_btn":
            context.user_data['asking_question'] = True
            await query.message.reply_text("Задайте вопрос:")
            return WAITING_FOR_QUESTION
        
        # Принятие/отклонение
        elif data.startswith("accept_report_"):
            report_id = int(data.replace("accept_report_", ""))
            context.user_data['answering_report'] = report_id
            await query.message.reply_text("Отправьте ответ:")
            return WAITING_FOR_REPORT_ANSWER
        
        elif data.startswith("reject_report_btn_"):
            report_id = int(data.replace("reject_report_btn_", ""))
            db.update_report_status(report_id, 'rejected', user.id)
            await query.message.edit_text("✅ Отклонено!")
            return ConversationHandler.END
        
        elif data.startswith("accept_question_"):
            question_id = int(data.replace("accept_question_", ""))
            context.user_data['answering_question'] = question_id
            await query.message.reply_text("Отправьте ответ:")
            return WAITING_FOR_QUESTION_ANSWER
        
        elif data.startswith("reject_question_btn_"):
            question_id = int(data.replace("reject_question_btn_", ""))
            db.update_question_status(question_id, 'rejected', user.id)
            await query.message.edit_text("✅ Отклонено!")
            return ConversationHandler.END
        
        elif data == "commands_menu":
            await query.message.edit_text("📋 Команды:\n/start /help /profile /clan /report /ask", reply_markup=Keyboards.back_to_start())
        
        elif data == "agents_list":
            agents = db.get_all_agents()
            text = "🔰 Агенты:\n━━━━━━━━━━━━━━━━\n\n"
            for agent in agents:
                text += f"👤 {agent['first_name']}\n📊 {agent['level']}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        return ConversationHandler.END

    @staticmethod
    async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.new_chat_members:
            return
        
        chat_id = update.effective_chat.id
        welcome_settings = db.get_welcome_settings(chat_id)
        
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            if welcome_settings and welcome_settings[0] == 1:
                welcome_text = welcome_settings[1] or "Добро пожаловать!"
                welcome_text = welcome_text.replace("{name}", member.first_name or "Гость")
                welcome_text = welcome_text.replace("{chat}", update.effective_chat.title or "Чат")
                await update.message.reply_text(welcome_text)

    @staticmethod
    async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    	user = update.effective_user
    	
    	if db.get_bot_admin_level(user.id) < 10:
    	   await update.message.reply_text("❌ Только Основатель!")
    	   return
    	   
    	   status_message = await update.message.reply_text("📦 Сохраняю данные...")
    	   
    	   try:
    	   	db.save_data()
    	   	await status_message.edit_text("✅ Данные успешно сохранены!")
    	   except Exception as e:
    	   	logger.error(f"Ошибка сохранения: {e}")
    	   	await status_message.edit_text(f"❌ Ошибка: {str(e)[:100]}")

    @staticmethod
    async def antispam_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        db.add_user(user.id, user.username, user.first_name)
        db.add_message(user.id, chat_id)
                
#==================#
#5 ЧАСТЬ | Main           #
#==================#

    @staticmethod
    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text
        
        if db.is_blacklisted(user.id):
            await update.message.reply_text("❌ Вы в черном списке!")
            return ConversationHandler.END
        
        if 'editing_welcome' in context.user_data:
            chat_id = context.user_data['editing_welcome']
            db.set_welcome_text(chat_id, text)
            await update.message.reply_text("✅ Приветствие установлено!")
            context.user_data.pop('editing_welcome', None)
            return ConversationHandler.END
        
        if 'asking_question' in context.user_data:
            question_id = db.add_question(user.id, text)
            await update.message.reply_text("✅ Вопрос отправлен!")
            context.user_data.pop('asking_question', None)
            
            agents = db.get_all_agents()
            for agent in agents:
                try:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Принять", callback_data=f"accept_question_{question_id}"),
                         InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_question_btn_{question_id}")]
                    ])
                    await context.bot.send_message(agent["user_id"], f"❓ Вопрос от {user.first_name}:\n{text}", reply_markup=keyboard)
                except:
                    pass
            return ConversationHandler.END
        
        if 'answering_report' in context.user_data:
            report_id = context.user_data['answering_report']
            db.update_report_status(report_id, 'answered', user.id)
            
            for r in db.data["reports"]:
                if r["report_id"] == report_id:
                    try:
                        await context.bot.send_message(r["user_id"], f"✅ Ваша жалоба рассмотрена!\n📝 Ответ: {text}")
                    except:
                        pass
                    break
            
            await update.message.reply_text("✅ Ответ отправлен!")
            context.user_data.pop('answering_report', None)
            return ConversationHandler.END
        
        if 'answering_question' in context.user_data:
            question_id = context.user_data['answering_question']
            db.update_question_status(question_id, 'answered', user.id, text)
            
            for q in db.data["questions"]:
                if q["question_id"] == question_id:
                    try:
                        await context.bot.send_message(q["user_id"], f"❓ Ответ на ваш вопрос:\n\n{text}")
                    except:
                        pass
                    break
            
            await update.message.reply_text("✅ Ответ отправлен!")
            context.user_data.pop('answering_question', None)
            return ConversationHandler.END
        
        if 'giving_reward' in context.user_data:
            if 'reward_target' not in context.user_data:
                try:
                    target_id = int(text)
                    context.user_data['reward_target'] = target_id
                    await update.message.reply_text("Отправьте текст награды:")
                    return WAITING_FOR_REWARD_TEXT
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_REWARD_USER
            else:
                target_id = context.user_data.get('reward_target')
                db.add_reward(target_id, user.id, text)
                await update.message.reply_text(f"✅ Награда выдана!")
                context.user_data.clear()
                return ConversationHandler.END
        
        if 'waiting_clan_id' in context.user_data:
            try:
                clan_id = int(text)
                clan = db.get_clan_by_id(clan_id)
                if not clan:
                    await update.message.reply_text("❌ Клан не найден!")
                    return WAITING_FOR_CLAN_ID
                
                if db.get_user_clan(user.id):
                    await update.message.reply_text("❌ Вы уже в клане!")
                    context.user_data.pop('waiting_clan_id', None)
                    return ConversationHandler.END
                
                if clan['entry_type'] == 'closed':
                    await update.message.reply_text("❌ Вход закрыт!")
                    context.user_data.pop('waiting_clan_id', None)
                    return ConversationHandler.END
                
                if clan['entry_type'] == 'request':
                    db.add_clan_request(clan_id, user.id)
                    await update.message.reply_text("✅ Заявка отправлена!")
                    context.user_data.pop('waiting_clan_id', None)
                    return ConversationHandler.END
                
                db.join_clan(user.id, clan_id)
                await update.message.reply_text(f"✅ Вы вступили в «{clan['name']}»!")
                context.user_data.pop('waiting_clan_id', None)
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_CLAN_ID
        
        if 'transfer_clan' in context.user_data:
            try:
                new_leader_id = int(text)
                clan = db.get_user_clan(user.id)
                new_leader_clan = db.get_user_clan(new_leader_id)
                if not new_leader_clan or new_leader_clan['clan_id'] != clan['clan_id']:
                    await update.message.reply_text("❌ Не в вашем клане!")
                    return WAITING_FOR_TRANSFER_CLAN
                for c in db.data["clans"]:
                    if c["clan_id"] == clan["clan_id"]:
                        c["leader_id"] = new_leader_id
                        db.save_data()
                        break
                await update.message.reply_text(f"✅ Клан передан!")
                context.user_data.pop('transfer_clan', None)
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_TRANSFER_CLAN
        
        if 'rename_level' in context.user_data:
            level = context.user_data['rename_level']
            rename_type = context.user_data.get('rename_type', 'bot')
            if rename_type == 'bot':
                db.update_bot_rank_name(level, text)
            elif rename_type == 'agent':
                db.update_agent_rank_name(level, text)
            else:
                db.update_chat_rank_name(level, text)
            await update.message.reply_text(f"✅ Переименовано в «{text}»!")
            context.user_data.pop('rename_level', None)
            context.user_data.pop('rename_type', None)
            return ConversationHandler.END
        
        if 'action' in context.user_data:
            action = context.user_data['action']
            
            if action == 'add_admin':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'add_admin_level'
                    await update.message.reply_text("Уровень (1-9):")
                    return WAITING_FOR_ADMIN_LEVEL
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID
            
            elif action == 'add_admin_level':
                try:
                    level = int(text)
                    db.add_bot_admin(context.user_data['target_id'], level, user.id)
                    await update.message.reply_text(f"✅ Админ добавлен!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_ADMIN_LEVEL
            
            elif action == 'remove_admin':
                try:
                    db.remove_bot_admin(int(text))
                    await update.message.reply_text("✅ Удален!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID
            
            elif action == 'change_admin_level':
                try:
                    context.user_data['target_id'] = int(text)
                    context.user_data['action'] = 'change_admin_level_value'
                    await update.message.reply_text("Новый уровень:")
                    return WAITING_FOR_ADMIN_LEVEL
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID
            
            elif action == 'change_admin_level_value':
                try:
                    level = int(text)
                    db.update_bot_admin_level(context.user_data['target_id'], level)
                    await update.message.reply_text("✅ Обновлено!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_ADMIN_LEVEL
            
            elif action == 'add_agent':
                try:
                    context.user_data['target_id'] = int(text)
                    context.user_data['action'] = 'add_agent_level'
                    await update.message.reply_text("Уровень (1-3):")
                    return WAITING_FOR_AGENT_LEVEL
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID
            
            elif action == 'add_agent_level':
                try:
                    level = int(text)
                    db.add_agent(context.user_data['target_id'], level)
                    await update.message.reply_text("✅ Агент добавлен!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_AGENT_LEVEL
            
            elif action == 'remove_agent':
                try:
                    db.remove_agent(int(text))
                    await update.message.reply_text("✅ Удален!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID
            
            elif action == 'change_agent_level':
                try:
                    context.user_data['target_id'] = int(text)
                    context.user_data['action'] = 'change_agent_level_value'
                    await update.message.reply_text("Новый уровень:")
                    return WAITING_FOR_AGENT_LEVEL
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID
            
            elif action == 'change_agent_level_value':
                try:
                    level = int(text)
                    db.update_agent_level(context.user_data['target_id'], level)
                    await update.message.reply_text("✅ Обновлено!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_AGENT_LEVEL
            
            elif action == 'blacklist_add':
                try:
                    context.user_data['target_id'] = int(text)
                    context.user_data['action'] = 'blacklist_add_reason'
                    await update.message.reply_text("Причина:")
                    return WAITING_FOR_BLACKLIST_REASON
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_BLACKLIST_ID
            
            elif action == 'blacklist_add_reason':
                db.add_to_blacklist(context.user_data['target_id'], text, user.id)
                await update.message.reply_text("✅ В ЧС!")
                context.user_data.clear()
                return ConversationHandler.END
            
            elif action == 'blacklist_remove':
                try:
                    db.remove_from_blacklist(int(text))
                    await update.message.reply_text("✅ Удален из ЧС!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_BLACKLIST_ID
        
        if 'broadcast_type' in context.user_data:
            sent = 0
            if context.user_data['broadcast_type'] == 'pm':
                for user_id in db.get_all_users():
                    try:
                        await context.bot.send_message(user_id, f"📨 {text}")
                        sent += 1
                    except:
                        pass
            else:
                for chat in db.get_all_chats():
                    try:
                        await context.bot.send_message(chat["chat_id"], f"📨 {text}")
                        sent += 1
                    except:
                        pass
            await update.message.reply_text(f"✅ Отправлено: {sent}")
            context.user_data.clear()
            return ConversationHandler.END
        
        if 'war_clan_id' in context.user_data:
            try:
                enemy_id = int(text)
                clan = db.get_user_clan(user.id)
                if enemy_id == clan['clan_id']:
                    await update.message.reply_text("❌ Нельзя войну с собой!")
                    return WAITING_FOR_WAR_CLAN_ID
                context.user_data['enemy_clan_id'] = enemy_id
                context.user_data.pop('war_clan_id')
                context.user_data['waiting_war_rating'] = True
                await update.message.reply_text("Ставка:")
                return WAITING_FOR_WAR_RATING
            except ValueError:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_WAR_CLAN_ID
        
        if 'waiting_war_rating' in context.user_data:
            try:
                rating = int(text)
                clan = db.get_user_clan(user.id)
                result = db.declare_war(clan['clan_id'], context.user_data['enemy_clan_id'], rating)
                if result:
                    await update.message.reply_text(f"⚔ Война завершена!\n🏆 Победитель: {result['clan1_name'] if result['winner_id'] == clan['clan_id'] else result['clan2_name']}")
                context.user_data.clear()
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("❌ Неверная ставка!")
                return WAITING_FOR_WAR_RATING
        
        if 'clan_msg_to' in context.user_data:
            try:
                context.user_data['clan_msg_to'] = int(text)
                context.user_data['waiting_clan_msg_text'] = True
                await update.message.reply_text("Текст сообщения:")
                return WAITING_FOR_CLAN_MSG_TEXT
            except ValueError:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_CLAN_MSG_CLAN
        
        if 'waiting_clan_msg_text' in context.user_data:
            clan = db.get_user_clan(user.id)
            db.add_clan_message(clan['clan_id'], context.user_data['clan_msg_to'], user.id, text)
            await update.message.reply_text("✅ Отправлено!")
            context.user_data.clear()
            return ConversationHandler.END
        
        if 'waiting_invite' in context.user_data:
            try:
                invite_id = int(text)
                clan = db.get_user_clan(user.id)
                db.join_clan(invite_id, clan['clan_id'])
                await update.message.reply_text("✅ Приглашен!")
                context.user_data.clear()
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_INVITE_USER
        
        return ConversationHandler.END


def main():
    print("🤖 Запуск Fluxy бота...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
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
        "ask": Handlers.ask, "backup": Handlers.backup_command,
    }
    
    for command, handler in commands.items():
        application.add_handler(CommandHandler(command, handler))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, Handlers.welcome_new_member), group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.antispam_check), group=1)
    
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
            CallbackQueryHandler(Handlers.button_handler, pattern="^find_clan_btn$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^give_reward_btn$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^transfer_clan$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^delete_clan$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^leave_clan_btn$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^report_btn$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^question_btn$"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^accept_report_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^reject_report_btn_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^accept_question_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^reject_question_btn_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^rank_access_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^toggle_access_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^rename_level_"),
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
            WAITING_FOR_REWARD_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_REWARD_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_TRANSFER_CLAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_RENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_REPORT_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
            WAITING_FOR_QUESTION_ANSWER: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.text_handler)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(conv_handler)
    
    application.add_handler(CallbackQueryHandler(Handlers.button_handler))
    
    print("✅ Бот запущен!")
    print(f"👑 Основатель: {SUPER_ADMIN_ID}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()