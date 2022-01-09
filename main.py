import discord as d
import discord
import re
from discord.ext import commands, tasks
from typing import Union
from discord.commands import Option
import datetime
import calendar
import time as timetime
import aiocron
import sqlite3
from discord.ext.ui import View, Message, Select, SelectOption, ViewTracker, MessageProvider
from typing import List
import asyncio

bot = discord.Bot()

dbname = 'database/plan.db'
bot.conn = sqlite3.connect(dbname)
bot.cur = bot.conn.cursor()

bot.cur.execute("CREATE TABLE IF NOT EXISTS plan(name, msg, year, month, day, hour, minutes)")
bot.conn.commit()

@bot.event
async def on_ready():
    print("Login!")
    # send_notice.start()

def set_date(date):
    try:
        ymd = date.split("/")
        year, month, day = map(int, ymd)
        return year, month, day
    except:
        raise ValueError("日付の入力が適切ではありません。")

def strptime(time):
    time=time.lower().strip()
    for pattern in ("am%H:%M", "pm%H:%M", "午前%H:%M", "午後%H:%M", "%H:%M",
                    "am%H時%M分", "pm%H時%M分", "午前%H時%M分", "午後%H時%M分", "%H時%M分"):
        try:
            timeobj = datetime.datetime.strptime(time, pattern)
            hour = timeobj.hour
            minute = timeobj.minute
            if re.search("^(?:pm|午後)", pattern) and hour<12:
                hour += 12
            return hour, minute
        except:
            continue
    raise ValueError("不正な時刻です。")

@bot.slash_command(guild_ids=[858610234132922389])
async def create(
    ctx,
    plan_name: Option(str, "予定の名前"),
    date: Option(str, "日付(例:2022/01/01) ※半角数字のみ、1などの単数は01と入力"),
    plan_msg: Option(str, "メッセージ(メンションも含めます。)"),
    time: Option(str, "通知時刻を設定できます。(例:12時00分や、22:00なども可能)※半角数字のみ、1などの単数は01と入力 / 入力しない場合は0:00に通知されます。",required=False),
    ):
    """通知する予定を作成します。メンバーと役職の指定ページは、必須の引数を全て入力後、TABキーを押して表示できます。"""
    if time is None:
        hour=0
        minutes=0
    else:
        hour, minutes=strptime(time)
    year, month, day=set_date(date)
    bot.cur.execute("INSERT INTO plan(name, msg, year, month, day, hour, minutes) VALUES(?,?,?,?,?,?,?)", (plan_name,plan_msg,year,month,day,hour,minutes))
    bot.conn.commit()
    embed = discord.Embed(title="予定の作成完了", description="次のように予定の作成が完了しました。",color=0x4CAF50)
    embed.add_field(name="予定の名前",value=f"{plan_name}",inline=True)
    embed.add_field(name="通知日",value=f"{year}年{month}月{day}日",inline=True)
    embed.add_field(name="通知時刻",value=f"{hour}時{minutes}分",inline=True)
    embed.add_field(name="メッセージ内容",value=f"{plan_msg}",inline=True)
    await ctx.respond(embed=embed)

def get_plan(bot):
    options=[]
    bot.cur.execute("SELECT * FROM plan;")
    for p in bot.cur.fetchall():
        options.append(f"{p[2]}/{p[3]}/{p[4]} {p[5]}:{p[6]} - {p[0]}")
    return options

@bot.slash_command(guild_ids=[858610234132922389])
async def edit(
    ctx,
    plan: Option(str, "予定を選択してください。", choices=get_plan(bot)),
    plan_name: Option(str, "予定の名前"),
    date: Option(str, "日付(例:2022/01/01) ※半角数字のみ、1などの単数は01と入力"),
    plan_msg: Option(str, "メッセージ(メンションも含めます。)"),
    time: Option(str, "通知時刻を設定できます。(例:12時00分や、22:00なども可能)※半角数字のみ、1などの単数は01と入力 / 入力しない場合は0:00に通知されます。",required=False) = None,
    ):
    """予定の通知時間やメッセージを変更します。"""
    if time is None:
        hour=0
        minutes=0
    else:
        hour, minutes=strptime(time)
    year, month, day=set_date(date)
    bot.cur.execute("UPDATE plan SET name = ?, msg = ?, year = ?, month = ?, day = ?, hour = ?, minutes = ? WHERE name = ?", (plan_name,plan_msg,year,month,day,hour,minutes,plan,))
    bot.conn.commit()
    embed = discord.Embed(title="予定の変更完了", description="次のように予定の変更が完了しました。",color=0xFFEB3B)
    embed.add_field(name="予定の名前",value=f"{plan_name}",inline=True)
    embed.add_field(name="通知日",value=f"{year}年{month}月{day}日",inline=True)
    embed.add_field(name="通知時刻",value=f"{hour}時{minutes}分",inline=True)
    embed.add_field(name="メッセージ内容",value=f"{plan_msg}",inline=True)
    await ctx.respond(embed=embed)

@bot.slash_command(guild_ids=[858610234132922389], name="delete")
async def delete_(
    ctx,
    plan: Option(str, "予定を選択してください。", choices=get_plan(bot)),
    ):
    """予定の削除を行います。"""
    bot.cur.execute("DELETE FROM plan WHERE name <= ?", (plan,))
    bot.conn.commit()
    embed = discord.Embed(title="予定の削除完了", description=f"「{plan}」の削除が完了しました。",color=0x00FFFF)
    await ctx.respond(embed=embed)

@bot.slash_command(guild_ids=[858610234132922389], name="list")
async def list_(ctx):
    """予定の一覧を表示します。"""
    embed = discord.Embed(title="予定の一覧",color=0x00BCD4)
    bot.cur.execute("SELECT * FROM plan;")
    for i in bot.cur.fetchall():
        embed.add_field(name=i[0], value=f"{i[2]}/{i[3]}/{i[4]} {i[5]}:{i[6]}", inline=False)
    await ctx.respond(embed=embed)

@tasks.loop(seconds=1)
async def send_notice():
    JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")
    now = datetime.datetime.now(JST) # JSTで現在時刻を取得(datetime型)
    sql_taple = (now.year, now.month, now.day, now.hour, now.minute)

    bot.cur.execute("SELECT * FROM plan WHERE year <= ? AND month <= ? AND day <= ? AND hour <= ? AND minutes <= ?", sql_taple) # 現在時刻とそれ以前のデータを全部取得
    coros = []
    for i in bot.cur.fetchall():
        embed = discord.Embed(title="予定の通知", description=i[0],color=0xFDD835, timestamp=datetime.datetime(*i[2:7]) - datetime.timedelta(hours=9)) # データベースにはJSTで入っているので9時間引いてる
        coros.append(bot.get_channel(875560501449469982).send(i[1], embed=embed)) # メッセージを送信するコルーチンを生成して配列にぶち込む
    loop = bot.loop or asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*coros)) # コルーチンを一気に実行するで

    bot.cur.execute("DELETE FROM plan WHERE year <= ? AND month <= ? AND day <= ? AND hour <= ? AND minutes <= ?", sql_taple) # データくんは用済みなので消し消し

_close = bot.close
async def close_handler():
    try:
        await bot.session.close()
        bot.conn.commit()
        bot.conn.close()
        print("[System] Session Closed Successfully.")
    except:
        bot.conn.commit()
        bot.conn.close()
        print("[System] Session Closed Failed or Already closed.")
        pass
    await _close()
bot.close = close_handler

bot.run("")