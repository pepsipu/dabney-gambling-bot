import os
from dotenv import load_dotenv
from itertools import starmap
from sqlitedict import SqliteDict
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = str(os.getenv("TG_TOKEN"))
DB_PATH = str(os.getenv("DB_PATH"))

users = SqliteDict(DB_PATH)


# logging.basicConfig(
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
# )


def format_leaderboard_entry(index: int, id: str) -> str:
    user = users[id]
    return f"{index + 1}. {user["username"]} - {user["hits"]}"


async def handle_leaderboard(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not (msg := update.message):
        return

    await msg.reply_text(
        f"Leaderboard:\n"
        + "\n".join(
            starmap(
                format_leaderboard_entry,
                enumerate(
                    sorted(users, key=lambda id: users[id]["hits"], reverse=True)
                ),
            )
        ),
        reply_to_message_id=msg.id,
    )


async def handle_roll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (
        not (msg := update.message)
        or not (roll := msg.dice)
        or not (author := msg.from_user)
    ):
        return

    # keep user up to date
    user = users[author.id] if author.id in users else {"hits": 0, "username": None}
    user["username"] = author.username

    if roll.emoji == "🎰" and roll.value == 64:
        user["hits"] += 1
        await msg.reply_text("holy you're cracked", reply_to_message_id=msg.id)

    users[author.id] = user
    users.commit()


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("leaderboard", handle_leaderboard))
    app.add_handler(MessageHandler(filters.Dice.ALL, handle_roll))
    app.run_polling()


if __name__ == "__main__":
    main()
