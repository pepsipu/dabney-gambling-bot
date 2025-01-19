import os
import logging
from dotenv import load_dotenv
import asyncio
import peewee as pw
from telegram import Update, ChatFullInfo, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

db = pw.SqliteDatabase("data/data.db")


class User(pw.Model):
    name = pw.CharField()

    class Meta:
        database = db


class Roll(pw.Model):
    msg = pw.IntegerField()
    user = pw.ForeignKeyField(User, backref="rolls")

    emoji = pw.CharField()
    value = pw.IntegerField()

    class Meta:
        database = db


db.connect()
db.create_tables([User, Roll])


BOT_TOKEN = str(os.getenv("TG_TOKEN"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def fetch_chat_details(bot: Bot, user_id, roll_count):
    chat = await bot.get_chat(user_id)
    return chat, roll_count


def format_leaderboard_entry(index: int, chat: ChatFullInfo, roll_count: int) -> str:
    return f"{index + 1}. @{chat.username} - {roll_count}"


async def handle_leaderboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not (msg := update.message):
        return

    # Perform a left join between User and Roll, counting rolls with value 64 for each user
    query = (
        User.select(User, pw.fn.COUNT(Roll.id).alias("roll_count"))  # type: ignore
        .join(Roll, pw.JOIN.LEFT_OUTER)
        .where(Roll.value == 64)
        .group_by(User)
        .order_by(pw.fn.COUNT(Roll.id).desc())  # type: ignore
    )

    bot = msg.get_bot()
    tasks = [fetch_chat_details(bot, user.name, user.roll_count) for user in query]
    results = await asyncio.gather(*tasks)

    text = f"Leaderboard:\n" + "\n".join(
        format_leaderboard_entry(i, result[0], result[1])
        for i, result in enumerate(results)
    )

    await msg.reply_text(
        text,
        reply_to_message_id=msg.id,
    )


async def handle_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (
        not (msg := update.message)
        or not (roll := msg.dice)
        or not (author := msg.from_user)
    ):
        return
    user, _ = User.get_or_create(name=author.id)
    Roll.create(msg=msg.id, user=user, emoji=roll.emoji, value=roll.value)

    if roll.emoji == "🎰" and roll.value == 64:
        await msg.reply_text("holy you're cracked", reply_to_message_id=msg.id)


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("leaderboard", handle_leaderboard))
    app.add_handler(MessageHandler(filters.Dice.ALL, handle_roll))
    app.run_polling()


if __name__ == "__main__":
    main()
