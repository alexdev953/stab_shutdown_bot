import sqlite3
from typing import Optional
from aiogram.types import User
import json
from Logger import logger

member_status = {"kicked": 0,
                 "member": 1}


class SqlString:

    first_sql: str = """create table if not exists users (
    user_id integer primary key autoincrement,
    first_name text,
    user_name text,
    telegram_id integer not null,
    created text not null default (datetime(current_timestamp, 'localtime')),
    updated text not null default (datetime(current_timestamp, 'localtime'))
);
create table if not exists power_data_tbl
(
    id_pow      integer                                                 not null
        constraint power_data_tbl_pk
            primary key autoincrement,
    pow_data    text                                                    not null,
    created     text default (datetime(current_timestamp, 'localtime')) not null,
    actual_date TEXT                                                    not null,
    actual_time TEXT                                                    not null
);
"""
    check_user_sql: str = 'select telegram_id from users where telegram_id = ?'
    insert_user_sql: str = "insert into users (first_name, user_name, telegram_id, last_name) values (?, ?, ?, ?)"
    update_user_sql: str = ("update users set updated = datetime(current_timestamp, 'localtime'), last_name = ? where "
                            "telegram_id = ?")
    update_member_sql: str = ("update users set member = ?, updated = datetime(current_timestamp, 'localtime') "
                              "where telegram_id = ?")
    insert_power_sql: str = "insert into power_data_tbl(pow_data, actual_date, actual_time) values(?,?,?);"
    exist_next_sql:str = ("select exists(select actual_date from power_data_tbl where "
                          "actual_date = strftime('%d.%m.%Y', 'now', 'localtime', '+1 day')) as next_day")
    get_power_sql: str = """select power_data_tbl.pow_data
        ,exists(select actual_date from power_data_tbl where actual_date = strftime('%d.%m.%Y', 'now', 'localtime', '+1 day')) as next_day
        from power_data_tbl
        where datetime(power_data_tbl.created)
        between datetime(current_timestamp, 'localtime', '-15 minutes')
        and datetime(current_timestamp, 'localtime')
        and actual_date = strftime('%d.%m.%Y', 'now', 'localtime')
        order by created limit 1;"""

    get_actual_power_sql: str = """select pow_data from power_data_tbl 
    where actual_date = strftime('%d.%m.%Y', 'now', 'localtime') order by created DESC limit 1;"""


class DataBase:
    con: Optional[sqlite3.Connection] = None

    def __init__(self):
        self.con = self.connect()
        self.first_start()
        self.sql_strings = SqlString()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect('bot.db')
        return con

    def first_start(self):
        sql = self.sql_strings.first_sql
        self.con.executescript(sql)

    def check_user(self, user: User):
        try:
            cur = self.con.cursor()
            cur.execute(self.sql_strings.check_user_sql,
                        (user.id,))
            info = cur.fetchone()
            if not info:
                cur.execute(self.sql_strings.insert_user_sql,
                            (user.first_name, user.username, user.id, user.last_name))
                self.con.commit()
            elif info:
                cur.execute(self.sql_strings.update_user_sql,
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
        cur.execute(self.sql_strings.update_member_sql,
                    (int_status, user_id))
        self.con.commit()

    def save_json(self, data: dict):
        cur = self.con.cursor()
        cur.execute(self.sql_strings.insert_power_sql,
                    (json.dumps(data), data.get('actual_date'), data.get('actual_time')))
        self.con.commit()

    def get_json(self) -> dict:
        cur = self.con.cursor()
        cur.execute(self.sql_strings.exist_next_sql)
        next_day = cur.fetchone()
        cur.execute(self.sql_strings.get_power_sql)
        info = cur.fetchone()
        logger.debug(info)
        if info:
            data = json.loads(info[0])
            data.update({"next_day": next_day[0]})
            return data
        else:
            return {"data": None, "next_day": next_day[0]}

    def get_last_actual(self):
        cur = self.con.cursor()
        cur.execute(self.sql_strings.get_actual_power_sql)
        info = cur.fetchone()
        logger.debug(info)
        return json.loads(info[0])
