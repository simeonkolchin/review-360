#!/usr/bin/env python3
"""One-off import of a group's full member list, through a user account.

The Bot API has no "list members" call at all — that is a deliberate privacy
decision, and no amount of admin rights changes it. A *user* account can do it
over MTProto, because it is simply reading what any member of the group can see
in the members tab.

So this is a manual, occasional tool rather than part of the running system:

    pip install telethon
    python tools/import_members.py \\
        --chat -1004346985805 \\
        --base-url https://tgreview360.ru/api \\
        --bot-token "$BOT_API_TOKEN"

The first run asks for a phone number and the login code, then caches the
session in `tools/.import.session` so later runs are silent.

Deliberately not a server feature: a stored user session lets whoever holds it
act as that person in Telegram — far more power than this product needs. Run it
from your own machine, and the imported people keep flowing through the same
`/bot/enroll` endpoint the bot uses.
"""

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from telethon import TelegramClient, utils
    from telethon.tl.types import User
except ImportError:  # pragma: no cover - the tool is optional
    print("Telethon is not installed:  pip install telethon", file=sys.stderr)
    raise SystemExit(1)

SESSION = Path(__file__).with_name(".import.session")

# Telegram's public demo credentials work for this, but get your own at
# https://my.telegram.org if you plan to use it regularly.
DEFAULT_API_ID = 2040
DEFAULT_API_HASH = "b18441a1ff607e10a989891a5462e627"


def enroll(base_url: str, bot_token: str, payload: dict) -> bool:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/bot/enroll",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-Bot-Token": bot_token},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        print(f"  ! {exc.code}: {exc.read().decode()[:200]}", file=sys.stderr)
        return False


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chat", required=True,
                        help="chat id, @username or invite link of the group")
    parser.add_argument("--base-url", default="http://localhost:8080/api")
    parser.add_argument("--bot-token", required=True, help="BOT_API_TOKEN from .env")
    parser.add_argument("--api-id", type=int, default=DEFAULT_API_ID)
    parser.add_argument("--api-hash", default=DEFAULT_API_HASH)
    args = parser.parse_args()

    chat_ref: str | int = args.chat
    if isinstance(chat_ref, str) and chat_ref.lstrip("-").isdigit():
        chat_ref = int(chat_ref)

    async with TelegramClient(str(SESSION), args.api_id, args.api_hash) as client:
        entity = await client.get_entity(chat_ref)
        title = getattr(entity, "title", "Группа")
        # Telethon ids are raw; the rest of the system speaks Bot API ids (-100…)
        bot_api_chat_id = utils.get_peer_id(entity)
        participants = await client.get_participants(entity)

        print(f"{title}: {len(participants)} участник(ов) по данным Telegram\n")

        imported = 0
        for person in participants:
            if not isinstance(person, User) or person.bot or person.deleted:
                continue
            ok = enroll(args.base_url, args.bot_token, {
                # The bot fills in profile photos later, on the next sync — it
                # can fetch them for any id it knows about.
                "telegram_chat_id": bot_api_chat_id,
                "chat_title": title,
                "telegram_id": person.id,
                "username": person.username,
                "first_name": person.first_name,
                "last_name": person.last_name,
            })
            name = " ".join(p for p in [person.first_name, person.last_name] if p)
            print(f"  {'✓' if ok else '✗'} {name or person.id}")
            imported += ok

        print(f"\nЗаписано: {imported}")
        print("Откройте страницу чата и нажмите «Обновить» — бот подтянет аватарки.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
