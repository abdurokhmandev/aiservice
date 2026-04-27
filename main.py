"""
Telegram AI Userbot
- Telethon bilan o'z accountingga ulanadi
- Har qanday private xabarga AI javob beradi
- OpenRouter orqali Claude (primary) -> GPT-4o (fallback)
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from telethon import TelegramClient, events
from telethon.tl.types import User
from openai import AsyncOpenAI

# ─── CONFIG ───────────────────────────────────────────────
API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MY_USER_ID = int(os.environ.get("MY_USER_ID", "0"))

# OpenRouter client
openrouter = AsyncOpenAI(
    api_key=OPENROUTER_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Modellar
PRIMARY_MODEL = "anthropic/claude-sonnet-4-5"
FALLBACK_MODEL = "openai/gpt-4o"

# System prompt
SYSTEM_PROMPT = """Sen Rahimov School xususiy maktabining rasmiy Telegram admini va yordamchisisisan.

MAKTAB HAQIDA TO'LIQ MA'LUMOT:
- Rahimov School — zamonaviy xususiy maktab
- 1-11 sinflarga qabul ochiq
- Dars kunlari: Dushanba-Juma (haftada 5 kun)
- Shanba: togaraklar (fanlar boyicha)
- Yakshanba: dam olish
- Narx: 6.200.000 som/oy
- Ish vaqti: 08:00 - 17:00

FILIALLAR:
- Ibn-Sino
- Lokomotiv
- Fargona

ALOQA:
- Telefon: +998 78 113-0005
- Telegram admin: @rahimovschool_admin

MUHIM QOIDALAR:
1. FAQAT Rahimov School bilan boglik savollarga javob ber
2. Rahimov School bilan boglik bolmagan savollarga:
   - Muloyimlik bilan rad et
   - "Uzr, men faqat Rahimov School haqida yordam bera olaman" de
3. Uslub:
   - Dostona, professional va ixcham javob ber
   - Uzbek tilida yoz (agar rus tilida yozsa, rus tilida javob ber)
   - Keraksiz uzun javob berma
4. Agar yuqoridagi malumotlarda yoq narsa soralsa:
   - "Batafsil malumot uchun @rahimovschool_admin ga yoki +998 78 113-0005 ga murojaat qiling" de"""

# Tarix
chat_history: dict[int, list] = {}
MAX_HISTORY = 10

# ─── AI FUNCTION ──────────────────────────────────────────

async def get_ai_reply(chat_id: int, user_text: str) -> str:
    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append({"role": "user", "content": user_text})

    if len(chat_history[chat_id]) > MAX_HISTORY * 2:
        chat_history[chat_id] = chat_history[chat_id][-MAX_HISTORY * 2:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history[chat_id]

    # Claude urinish
    reply = None
    try:
        response = await openrouter.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=messages,
            max_tokens=512
        )
        reply = response.choices[0].message.content
        print(f"[Claude] javob berdi")
    except Exception as e:
        print(f"[Claude error] {e}")

    # Fallback: GPT-4o
    if not reply:
        try:
            response = await openrouter.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=messages,
                max_tokens=512
            )
            reply = response.choices[0].message.content
            print(f"[GPT-4o fallback] javob berdi")
        except Exception as e:
            print(f"[GPT error] {e}")

    if not reply:
        reply = "Hozir javob bera olmayapman, keyinroq urinib ko'ring."

    chat_history[chat_id].append({"role": "assistant", "content": reply})
    return reply


# ─── TELEGRAM ─────────────────────────────────────────────

async def main():
    tg = TelegramClient("userbot_session", API_ID, API_HASH)

    @tg.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def handle_private(event):
        sender = await event.get_sender()

        if not isinstance(sender, User):
            return
        if sender.id == MY_USER_ID:
            return
        if sender.bot:
            return

        user_text = event.raw_text.strip()
        if not user_text:
            return

        chat_id = event.chat_id
        print(f"[{sender.first_name}]: {user_text[:60]}")

        async with tg.action(chat_id, "typing"):
            reply = await get_ai_reply(chat_id, user_text)

        await event.reply(reply)
        print(f"[AI -> {sender.first_name}]: {reply[:60]}")

    print("🤖 AI Userbot ishga tushmoqda...")
    await tg.start()
    me = await tg.get_me()
    print(f"✅ Ulandi: {me.first_name} (@{me.username})")
    print("📨 Private xabarlar kuzatilmoqda...")
    await tg.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
