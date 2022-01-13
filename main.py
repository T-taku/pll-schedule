import discord as d
import discord
import re
from discord.ext import tasks
from discord.commands import Option
import datetime
import sqlite3
import asyncio
from discord import enums as en
import configparser

bot = discord.Bot()

def get_token(name):
    config = configparser.ConfigParser()
    config.read('config.ini')
    tokens = 'tokens'
    return config.get(tokens, name)

dbname = 'database/plan.db'
bot.conn = sqlite3.connect(dbname)
bot.cur = bot.conn.cursor()
bot.cur.execute(
    "CREATE TABLE IF NOT EXISTS plan(name, msg, year, month, day, hour, minutes)")
bot.conn.commit()


@bot.event
async def on_ready():
    listening = discord.Game("予定を通知します!")
    await bot.change_presence(status=discord.Status.online, activity=listening)
    print("Login!")


def set_date(date):
    try:
        ymd = date.split("/")
        year, month, day = map(int, ymd)
        return year, month, day
    except:
        raise ValueError("日付の入力が適切ではありません。")


def strptime(time):
    time = time.lower().strip()
    for pattern in ("am%H:%M", "pm%H:%M", "午前%H:%M", "午後%H:%M", "%H:%M",
                    "am%H時%M分", "pm%H時%M分", "午前%H時%M分", "午後%H時%M分", "%H時%M分"):
        try:
            timeobj = datetime.datetime.strptime(time, pattern)
            hour = timeobj.hour
            minute = timeobj.minute
            if re.search("^(?:pm|午後)", pattern) and hour < 12:
                hour += 12
            return hour, minute
        except:
            continue
    raise ValueError("不正な時刻です。")


@bot.slash_command(guild_ids=[int(get_token("guild_id"))])
async def create(
    ctx,
    plan_name: Option(str, "予定の名前"),
    mention: Option(en.SlashCommandOptionType(9), "メンション先"),
    date: Option(str, "日付(例:2022/01/01) ※半角数字のみ、1などの単数は01と入力"),
    time: Option(str, "通知時刻を設定できます。(例:午後12時00分や、22:00なども可能)※半角数字のみ、1などの単数は01と入力 / 入力しない場合は0:00に通知されます。"),
    plan_msg: Option(str, "メッセージ(メンションも含めます。)"),
):
    """通知する予定を作成します。メンバーと役職の指定ページは、必須の引数を全て入力後、TABキーを押して表示できます。"""
    if time is None:
        hour = 0
        minutes = 0
    else:
        hour, minutes = strptime(time)
    year, month, day = set_date(date)
    msg = f"<@{mention.id}> {plan_msg}"
    bot.cur.execute("INSERT INTO plan(name, msg, year, month, day, hour, minutes) VALUES(?,?,?,?,?,?,?)",
                    (plan_name, msg, year, month, day, hour, minutes))
    bot.conn.commit()
    embed = discord.Embed(
        title="予定の作成完了", description="次のように予定の作成が完了しました。", color=0x4CAF50)
    embed.add_field(name="予定の名前", value=f"{plan_name}", inline=True)
    embed.add_field(name="通知日", value=f"{year}年{month}月{day}日", inline=True)
    embed.add_field(name="通知時刻", value=f"{hour}時{minutes}分", inline=True)
    embed.add_field(name="メッセージ内容", value=f"({mention}へのメンション) {plan_msg}", inline=True)
    await ctx.respond(embed=embed)


async def get_plan(ctx: discord.AutocompleteContext):
    bot.conn.commit()
    options = []
    bot.cur.execute("SELECT * FROM plan;")
    for p in bot.cur.fetchall():
        options.append(f"{p[0]}")
    return options


@bot.slash_command(guild_ids=[int(get_token("guild_id"))])
async def edit(
    ctx,
    plan: Option(str, "予定を選択してください。", autocomplete=get_plan),
    plan_name: Option(en.SlashCommandOptionType(9), "予定の名前"),
    mention: Option(str, "メンション先(@を打った後メンション先一覧を表示してください。)"),
    date: Option(str, "日付(例:2022/01/01) ※半角数字のみ、1などの単数は01と入力"),
    time: Option(str, "通知時刻を設定できます。(例:午後12時00分や、22:00なども可能)※半角数字のみ、1などの単数は01と入力 / 入力しない場合は0:00に通知されます。"),
    plan_msg: Option(str, "メッセージ(メンションも含めます。)"),
):
    """予定の通知時間やメッセージを変更します。"""
    if time is None:
        hour = 0
        minutes = 0
    else:
        hour, minutes = strptime(time)
    year, month, day = set_date(date)
    msg = f"<@{mention.id}> {plan_msg}"
    bot.cur.execute("UPDATE plan SET name = ?, msg = ?, year = ?, month = ?, day = ?, hour = ?, minutes = ? WHERE name = ?",
                    (plan_name, msg, year, month, day, hour, minutes, plan))
    bot.conn.commit()
    embed = discord.Embed(
        title="予定の変更完了", description="次のように予定の変更が完了しました。", color=0xFFEB3B)
    embed.add_field(name="予定の名前", value=f"{plan_name}", inline=True)
    embed.add_field(name="通知日", value=f"{year}年{month}月{day}日", inline=True)
    embed.add_field(name="通知時刻", value=f"{hour}時{minutes}分", inline=True)
    embed.add_field(name="メッセージ内容", value=f"({mention}へのメンション) {plan_msg}", inline=True)
    await ctx.respond(embed=embed)


@bot.slash_command(guild_ids=[int(get_token("guild_id"))], name="delete")
async def delete_(
    ctx,
    plan: Option(str, "予定を選択してください。", autocomplete=get_plan),
):
    """予定の削除を行います。"""
    bot.cur.execute("DELETE FROM plan WHERE name = ?", (plan,))
    bot.conn.commit()
    embed = discord.Embed(
        title="予定の削除完了", description=f"「{plan}」の削除が完了しました。", color=0xF44336)
    await ctx.respond(embed=embed)


@bot.slash_command(guild_ids=[int(get_token("guild_id"))], name="list")
async def list_(ctx):
    """予定の一覧を表示します。"""
    embed = discord.Embed(title="予定の一覧", color=0x00BCD4)
    bot.cur.execute("SELECT * FROM plan;")
    for i in bot.cur.fetchall():
        embed.add_field(
            name=i[0], value=f"{i[2]}/{i[3]}/{i[4]} {i[5]}:{i[6]}", inline=False)
    await ctx.respond(embed=embed)


@tasks.loop(seconds=1.0)
async def send_notice():
    JST = datetime.timezone(datetime.timedelta(hours=+9), "JST")
    now = datetime.datetime.now(JST)  # JSTで現在時刻を取得(datetime型)
    sql_taple = (now.year, now.month, now.day, now.hour, now.minute)
    # 現在時刻とそれ以前のデータを全部取得
    bot.cur.execute(
        "SELECT * FROM plan WHERE year <= ? AND month <= ? AND day <= ? AND hour <= ? AND minutes <= ?", sql_taple)
    coros = []
    try:
        for i in bot.cur.fetchall():
            embed = discord.Embed(title=i[0], color=0xFDD835, timestamp=datetime.datetime(
                *i[2:7]) - datetime.timedelta(hours=9))  # データベースにはJSTで入っているので9時間引いてる
            coros.append(bot.get_channel(int(get_token("channel_id"))).send(
                embed=embed))  # メッセージを送信するコルーチンを生成して配列にぶち込む
            coros.append(bot.get_channel(int(get_token("channel_id"))).send(i[1]))
            # データくんは用済みなので消し消し
            bot.cur.execute(
                "DELETE FROM plan WHERE year <= ? AND month <= ? AND day <= ? AND hour <= ? AND minutes <= ?", sql_taple)
            bot.conn.commit()
        loop = bot.loop or asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*coros))  # コルーチンを一気に実行するで
    except:
        return

send_notice.start()

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
