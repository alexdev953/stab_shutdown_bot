import sqlite3
from typing import Optional
from aiogram.types import User, Update
from Logger import logger

member_status = {"kicked": 0,
                 "member": 1}


class DataBase:
    con: Optional[sqlite3.Connection] = None

    def __init__(self):
        self.con = self.connect()
        self.first_start()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect('bot.db')
        return con

    def first_start(self):
        sql = """create table if not exists users (
    user_id integer primary key autoincrement,
    first_name text,
    user_name text,
    telegram_id integer not null,
    created text not null default current_timestamp,
    updated text not null default current_timestamp
);"""
        self.con.execute(sql)

    def check_user(self, user: User):
        try:
            cur = self.con.cursor()
            cur.execute('select telegram_id from users where telegram_id = ?', (user.id,))
            info = cur.fetchone()
            if not info:
                cur.execute("insert into users (first_name, user_name, telegram_id, last_name) values (?, ?, ?, ?)",
                            (user.first_name, user.username, user.id, user.last_name))
                self.con.commit()
            elif info:
                cur.execute("update users set updated = current_timestamp, last_name = ? where telegram_id = ?",
                            (user.last_name, user.id))
                self.con.commit()
            cur.close()
        except Exception as e:
            logger.exception(e)
        finally:
            return True

    def chat_member(self, user_id, status):
        cur = self.con.cursor()
        int_status = member_status.get(status, 1)
        cur.execute("update users set member = ?, updated = current_timestamp where telegram_id = ?",
                    (int_status, user_id))
        self.con.commit()

