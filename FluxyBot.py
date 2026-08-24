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
    """База данных на JSONBin без SQLite"""
    
    def __init__(self):
        self.local_file = "backup_local.json"
        self.data = {}
        self.load_data()
    
    def load_data(self):
        """Загрузка данных из локального файла или JSONBin"""
        # Пробуем локальный файл
        try:
            with open(self.local_file, 'r') as f:
                self.data = json.load(f)
                print("✅ Загружено из локального файла")
                return
        except:
            pass
        
        # Пробуем JSONBin
        try:
            response = requests.get(JSONBIN_URL, headers=JSONBIN_HEADERS, timeout=5)
            if response.status_code == 200:
                self.data = response.json().get("record", {})
                print("✅ Загружено из JSONBin")
                return
        except Exception as e:
            print(f"❌ Ошибка загрузки из JSONBin: {e}")
        
        # Пустые данные
        self.data = {
            "users": [],
            "bot_admins": [],
            "support_agents": [],
            "chats": [],
            "clans": [],
            "bot_blacklist": [],
            "access_settings": [],
            "reports": [],
            "questions": [],
            "chat_messages": [],
            "clan_bonus_usage": [],
        }
        print("✅ Создана пустая база данных")
    
    def save_data(self):
        """Сохранение в локальный файл и JSONBin"""
        # Локально
        try:
            with open(self.local_file, 'w') as f:
                json.dump(self.data, f)
        except:
            pass
        
        # JSONBin
        try:
            response = requests.put(JSONBIN_URL, headers=JSONBIN_HEADERS, json=self.data, timeout=5)
            if response.status_code == 200:
                print("✅ Сохранено в JSONBin")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
    
    # Методы для пользователей
    def add_user(self, user_id, username, first_name):
        for user in self.data["users"]:
            if user["user_id"] == user_id:
                return
        self.data["users"].append({
            "user_id": user_id,
            "username": username or "",
            "first_name": first_name or "Пользователь",
            "clan_id": None,
            "warnings": 0,
            "registration_date": datetime.now().isoformat()
        })
        self.save_data()
    
    def get_user(self, user_id):
        for user in self.data["users"]:
            if user["user_id"] == user_id:
                return user
        return None
    
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
            "user_id": user_id,
            "level": level,
            "added_by": added_by,
            "added_date": datetime.now().isoformat()
        })
        self.save_data()
    
    def remove_bot_admin(self, user_id):
        self.data["bot_admins"] = [a for a in self.data["bot_admins"] if a["user_id"] != user_id]
        self.save_data()
    
    def get_all_bot_admins(self):
        admins = []
        for admin in self.data["bot_admins"]:
            user = self.get_user(admin["user_id"])
            admins.append({
                "user_id": admin["user_id"],
                "level": admin["level"],
                "username": user["username"] if user else "",
                "first_name": user["first_name"] if user else "Пользователь"
            })
        return sorted(admins, key=lambda x: x["level"], reverse=True)
    
    def update_bot_admin_level(self, user_id, level):
        for admin in self.data["bot_admins"]:
            if admin["user_id"] == user_id:
                admin["level"] = level
                self.save_data()
                return
    
    def add_agent(self, user_id, level):
        for agent in self.data["support_agents"]:
            if agent["user_id"] == user_id:
                agent["level"] = level
                self.save_data()
                return
        self.data["support_agents"].append({
            "user_id": user_id,
            "level": level,
            "status": "offline",
            "answered_questions": 0
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
        agents = []
        for agent in self.data["support_agents"]:
            user = self.get_user(agent["user_id"])
            agents.append({
                "user_id": agent["user_id"],
                "level": agent["level"],
                "status": agent.get("status", "offline"),
                "answered_questions": agent.get("answered_questions", 0),
                "first_name": user["first_name"] if user else "Агент"
            })
        return agents
    
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
            "clan_id": clan_id,
            "name": name,
            "leader_id": leader_id,
            "rating": 0,
            "entry_type": "open",
            "created_date": datetime.now().isoformat(),
            "total_members": 1,
            "wins": 0,
            "losses": 0
        })
        self.join_clan(leader_id, clan_id)
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
                user["clan_join_date"] = datetime.now().isoformat()
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
        members = []
        for user in self.data["users"]:
            if user.get("clan_id") == clan_id:
                members.append(user)
        return members
    
    def add_clan_rating(self, clan_id, rating):
        for clan in self.data["clans"]:
            if clan["clan_id"] == clan_id:
                clan["rating"] = clan.get("rating", 0) + rating
                self.save_data()
                return
    
    def get_top_clans(self, limit=10):
        clans = sorted(self.data["clans"], key=lambda x: (x.get("rating", 0), x.get("total_members", 0)), reverse=True)
        return clans[:limit]
    
    def update_clan_entry_type(self, clan_id, entry_type):
        for clan in self.data["clans"]:
            if clan["clan_id"] == clan_id:
                clan["entry_type"] = entry_type
                self.save_data()
                return
    
    # Черный список
    def add_to_blacklist(self, user_id, reason, added_by):
        self.data["bot_blacklist"].append({
            "user_id": user_id,
            "reason": reason,
            "date": datetime.now().isoformat(),
            "added_by": added_by
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
            "report_id": report_id,
            "user_id": user_id,
            "reported_user_id": reported_user_id,
            "reason": reason,
            "date": datetime.now().isoformat(),
            "status": "pending",
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
            "question_id": question_id,
            "user_id": user_id,
            "text": text,
            "date": datetime.now().isoformat(),
            "status": "pending"
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
                chat["title"] = title
                self.save_data()
                return
        self.data["chats"].append({
            "chat_id": chat_id,
            "title": title or "Чат",
            "welcome_enabled": 0,
            "welcome_text": None,
            "antispam_enabled": 0,
            "antispam_seconds": 5,
            "antispam_max_messages": 5
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
        return ranks.get(level, f"Уровень {level}")
    
    def get_chat_rank_name(self, level):
        ranks = {0: "Пользователь", 1: "Младший модератор", 2: "Модератор", 3: "Старший модератор", 4: "Младший админ", 5: "Админ", 6: "Старший админ", 7: "Главный админ", 8: "Заместитель владельца", 9: "Сооснователь", 10: "Владелец"}
        return ranks.get(level, f"Уровень {level}")
    
    def get_agent_rank_name(self, level):
        ranks = {1: "Младший агент", 2: "Агент", 3: "Старший агент"}
        return ranks.get(level, f"Уровень {level}")
    
    def update_bot_rank_name(self, level, name):
        self.data.setdefault("bot_rank_names", {})[str(level)] = name
        self.save_data()
    
    def update_agent_rank_name(self, level, name):
        self.data.setdefault("agent_rank_names", {})[str(level)] = name
        self.save_data()
    
    def update_chat_rank_name(self, level, name):
        self.data.setdefault("chat_rank_names", {})[str(level)] = name
        self.save_data()
    
    # Доступ
    def set_access_level(self, setting_type, setting_name, min_level):
        self.data.setdefault("access_settings", []).append({
            "type": setting_type,
            "name": setting_name,
            "min_level": min_level
        })
        self.save_data()
    
    def get_access_level(self, setting_type, setting_name):
        for setting in self.data.get("access_settings", []):
            if setting["type"] == setting_type and setting["name"] == setting_name:
                return setting["min_level"]
        return 10
    
    # Статистика
    def get_total_stats(self):
        return (
            len(self.data["users"]),
            len(self.data["chats"]),
            len(self.data["clans"]),
            len(self.data["bot_admins"]),
            len(self.data["support_agents"]),
            len(self.data["bot_blacklist"]),
            len(self.data.get("chat_messages", []))
        )
    
    def add_message(self, user_id, chat_id):
        self.data.setdefault("chat_messages", []).append({
            "user_id": user_id,
            "chat_id": chat_id,
            "message_time": datetime.now().isoformat()
        })
        # Не сохраняем каждое сообщение для скорости
    
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
            "user_id": user_id,
            "from_user_id": from_user_id,
            "text": text,
            "date": datetime.now().isoformat()
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
            if usage["clan_id"] == clan_id and usage["user_id"] == user_id and usage["date"] == today:
                return False
        return True
    
    def use_clan_bonus(self, user_id, clan_id):
        today = datetime.now().strftime("%Y-%m-%d")
        self.data.setdefault("clan_bonus_usage", []).append({
            "clan_id": clan_id,
            "user_id": user_id,
            "date": today
        })
        self.save_data()
    
    def get_all_users(self):
        return [user["user_id"] for user in self.data["users"]]


# Создание экземпляра
db = Database()

def check_bot_access(user_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_bot_admin_level(user_id)
    required_level = db.get_access_level('bot', function)
    return user_level >= required_level

def check_chat_access(user_id, chat_id, function):
    if user_id == SUPER_ADMIN_ID:
        return True
    user_level = db.get_bot_admin_level(user_id)
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

    @staticmethod
    def bot_access_functions():
        keyboard = [
            [InlineKeyboardButton("👥 Управление админами", callback_data="bot_access_manage_admins")],
            [InlineKeyboardButton("🔰 Управление агентами", callback_data="bot_access_manage_agents")],
            [InlineKeyboardButton("🚫 Черный список", callback_data="bot_access_blacklist")],
            [InlineKeyboardButton("⭐️ Выдача репутации", callback_data="bot_access_give_clan_rep")],
            [InlineKeyboardButton("🗂 Просмотр чатов", callback_data="bot_access_view_chats")],
            [InlineKeyboardButton("📊 Статистика", callback_data="bot_access_stats")],
            [InlineKeyboardButton("📨 Рассылка", callback_data="bot_access_broadcast")],
            [InlineKeyboardButton("❗️ Просмотр жалоб", callback_data="bot_access_view_reports")],
            [InlineKeyboardButton("🎁 Выдача наград", callback_data="bot_access_give_reward")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def agent_access_functions():
        keyboard = [
            [InlineKeyboardButton("❓ Просмотр вопросов", callback_data="agent_access_view_questions")],
            [InlineKeyboardButton("✉️ Ответ на вопросы", callback_data="agent_access_answer_questions")],
            [InlineKeyboardButton("📊 Статистика агента", callback_data="agent_access_hstats")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def chat_access_functions():
        keyboard = [
            [InlineKeyboardButton("🔨 Бан", callback_data="chat_access_ban")],
            [InlineKeyboardButton("🔓 Разбан", callback_data="chat_access_unban")],
            [InlineKeyboardButton("🔇 Мут", callback_data="chat_access_mute")],
            [InlineKeyboardButton("🔊 Размут", callback_data="chat_access_unmute")],
            [InlineKeyboardButton("⚠️ Предупреждение", callback_data="chat_access_warn")],
            [InlineKeyboardButton("✅ Снятие предупреждения", callback_data="chat_access_unwarn")],
            [InlineKeyboardButton("👑 Назначение админов", callback_data="chat_access_setadm")],
            [InlineKeyboardButton("👋 Приветствие", callback_data="chat_access_welcome_settings")],
            [InlineKeyboardButton("🚫 Антиспам", callback_data="chat_access_antispam_settings")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def access_levels():
        keyboard = [
            [InlineKeyboardButton("1", callback_data="set_level_1"), InlineKeyboardButton("2", callback_data="set_level_2")],
            [InlineKeyboardButton("3", callback_data="set_level_3"), InlineKeyboardButton("4", callback_data="set_level_4")],
            [InlineKeyboardButton("5", callback_data="set_level_5"), InlineKeyboardButton("6", callback_data="set_level_6")],
            [InlineKeyboardButton("7", callback_data="set_level_7"), InlineKeyboardButton("8", callback_data="set_level_8")],
            [InlineKeyboardButton("9", callback_data="set_level_9"), InlineKeyboardButton("10", callback_data="set_level_10")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")]
        ]
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
        user = update.effective_user
        user_id = user.id
        bot_level = db.get_bot_admin_level(user_id)
        
        text = """📋 Справка по командам:
━━━━━━━━━━━━━━━━

👤 Основные команды:
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
/ban - Забанить
/unban - Разбанить
/mute - Замутить
/unmute - Размутить
/warn - Предупредить
/unwarn - Снять предупреждение
/setadm - Назначить админа"""
        
        if bot_level >= 5:
            text += """

⭐️ Админ команды:
/permban - Бан в боте
/unperm - Разбан в боте
/broadcast - Рассылка
/reports - Просмотр жалоб
/give_rep - Выдать репутацию"""
        
        if bot_level >= 10:
            text += """

👑 Команды Основателя:
/rename_bot_rank - Переименовать ранг бота
/rename_agent_rank - Переименовать ранг агента
/rename_chat_rank - Переименовать ранг чата
/backup - Резервное копирование"""
        
        agent_level = db.get_agent_level(user_id)
        if agent_level >= 1:
            text += """

🔰 Команды агента:
/hstats - Статистика агента
/answer_question - Ответить на вопрос
/reject_question - Отклонить вопрос"""
        
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
        
        if not db.can_use_clan_bonus(user.id, clan[0]):
            await update.message.reply_text("❌ Вы уже использовали бонус клана сегодня!\n🕐 Приходите завтра!")
            return
        
        members = db.get_clan_members(clan[0])
        bonus = len(members)
        db.add_clan_rating(clan[0], bonus)
        db.use_clan_bonus(user.id, clan[0])
        await update.message.reply_text(f"✅ Клан получил +{bonus} рейтинга!\n📅 Следующий бонус доступен завтра!")

    @staticmethod
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message.reply_to_message:
            await update.message.reply_text("❌ Ответьте на сообщение!")
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
            is_leader = clan[2] == user.id
            text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan[0]}
🛡 Название: {clan[1]}
🏆 Рейтинг: {clan[3]}
👥 Участников: {clan[6]}
🏅 Побед: {clan[7]}
💀 Поражений: {clan[8]}"""
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
            text += f"{i}. 🛡 {clan[1]}\n   🆔 ID: {clan[0]}\n   🏆 Рейтинг: {clan[2]}\n   👥 Участников: {clan[4]}\n━━━━━━━━━━━━━━━━\n"
        
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
        
        await update.message.reply_text(f"✅ Жалоба отправлена!\n\n👤 Нарушитель: {target.first_name}\n🆔 ID: {target.id}\n📝 Причина: {reason}\n🔗 Ссылка: {message_link}\n🕐 Время: {datetime.now().strftime('%H:%M:%S')}")
        
        admins = db.get_all_bot_admins()
        for admin in admins:
            try:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Принять", callback_data=f"accept_report_{report_id}"),
                     InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_report_btn_{report_id}")]
                ])
                await context.bot.send_message(
                    admin[0],
                    f"❗️ Новая жалоба!\n\n"
                    f"👤 От: {update.effective_user.first_name}\n"
                    f"🆔 ID отправителя: {update.effective_user.id}\n"
                    f"🎯 Нарушитель: {target.first_name}\n"
                    f"🆔 ID нарушителя: {target.id}\n"
                    f"📝 Причина: {reason}\n"
                    f"🔗 Ссылка: {message_link}\n"
                    f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
                    reply_markup=keyboard
                )
            except:
                pass

    @staticmethod
    async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Эта команда работает только в группе!")
            return
        
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
        
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Эта команда работает только в группе!")
            return
        
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
        
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Эта команда работает только в группе!")
            return
        
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
        
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Эта команда работает только в группе!")
            return
        
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
        
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Эта команда работает только в группе!")
            return
        
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
        
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Эта команда работает только в группе!")
            return
        
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
        
        if update.effective_chat.type == 'private':
            await update.message.reply_text("❌ Эта команда работает только в группе!")
            return
        
        if not check_chat_access(user.id, chat_id, 'setadm'):
            await update.message.reply_text("❌ Недостаточно прав!")
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ /setadm <ID> <уровень>")
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
            
            text += "\nИспользуйте кнопки в личных сообщениях!"
            await update.message.reply_text(text)
        
        elif is_agent:
            questions = db.get_pending_questions()
            if not questions:
                await update.message.reply_text("✅ Нет новых вопросов!")
                return
            
            text = "❓ Вопросы:\n\n"
            for question in questions:
                text += f"🆔 #{question[0]}\n👤 От: {question[6]}\n💬 Вопрос: {question[2]}\n━━━━━━━━━━━━━━━━\n"
            
            text += "\nИспользуйте кнопки в личных сообщениях!"
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
    async def rename_bot_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if db.get_bot_admin_level(user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /rename_bot_rank <уровень> <название>")
            return
        try:
            level = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный уровень!")
            return
        name = " ".join(context.args[1:])
        db.update_bot_rank_name(level, name)
        await update.message.reply_text(f"✅ Ранг {level} → «{name}»!")

    @staticmethod
    async def rename_agent_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if db.get_bot_admin_level(user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /rename_agent_rank <уровень> <название>")
            return
        try:
            level = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный уровень!")
            return
        name = " ".join(context.args[1:])
        db.update_agent_rank_name(level, name)
        await update.message.reply_text(f"✅ Уровень {level} → «{name}»!")

    @staticmethod
    async def rename_chat_rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if db.get_bot_admin_level(user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        if len(context.args) < 2:
            await update.message.reply_text("❌ /rename_chat_rank <уровень> <название>")
            return
        try:
            level = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный уровень!")
            return
        name = " ".join(context.args[1:])
        db.update_chat_rank_name(level, name)
        await update.message.reply_text(f"✅ Ранг {level} → «{name}»!")

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
        question_id = db.add_question(user.id, question)
        await update.message.reply_text("✅ Вопрос отправлен агентам!")
        
        agents = db.get_all_agents()
        for agent in agents:
            try:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Принять", callback_data=f"accept_question_{question_id}"),
                     InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_question_btn_{question_id}")]
                ])
                await context.bot.send_message(
                    agent[0],
                    f"❓ Новый вопрос!\n👤 От: {user.first_name}\n🆔 ID: {user.id}\n💬 Вопрос: {question}\n🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
                    reply_markup=keyboard
                )
            except:
                pass

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
        
        # Навигация назад
        if data == "back_to_start":
            user_id = user.id
            bot_rank_level = db.get_bot_admin_level(user_id)
            
            is_chat_owner = False
            if update.effective_chat.type != 'private':
                chat_id = update.effective_chat.id
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
🛡️ Клан: {clan[1] if clan else 'Нет'}
🏆 Рейтинг: {clan[3] if clan else 0}"""
            await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
            return ConversationHandler.END
        
        elif data == "back_to_clan":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan[2] == user.id
                text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan[0]}
🛡 Название: {clan[1]}
🏆 Рейтинг: {clan[3]}
👥 Участников: {clan[6]}
🏅 Побед: {clan[7]}
💀 Поражений: {clan[8]}"""
                await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
            return ConversationHandler.END
        
        # Профиль и награды
        elif data == "profile":
            clan = db.get_user_clan(user.id)
            text = f"""👤 Профиль
━━━━━━━━━━━━━━━━

🆔 ID: {user.id}
🎖️ Ранг: {db.get_bot_rank_name(db.get_bot_admin_level(user.id))}
🛡️ Клан: {clan[1] if clan else 'Нет'}
🏆 Рейтинг: {clan[3] if clan else 0}"""
            await query.message.edit_text(text, reply_markup=Keyboards.profile_menu())
        
        elif data == "my_rewards":
            rewards = db.get_user_rewards(user.id)
            text = f"🏆 Ваши награды:\n━━━━━━━━━━━━━━━━\n\n"
            if not rewards:
                text += "Нет наград"
            for reward in rewards:
                text += f"🎁 {reward[3]}\n👤 От: {reward[8] or 'Пользователь'}\n📅 {reward[4][:10]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_profile())
        
        elif data == "give_reward_btn":
            context.user_data['giving_reward'] = True
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_REWARD_USER
        
        # Статистика чата
        elif data == "chat_stats":
            await query.message.edit_text("📊 Статистика чата\n\nВыберите период:", reply_markup=Keyboards.chat_stats_menu())
        
        elif data == "top_day":
            top = db.get_top_messages(chat_id, 'day')
            text = "📊 Топ дня по сообщениям:\n━━━━━━━━━━━━━━━━\n\n"
            if not top:
                text += "Нет данных"
            for i, user_stat in enumerate(top, 1):
                text += f"{i}. {user_stat[1] or 'Пользователь'}\n💬 Сообщений: {user_stat[2]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "top_week":
            top = db.get_top_messages(chat_id, 'week')
            text = "📊 Топ недели по сообщениям:\n━━━━━━━━━━━━━━━━\n\n"
            if not top:
                text += "Нет данных"
            for i, user_stat in enumerate(top, 1):
                text += f"{i}. {user_stat[1] or 'Пользователь'}\n💬 Сообщений: {user_stat[2]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "top_all":
            top = db.get_top_messages(chat_id, 'all')
            text = "📊 Весь топ по сообщениям:\n━━━━━━━━━━━━━━━━\n\n"
            if not top:
                text += "Нет данных"
            for i, user_stat in enumerate(top, 1):
                text += f"{i}. {user_stat[1] or 'Пользователь'}\n💬 Сообщений: {user_stat[2]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        # Клан
        elif data == "clan_menu":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan[2] == user.id
                text = f"""🛡 Ваш клан
━━━━━━━━━━━━━━━━

🆔 ID: {clan[0]}
🛡 Название: {clan[1]}
🏆 Рейтинг: {clan[3]}
👥 Участников: {clan[6]}
🏅 Побед: {clan[7]}
💀 Поражений: {clan[8]}"""
                await query.message.edit_text(text, reply_markup=Keyboards.my_clan_menu(is_leader))
            else:
                await query.message.edit_text("🛡 Кланы\n\nВыберите действие:", reply_markup=Keyboards.clan_menu())
        
        elif data == "clan_settings":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                await query.message.edit_text("⚙️ Настройки клана:", reply_markup=Keyboards.clan_settings_menu())
        
        elif data == "clan_requests":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                requests = db.get_clan_requests(clan[0])
                text = f"📋 Заявки в клан:\n━━━━━━━━━━━━━━━━\n\n"
                if not requests:
                    text += "Нет заявок"
                for req in requests:
                    text += f"🆔 Заявка: {req[0]}\n👤 {req[7] or 'Пользователь'}\n🆔 ID: {req[2]}\n━━━━━━━━━━━━━━━━\n"
                text += "\n/accept_request <ID> - принять\n/reject_request <ID> - отклонить"
                await query.message.edit_text(text, reply_markup=Keyboards.back_to_clan())
        
        elif data == "clan_members":
            clan = db.get_user_clan(user.id)
            if clan:
                is_leader = clan[2] == user.id
                members = db.get_clan_members(clan[0])
                text = f"👥 Участники клана «{clan[1]}»:\n━━━━━━━━━━━━━━━━\n\n"
                for member in members:
                    text += f"👤 {member[2] or 'Пользователь'}\n🆔 ID: {member[0]}\n━━━━━━━━━━━━━━━━\n"
                await query.message.edit_text(text, reply_markup=Keyboards.clan_members_menu(is_leader))
        
        elif data == "clan_messages":
            clan = db.get_user_clan(user.id)
            if clan:
                messages = db.get_clan_messages(clan[0])
                text = f"✉️ Сообщения клана:\n━━━━━━━━━━━━━━━━\n\n"
                if not messages:
                    text += "Нет сообщений"
                for msg in messages[:10]:
                    text += f"📩 От: {msg[7] or 'Клан'}\n💬 {msg[4]}\n📅 {msg[5][:10]}\n━━━━━━━━━━━━━━━━\n"
                await query.message.edit_text(text, reply_markup=Keyboards.back_to_clan())
        
        elif data == "clan_entry":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                await query.message.edit_text("🔒 Выберите тип входа:", reply_markup=Keyboards.clan_entry_menu())
        
        elif data == "entry_open":
            clan = db.get_user_clan(user.id)
            db.update_clan_entry_type(clan[0], 'open')
            await query.message.reply_text("✅ Вход в клан открыт!")
        
        elif data == "entry_closed":
            clan = db.get_user_clan(user.id)
            db.update_clan_entry_type(clan[0], 'closed')
            await query.message.reply_text("✅ Вход в клан закрыт!")
        
        elif data == "entry_request":
            clan = db.get_user_clan(user.id)
            db.update_clan_entry_type(clan[0], 'request')
            await query.message.reply_text("✅ Вход по заявкам!")
        
        elif data == "declare_war":
            clan = db.get_user_clan(user.id)
            if not clan or clan[2] != user.id:
                await query.message.reply_text("❌ Только лидер!")
                return ConversationHandler.END
            context.user_data['war_clan_id'] = True
            await query.message.reply_text("Отправьте ID вражеского клана:")
            return WAITING_FOR_WAR_CLAN_ID
        
        elif data == "message_clan":
            clan = db.get_user_clan(user.id)
            if not clan or clan[2] != user.id:
                await query.message.reply_text("❌ Только лидер!")
                return ConversationHandler.END
            context.user_data['clan_msg_to'] = True
            await query.message.reply_text("Отправьте ID клана:")
            return WAITING_FOR_CLAN_MSG_CLAN
        
        elif data == "invite_member":
            clan = db.get_user_clan(user.id)
            if not clan:
                await query.message.reply_text("❌ Вы не в клане!")
                return ConversationHandler.END
            context.user_data['waiting_invite'] = True
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_INVITE_USER
        
        elif data == "transfer_clan":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                context.user_data['transfer_clan'] = True
                await query.message.reply_text("Отправьте ID нового лидера клана:")
                return WAITING_FOR_TRANSFER_CLAN
        
        elif data == "delete_clan":
            clan = db.get_user_clan(user.id)
            if clan and clan[2] == user.id:
                db.cursor.execute("UPDATE users SET clan_id = NULL WHERE clan_id = ?", (clan[0],))
                db.cursor.execute("DELETE FROM clans WHERE clan_id = ?", (clan[0],))
                db.cursor.execute("DELETE FROM clan_requests WHERE clan_id = ?", (clan[0],))
                db.cursor.execute("DELETE FROM clan_messages WHERE from_clan_id = ? OR to_clan_id = ?", (clan[0], clan[0]))
                db.conn.commit()
                await query.message.edit_text("✅ Клан удален!", reply_markup=Keyboards.clan_menu())
        
        elif data == "leave_clan_btn":
            clan = db.get_user_clan(user.id)
            if clan:
                if clan[2] == user.id:
                    await query.message.reply_text("❌ Лидер не может покинуть клан!")
                else:
                    db.leave_clan(user.id)
                    await query.message.edit_text(f"✅ Вы покинули клан «{clan[1]}»!", reply_markup=Keyboards.clan_menu())
            else:
                await query.message.reply_text("❌ Вы не в клане!")
            return ConversationHandler.END
        
        elif data == "find_clan_btn":
            context.user_data['waiting_clan_id'] = True
            await query.message.reply_text("Отправьте ID клана:")
            return WAITING_FOR_CLAN_ID
        
        elif data == "create_clan_btn":
            await query.message.reply_text("Используйте команду:\n/create_clan <название>")
        
        elif data == "clan_list_btn":
            await query.message.reply_text("Используйте команду:\n/clan_top")
        
        # Админ панель бота
        elif data == "admin_panel":
            if db.get_bot_admin_level(user.id) < 1:
                await query.message.reply_text("❌ Недостаточно прав!")
                return ConversationHandler.END
            await query.message.edit_text("⭐️ Админ панель бота", reply_markup=Keyboards.admin_panel())
        
        elif data == "admins_list":
            admins = db.get_all_bot_admins()
            text = "👥 Админы бота:\n━━━━━━━━━━━━━━━━\n\n"
            for admin in admins:
                text += f"👤 {admin[5] or 'Пользователь'}\n🆔 ID: {admin[0]}\n📊 Уровень: {admin[1]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.admin_manage_menu())
        
        elif data == "add_admin":
            context.user_data['action'] = 'add_admin'
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "remove_admin":
            context.user_data['action'] = 'remove_admin'
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "change_admin_level":
            context.user_data['action'] = 'change_admin_level'
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_ADMIN_ID
        
        elif data == "agents_manage":
            agents = db.get_all_agents()
            text = "🔰 Агенты поддержки:\n━━━━━━━━━━━━━━━━\n\n"
            for agent in agents:
                text += f"👤 {agent[6] or 'Агент'}\n🆔 ID: {agent[0]}\n📊 Уровень: {agent[1]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.agent_manage_menu())
        
        elif data == "add_agent":
            context.user_data['action'] = 'add_agent'
            await query.message.reply_text("Отправьте ID агента:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "remove_agent":
            context.user_data['action'] = 'remove_agent'
            await query.message.reply_text("Отправьте ID агента:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "change_agent_level":
            context.user_data['action'] = 'change_agent_level'
            await query.message.reply_text("Отправьте ID агента:")
            return WAITING_FOR_AGENT_ID
        
        elif data == "bot_blacklist":
            blacklist = db.get_blacklist()
            text = "🚫 Черный список бота:\n━━━━━━━━━━━━━━━━\n\n"
            if not blacklist:
                text += "Список пуст"
            for item in blacklist:
                text += f"👤 {item[5] or 'Пользователь'}\n🆔 ID: {item[0]}\n📝 Причина: {item[1]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.blacklist_menu())
        
        elif data == "blacklist_add":
            context.user_data['action'] = 'blacklist_add'
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_BLACKLIST_ID
        
        elif data == "blacklist_remove":
            context.user_data['action'] = 'blacklist_remove'
            await query.message.reply_text("Отправьте ID пользователя:")
            return WAITING_FOR_BLACKLIST_ID
        
        elif data == "blacklist_list":
            blacklist = db.get_blacklist()
            text = "🚫 Черный список:\n━━━━━━━━━━━━━━━━\n\n"
            for item in blacklist:
                text += f"🆔 {item[0]}: {item[1]}\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "broadcast_menu":
            await query.message.edit_text("📨 Рассылка", reply_markup=Keyboards.broadcast_menu())
        
        elif data == "broadcast_pm":
            context.user_data['broadcast_type'] = 'pm'
            await query.message.reply_text("Отправьте текст рассылки:")
            return WAITING_FOR_BROADCAST_TEXT
        
        elif data == "broadcast_chats":
            context.user_data['broadcast_type'] = 'chats'
            await query.message.reply_text("Отправьте текст рассылки:")
            return WAITING_FOR_BROADCAST_TEXT
        
        elif data == "super_admin":
            await query.message.edit_text("👑 Супер админ функции", reply_markup=Keyboards.super_admin_menu())
        
        elif data == "bot_stats":
            total_users, total_chats, total_clans, total_admins, total_agents, total_blacklist, total_messages = db.get_total_stats()
            
            text = f"""📊 Статистика бота:
━━━━━━━━━━━━━━━━

👥 Пользователей: {total_users}
💬 Чатов: {total_chats}
🛡 Кланов: {total_clans}
👑 Админов: {total_admins}
🔰 Агентов: {total_agents}
🚫 В ЧС: {total_blacklist}
📨 Сообщений: {total_messages}"""
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "all_commands":
            user_id = user.id
            bot_level = db.get_bot_admin_level(user_id)
            
            text = """📋 Все команды бота:
━━━━━━━━━━━━━━━━

👤 Основные:
/start, /profile, /ping, /id, /help

🛡 Кланы:
/clan, /clan_top, /clan_bonus
/create_clan, /join_clan, /leave_clan

📝 Прочее:
/report, /stats, /ask"""
            
            if bot_level >= 1:
                text += """

🔨 Модерация:
/ban, /unban, /mute, /unmute
/warn, /unwarn, /setadm"""
            
            if bot_level >= 5:
                text += """

⭐️ Админ:
/permban, /unperm, /broadcast
/reports, /give_rep"""
            
            if bot_level >= 10:
                text += """

👑 Основатель:
/rename_bot_rank, /rename_agent_rank
/rename_chat_rank, /backup"""
            
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        # Ранги по кнопкам
        elif data == "bot_rank_names":
            context.user_data['rename_type'] = 'bot'
            await query.message.edit_text("Выберите уровень для переименования:", reply_markup=Keyboards.rank_levels('bot'))
        
        elif data == "agent_rank_names":
            context.user_data['rename_type'] = 'agent'
            await query.message.edit_text("Выберите уровень для переименования:", reply_markup=Keyboards.rank_levels('agent'))
        
        elif data == "chat_rank_names":
            context.user_data['rename_type'] = 'chat'
            await query.message.edit_text("Выберите уровень для переименования:", reply_markup=Keyboards.rank_levels('chat'))
        
        elif data.startswith("rename_level_"):
            level = int(data.replace("rename_level_", ""))
            context.user_data['rename_level'] = level
            await query.message.reply_text(f"Отправьте новое название для уровня {level}:")
            return WAITING_FOR_RENAME
        
        # ПРАВА ПО КНОПКАМ
        elif data == "bot_rank_settings":
            await query.message.edit_text("⚙️ Права рангов бота:\n\nВыберите функцию:", reply_markup=Keyboards.bot_access_functions())
        
        elif data.startswith("bot_access_"):
            function = data.replace("bot_access_", "")
            context.user_data['setting_type'] = 'bot'
            context.user_data['setting_name'] = function
            await query.message.edit_text(f"Выберите минимальный уровень для «{function}»:", reply_markup=Keyboards.access_levels())
        
        elif data == "agent_settings":
            await query.message.edit_text("⚙️ Права агентов:\n\nВыберите функцию:", reply_markup=Keyboards.agent_access_functions())
        
        elif data.startswith("agent_access_"):
            function = data.replace("agent_access_", "")
            context.user_data['setting_type'] = 'agent'
            context.user_data['setting_name'] = function
            await query.message.edit_text(f"Выберите минимальный уровень для «{function}»:", reply_markup=Keyboards.access_levels())
        
        elif data == "chat_rank_settings":
            await query.message.edit_text("⚙️ Права рангов чата:\n\nВыберите функцию:", reply_markup=Keyboards.chat_access_functions())
        
        elif data.startswith("chat_access_"):
            function = data.replace("chat_access_", "")
            context.user_data['setting_type'] = 'chat'
            context.user_data['setting_name'] = function
            await query.message.edit_text(f"Выберите минимальный уровень для «{function}»:", reply_markup=Keyboards.access_levels())
        
        elif data.startswith("set_level_"):
            level = int(data.replace("set_level_", ""))
            setting_type = context.user_data.get('setting_type')
            setting_name = context.user_data.get('setting_name')
            
            if setting_type and setting_name:
                db.set_access_level(setting_type, setting_name, level)
                await query.message.edit_text(
                    f"✅ Доступ установлен!\n\nТип: {setting_type}\nФункция: {setting_name}\nУровень: {level}",
                    reply_markup=Keyboards.back_to_start()
                )
                context.user_data.pop('setting_type', None)
                context.user_data.pop('setting_name', None)
            else:
                await query.message.edit_text("❌ Ошибка!", reply_markup=Keyboards.back_to_start())
            return ConversationHandler.END
        
        # Админ панель чата
        elif data == "chat_panel":
            await query.message.edit_text("👑 Админ панель чата", reply_markup=Keyboards.chat_panel())
        
        elif data == "chat_admins_list":
            admins = db.get_chat_admins(chat_id)
            text = "👥 Админы чата:\n━━━━━━━━━━━━━━━━\n\n"
            for admin in admins:
                text += f"👤 {admin[5] or 'Пользователь'}\n🆔 ID: {admin[0]}\n📊 Уровень: {admin[1]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "welcome_settings":
            welcome_settings = db.get_welcome_settings(chat_id)
            welcome_enabled = welcome_settings[0] if welcome_settings else 0
            await query.message.edit_text("👋 Настройки приветствия", reply_markup=Keyboards.welcome_settings_menu(welcome_enabled))
        
        elif data == "toggle_welcome":
            welcome_settings = db.get_welcome_settings(chat_id)
            current = welcome_settings[0] if welcome_settings else 0
            db.enable_welcome(chat_id, not current)
            welcome_settings = db.get_welcome_settings(chat_id)
            welcome_enabled = welcome_settings[0] if welcome_settings else 0
            await query.message.edit_text("👋 Настройки приветствия", reply_markup=Keyboards.welcome_settings_menu(welcome_enabled))
        
        elif data == "edit_welcome_text":
            context.user_data['editing_welcome'] = chat_id
            await query.message.reply_text("Отправьте новый текст приветствия:")
            return WAITING_FOR_WELCOME_TEXT
        
        elif data == "show_welcome":
            welcome_settings = db.get_welcome_settings(chat_id)
            if welcome_settings and welcome_settings[1]:
                await query.message.reply_text(f"Текущее приветствие:\n\n{welcome_settings[1]}")
            else:
                await query.message.reply_text("Приветствие не установлено")
        
        elif data == "antispam_settings":
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_seconds = antispam_settings[1] if antispam_settings else 5
            antispam_max = db.get_antispam_max_messages(chat_id)
            await query.message.edit_text("🚫 Настройки антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max))
        
        elif data == "toggle_antispam":
            antispam_settings = db.get_antispam_settings(chat_id)
            current = antispam_settings[0] if antispam_settings else 0
            db.enable_antispam(chat_id, not current)
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_seconds = antispam_settings[1] if antispam_settings else 5
            antispam_max = db.get_antispam_max_messages(chat_id)
            await query.message.edit_text("🚫 Настройки антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, antispam_seconds, antispam_max))
        
        elif data == "change_antispam_interval":
            await query.message.edit_text("⏱ Выберите интервал:", reply_markup=Keyboards.antispam_interval_menu())
        
        elif data == "change_antispam_messages":
            await query.message.edit_text("📊 Выберите максимум сообщений:", reply_markup=Keyboards.antispam_messages_menu())
        
        elif data.startswith("set_antispam_"):
            seconds = int(data.replace("set_antispam_", ""))
            db.set_antispam_seconds(chat_id, seconds)
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_max = db.get_antispam_max_messages(chat_id)
            await query.message.edit_text("🚫 Настройки антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, seconds, antispam_max))
        
        elif data.startswith("set_msg_"):
            max_messages = int(data.replace("set_msg_", ""))
            db.set_antispam_max_messages(chat_id, max_messages)
            antispam_settings = db.get_antispam_settings(chat_id)
            antispam_enabled = antispam_settings[0] if antispam_settings else 0
            antispam_seconds = antispam_settings[1] if antispam_settings else 5
            await query.message.edit_text("🚫 Настройки антиспама", reply_markup=Keyboards.antispam_settings_menu(antispam_enabled, antispam_seconds, max_messages))
        
        # Помощь
        elif data == "help_menu":
            await query.message.edit_text("🆘 Помощь:\n\nВыберите действие:", reply_markup=Keyboards.help_menu())
        
        elif data == "report_btn":
            if update.effective_chat.type == 'private':
                await query.message.reply_text("❌ Эта функция работает только в группе! Ответьте на сообщение нарушителя и напишите /report <причина>")
            else:
                await query.message.reply_text("📝 Чтобы отправить жалобу:\n1. Ответьте на сообщение нарушителя\n2. Напишите /report <причина>")
        
        elif data == "question_btn":
            context.user_data['asking_question'] = True
            await query.message.reply_text("❓ Задайте ваш вопрос:")
            return WAITING_FOR_QUESTION
        
        # Кнопки принятия/отклонения жалоб
        elif data.startswith("accept_report_"):
            report_id = int(data.replace("accept_report_", ""))
            context.user_data['answering_report'] = report_id
            await query.message.reply_text("Отправьте ответ на жалобу:")
            return WAITING_FOR_REPORT_ANSWER
        
        elif data.startswith("reject_report_btn_"):
            report_id = int(data.replace("reject_report_btn_", ""))
            db.update_report_status(report_id, 'rejected', user.id)
            await query.message.edit_text(f"✅ Жалоба #{report_id} отклонена!")
            return ConversationHandler.END
        
        # Кнопки принятия/отклонения вопросов
        elif data.startswith("accept_question_"):
            question_id = int(data.replace("accept_question_", ""))
            context.user_data['answering_question'] = question_id
            await query.message.reply_text("Отправьте ответ на вопрос:")
            return WAITING_FOR_QUESTION_ANSWER
        
        elif data.startswith("reject_question_btn_"):
            question_id = int(data.replace("reject_question_btn_", ""))
            db.update_question_status(question_id, 'rejected', user.id)
            await query.message.edit_text(f"✅ Вопрос #{question_id} отклонен!")
            return ConversationHandler.END
        
        elif data == "commands_menu":
            user_id = user.id
            bot_level = db.get_bot_admin_level(user_id)
            
            text = """📋 Все команды бота:
━━━━━━━━━━━━━━━━

👤 Основные:
/start, /profile, /ping, /id, /help

🛡 Кланы:
/clan, /clan_top, /clan_bonus
/create_clan, /join_clan, /leave_clan

📝 Прочее:
/report, /stats, /ask"""
            
            if bot_level >= 1:
                text += """

🔨 Модерация:
/ban, /unban, /mute, /unmute
/warn, /unwarn, /setadm"""
            
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "agents_list":
            agents = db.get_all_agents()
            text = "🔰 Агенты поддержки:\n━━━━━━━━━━━━━━━━\n\n"
            if not agents:
                text += "Нет агентов"
            for agent in agents:
                status = "🟢" if agent[2] == 'online' else "🔴"
                text += f"{status} {agent[6] or 'Агент'}\n📊 Уровень: {agent[1]}\n❓ Отвечено: {agent[3]}\n━━━━━━━━━━━━━━━━\n"
            await query.message.edit_text(text, reply_markup=Keyboards.back_to_start())
        
        elif data == "report":
            await query.message.reply_text("Используйте команду:\n/report <причина> (ответив на сообщение)")
        
        elif data == "question":
            await query.message.reply_text("Используйте команду:\n/ask <текст вопроса>")
        
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
                welcome_text = welcome_settings[1] or "Добро пожаловать, {name}!"
                welcome_text = welcome_text.replace("{name}", member.first_name or "Гость")
                welcome_text = welcome_text.replace("{id}", str(member.id))
                welcome_text = welcome_text.replace("{chat}", update.effective_chat.title or "Наш чат")
                try:
                    await update.message.reply_text(welcome_text)
                except Exception as e:
                    logger.error(f"Ошибка отправки приветствия: {e}")

    @staticmethod
    async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if db.get_bot_admin_level(user.id) < 10:
            await update.message.reply_text("❌ Только Основатель!")
            return
        
        status_message = await update.message.reply_text("📦 Выполняю резервное копирование...")
        
        try:
            if backup_manager.backup(db):
                await status_message.edit_text("✅ Резервное копирование успешно выполнено!")
            else:
                await status_message.edit_text("❌ Ошибка! Проверьте интернет.")
        except Exception as e:
            logger.error(f"Ошибка backup: {e}")
            await status_message.edit_text(f"❌ Критическая ошибка: {str(e)[:100]}")

    @staticmethod
    async def antispam_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        chat_id = update.effective_chat.id
        db.add_user(user.id, user.username, user.first_name)
        db.add_message(user.id, chat_id)
        
        chat_settings = db.get_antispam_settings(chat_id)
        if not chat_settings or chat_settings[0] != 1:
            return
        
        db.add_antispam_message(user.id, chat_id)
        recent_messages = db.get_recent_messages(user.id, chat_id, chat_settings[1])
        max_messages = db.get_antispam_max_messages(chat_id)
        
        if recent_messages > max_messages:
            try:
                await update.message.delete()
                warning_msg = await update.message.reply_text(f"⚠️ {user.first_name}, не спамьте! Лимит: {max_messages} сообщений за {chat_settings[1]} сек.")
                await asyncio.sleep(5)
                await warning_msg.delete()
            except Exception as e:
                logger.error(f"Ошибка антиспама: {e}")
                
#==================#
#5 ЧАСТЬ | Main           #
#==================#

    @staticmethod
    async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        text = update.message.text
        
        if db.is_blacklisted(user.id):
            await update.message.reply_text("❌ Вы в черном списке бота!")
            return ConversationHandler.END
        
        if 'editing_welcome' in context.user_data:
            chat_id = context.user_data['editing_welcome']
            db.set_welcome_text(chat_id, text)
            await update.message.reply_text(f"✅ Приветствие установлено!")
            context.user_data.pop('editing_welcome', None)
            return ConversationHandler.END
        
        if 'asking_question' in context.user_data:
            question = text
            question_id = db.add_question(user.id, question)
            await update.message.reply_text("✅ Вопрос отправлен агентам!")
            context.user_data.pop('asking_question', None)
            
            agents = db.get_all_agents()
            for agent in agents:
                try:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Принять", callback_data=f"accept_question_{question_id}"),
                         InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_question_btn_{question_id}")]
                    ])
                    await context.bot.send_message(
                        agent[0],
                        f"❓ Новый вопрос!\n👤 От: {user.first_name}\n🆔 ID: {user.id}\n💬 Вопрос: {question}\n🕐 Время: {datetime.now().strftime('%H:%M:%S')}",
                        reply_markup=keyboard
                    )
                except:
                    pass
            return ConversationHandler.END
        
        if 'answering_report' in context.user_data:
            report_id = context.user_data['answering_report']
            answer = text
            db.update_report_status(report_id, 'answered', user.id)
            
            db.cursor.execute("SELECT user_id FROM reports WHERE report_id = ?", (report_id,))
            result = db.cursor.fetchone()
            if result:
                try:
                    await context.bot.send_message(result[0], f"✅ Ваша жалоба рассмотрена!\n📝 Ответ: {answer}")
                except:
                    pass
            
            await update.message.reply_text(f"✅ Ответ отправлен!")
            context.user_data.pop('answering_report', None)
            return ConversationHandler.END
        
        if 'answering_question' in context.user_data:
            question_id = context.user_data['answering_question']
            answer = text
            db.update_question_status(question_id, 'answered', user.id, answer)
            
            db.cursor.execute("SELECT user_id FROM questions WHERE question_id = ?", (question_id,))
            result = db.cursor.fetchone()
            if result:
                try:
                    await context.bot.send_message(result[0], f"❓ Ответ на ваш вопрос:\n\n{answer}")
                except:
                    pass
            
            await update.message.reply_text(f"✅ Ответ отправлен!")
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
                    await update.message.reply_text("❌ Неверный ID! Введите число:")
                    return WAITING_FOR_REWARD_USER
            else:
                target_id = context.user_data.get('reward_target')
                db.add_reward(target_id, user.id, text)
                await update.message.reply_text(f"✅ Награда выдана пользователю {target_id}!")
                try:
                    await context.bot.send_message(target_id, f"🎁 Вы получили награду!\n📝 {text}")
                except:
                    pass
                context.user_data.clear()
                return ConversationHandler.END
        
        if 'waiting_clan_id' in context.user_data:
            try:
                clan_id = int(text)
                clan = db.get_clan_by_id(clan_id)
                if not clan:
                    await update.message.reply_text("❌ Клан не найден! Попробуйте еще раз:")
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
                
            except ValueError:
                await update.message.reply_text("❌ Неверный ID! Введите числовой ID:")
                return WAITING_FOR_CLAN_ID
        
        if 'transfer_clan' in context.user_data:
            try:
                new_leader_id = int(text)
                clan = db.get_user_clan(user.id)
                new_leader_clan = db.get_user_clan(new_leader_id)
                if not new_leader_clan or new_leader_clan[0] != clan[0]:
                    await update.message.reply_text("❌ Пользователь не в вашем клане!")
                    return WAITING_FOR_TRANSFER_CLAN
                db.cursor.execute("UPDATE clans SET leader_id = ? WHERE clan_id = ?", (new_leader_id, clan[0]))
                db.conn.commit()
                await update.message.reply_text(f"✅ Клан передан пользователю {new_leader_id}!")
                context.user_data.pop('transfer_clan', None)
                return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_TRANSFER_CLAN
        
        if 'rename_level' in context.user_data:
            level = context.user_data['rename_level']
            rename_type = context.user_data.get('rename_type', 'bot')
            name = text
            if rename_type == 'bot':
                db.update_bot_rank_name(level, name)
            elif rename_type == 'agent':
                db.update_agent_rank_name(level, name)
            elif rename_type == 'chat':
                db.update_chat_rank_name(level, name)
            await update.message.reply_text(f"✅ Уровень {level} переименован в «{name}»!")
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
                    await update.message.reply_text("Отправьте уровень (1-9):")
                    return WAITING_FOR_ADMIN_LEVEL
                except ValueError:
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
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_ADMIN_LEVEL
            
            elif action == 'remove_admin':
                try:
                    target_id = int(text)
                    db.remove_bot_admin(target_id)
                    await update.message.reply_text(f"✅ Админ {target_id} удален!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID
            
            elif action == 'change_admin_level':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'change_admin_level_value'
                    await update.message.reply_text("Отправьте новый уровень (1-9):")
                    return WAITING_FOR_ADMIN_LEVEL
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_ADMIN_ID
            
            elif action == 'change_admin_level_value':
                try:
                    level = int(text)
                    target_id = context.user_data.get('target_id')
                    db.update_bot_admin_level(target_id, level)
                    await update.message.reply_text(f"✅ Уровень изменен!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_ADMIN_LEVEL
            
            elif action == 'add_agent':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'add_agent_level'
                    await update.message.reply_text("Отправьте уровень (1-3):")
                    return WAITING_FOR_AGENT_LEVEL
                except ValueError:
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
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_AGENT_LEVEL
            
            elif action == 'remove_agent':
                try:
                    target_id = int(text)
                    db.remove_agent(target_id)
                    await update.message.reply_text(f"✅ Агент {target_id} удален!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID
            
            elif action == 'change_agent_level':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'change_agent_level_value'
                    await update.message.reply_text("Отправьте новый уровень (1-3):")
                    return WAITING_FOR_AGENT_LEVEL
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_AGENT_ID
            
            elif action == 'change_agent_level_value':
                try:
                    level = int(text)
                    target_id = context.user_data.get('target_id')
                    db.update_agent_level(target_id, level)
                    await update.message.reply_text(f"✅ Уровень изменен!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
                    await update.message.reply_text("❌ Неверный уровень!")
                    return WAITING_FOR_AGENT_LEVEL
            
            elif action == 'blacklist_add':
                try:
                    target_id = int(text)
                    context.user_data['target_id'] = target_id
                    context.user_data['action'] = 'blacklist_add_reason'
                    await update.message.reply_text("Отправьте причину:")
                    return WAITING_FOR_BLACKLIST_REASON
                except ValueError:
                    await update.message.reply_text("❌ Неверный ID!")
                    return WAITING_FOR_BLACKLIST_ID
            
            elif action == 'blacklist_add_reason':
                target_id = context.user_data.get('target_id')
                db.add_to_blacklist(target_id, text, user.id)
                await update.message.reply_text(f"✅ {target_id} добавлен в ЧС!")
                context.user_data.clear()
                return ConversationHandler.END
            
            elif action == 'blacklist_remove':
                try:
                    target_id = int(text)
                    db.remove_from_blacklist(target_id)
                    await update.message.reply_text(f"✅ {target_id} удален из ЧС!")
                    context.user_data.clear()
                    return ConversationHandler.END
                except ValueError:
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
            
            await update.message.reply_text(f"✅ Рассылка завершена!\n📊 Отправлено: {sent}")
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
                
            except ValueError:
                await update.message.reply_text("❌ Неверный ID!")
                return WAITING_FOR_WAR_CLAN_ID
        
        if 'waiting_war_rating' in context.user_data:
            try:
                rating = int(text)
                clan = db.get_user_clan(user.id)
                enemy_clan_id = context.user_data.get('enemy_clan_id')
                enemy_clan = db.get_clan_by_id(enemy_clan_id)
                
                result = db.declare_war(clan[0], enemy_clan_id, rating)
                if result:
                    winner_name = result['clan1_name'] if result['winner_id'] == clan[0] else result['clan2_name']
                    text_result = f"⚔ ВОЙНА ЗАВЕРШЕНА!\n\n🏆 Победитель: {winner_name}!\n💰 Ставка: {rating}"
                    await update.message.reply_text(text_result)
                    context.user_data.clear()
                    return ConversationHandler.END
            except ValueError:
                await update.message.reply_text("❌ Неверная ставка!")
                return WAITING_FOR_WAR_RATING
        
        if 'clan_msg_to' in context.user_data:
            try:
                to_clan_id = int(text)
                context.user_data['clan_msg_to'] = to_clan_id
                context.user_data['waiting_clan_msg_text'] = True
                await update.message.reply_text("Отправьте текст сообщения:")
                return WAITING_FOR_CLAN_MSG_TEXT
            except ValueError:
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
        "answer_report": Handlers.answer_report, "reject_report": Handlers.reject_report,
        "answer_question": Handlers.answer_question, "reject_question": Handlers.reject_question,
        "astats": Handlers.astats, "hstats": Handlers.hstats,
        "give_rep": Handlers.give_rep, "rename_bot_rank": Handlers.rename_bot_rank,
        "rename_agent_rank": Handlers.rename_agent_rank, "rename_chat_rank": Handlers.rename_chat_rank,
        "accept_request": Handlers.accept_request, "reject_request": Handlers.reject_request,
        "ask": Handlers.ask, "backup": Handlers.backup_command,
    }
    
    for command, handler in commands.items():
        application.add_handler(CommandHandler(command, handler))
    
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, Handlers.on_bot_added), group=2)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, Handlers.welcome_new_member), group=3)
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
            CallbackQueryHandler(Handlers.button_handler, pattern="^bot_access_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^agent_access_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^chat_access_"),
            CallbackQueryHandler(Handlers.button_handler, pattern="^set_level_"),
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
    print("📦 Резервное копирование: /backup")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()