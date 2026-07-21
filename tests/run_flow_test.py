#!/usr/bin/env python3
"""End-to-end check of the whole Review 360 flow.

Walks the real path a team takes: people enroll from a group, someone builds a
team on the site, a round starts, everyone answers in the bot, the round closes
and the aggregated (anonymous) results come back.

    python tests/run_flow_test.py --base-url http://localhost:8080/api
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

OK = "\x1b[32m"
ERR = "\x1b[31m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  {OK}PASS{RESET}  {name}")
    else:
        failed += 1
        print(f"  {ERR}FAIL{RESET}  {name} {DIM}{detail}{RESET}")


class Client:
    def __init__(self, base_url: str, bot_token: str):
        self.base = base_url.rstrip("/")
        self.bot_token = bot_token
        self.cookie: str | None = None

    def call(self, method: str, path: str, body=None, bot=False, params=None):
        url = f"{self.base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        if bot:
            request.add_header("X-Bot-Token", self.bot_token)
        elif self.cookie:
            request.add_header("Cookie", self.cookie)

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode()
                set_cookie = response.headers.get("Set-Cookie")
                if set_cookie:
                    self.cookie = set_cookie.split(";")[0]
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()[:300]


import urllib.parse  # noqa: E402  (used inside Client.call)

PEOPLE = [
    (9001, "anna", "Анна"),
    (9002, "boris", "Борис"),
    (9003, "vera", "Вера"),
    (9004, "gleb", "Глеб"),
]
CHAT_ID = -100900900900


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8080/api")
    parser.add_argument("--bot-token", default="change-me-bot-token")
    args = parser.parse_args()

    client = Client(args.base_url, args.bot_token)

    print("\n1. Health")
    status, _ = client.call("GET", "/health")
    check("gateway is healthy", status == 200, f"status={status}")

    print("\n2. People enroll from the group (bot API)")
    for telegram_id, username, name in PEOPLE:
        status, _ = client.call(
            "POST",
            "/bot/enroll",
            {
                "telegram_chat_id": CHAT_ID,
                "chat_title": "Тестовая команда",
                "telegram_id": telegram_id,
                "username": username,
                "first_name": name,
                "can_dm": True,
            },
            bot=True,
        )
        check(f"enrolled {name}", status == 200, f"status={status}")

    print("\n3. Auth is required")
    fresh = Client(args.base_url, args.bot_token)
    status, _ = fresh.call("GET", "/chats")
    check("GET /chats without a cookie is rejected", status == 401, f"status={status}")

    print("\n4. Login and read the chat")
    status, _ = client.call(
        "POST", "/auth/dev-login", {"telegram_id": PEOPLE[0][0], "first_name": PEOPLE[0][2]}
    )
    if status == 403:
        # Production has dev-login switched off, as it should — drive the real
        # login instead: mint a one-time token, confirm it the way the bot does,
        # then exchange it for the session cookie.
        print(f"  {DIM}dev-login disabled — using the bot login bridge{RESET}")
        status, link = client.call("POST", "/auth/login-link")
        check("login link issued", status == 200 and link.get("token"), f"status={status}")
        token = link["token"]

        status, _ = client.call(
            "POST",
            "/bot/confirm-login",
            {
                "token": token,
                "telegram_id": PEOPLE[0][0],
                "first_name": PEOPLE[0][2],
                "username": PEOPLE[0][1],
            },
            bot=True,
        )
        check("bot confirmed the login", status == 200, f"status={status}")

        status, user = client.call("GET", "/auth/login-status", params={"token": token})
        check("session cookie issued", status == 200 and client.cookie, f"status={status}")

        status, _ = client.call("GET", "/auth/login-status", params={"token": token})
        check("login token is single-use", status == 409, f"status={status}")
    else:
        check("dev-login works", status == 200, f"status={status}")

    status, chats = client.call("GET", "/chats")
    check("chat is visible", status == 200 and len(chats) >= 1, f"status={status}")
    chat = next((c for c in chats if c["telegram_chat_id"] == CHAT_ID), None)
    check("our chat is in the list", chat is not None)
    if chat is None:
        return 1

    status, members = client.call("GET", f"/chats/{chat['id']}/members")
    check("all 4 enrolled members returned", status == 200 and len(members) == 4,
          f"got={len(members) if status == 200 else status}")

    print("\n5. Create a team")
    status, team = client.call(
        "POST",
        f"/chats/{chat['id']}/teams",
        {
            "name": "Продукт",
            "leader_telegram_id": PEOPLE[0][0],
            "member_telegram_ids": [p[0] for p in PEOPLE],
        },
    )
    check("team created", status == 201, f"status={status} {team}")
    if status != 201:
        return 1
    check("leader is set", team["leader"] is not None)
    check("team has 4 members", len(team["members"]) == 4)

    status, _ = client.call(
        "POST",
        f"/chats/{chat['id']}/teams",
        {"name": "Слишком мало", "member_telegram_ids": [PEOPLE[0][0]]},
    )
    check("team with 1 member is rejected", status == 400, f"status={status}")

    print("\n6. Start the round")
    status, round_ = client.call("POST", f"/teams/{team['id']}/rounds")
    check("round started", status == 201, f"status={status} {round_}")
    if status != 201:
        return 1
    # 4 people rating themselves and each other = 16 assignments
    check("16 assignments created", round_["total_assignments"] == 16,
          f"got={round_['total_assignments']}")

    status, _ = client.call("POST", f"/teams/{team['id']}/rounds")
    check("second concurrent round is rejected", status == 409, f"status={status}")

    print("\n7. Everyone answers in the bot")
    token = round_["token"]
    for telegram_id, _, name in PEOPLE:
        status, tasks = client.call(
            "GET", "/bot/tasks", bot=True, params={"token": token, "telegram_id": telegram_id}
        )
        if status != 200:
            check(f"{name} got tasks", False, f"status={status} {tasks}")
            continue
        competencies = tasks["competencies"]
        done = 0
        for assignment in tasks["assignments"]:
            # score 4 for yourself, 5 for everyone else — makes the aggregation
            # easy to assert on
            score = 4 if assignment["kind"] == "self" else 5
            status, _ = client.call(
                "POST",
                "/bot/responses",
                {
                    "assignment_id": assignment["id"],
                    "responses": [
                        {"competency_id": c["id"], "score": score} for c in competencies
                    ],
                },
                bot=True,
                params={"telegram_id": telegram_id},
            )
            if status == 200:
                done += 1
                # then the free-text note the bot asks for after each person
                client.call(
                    "POST",
                    "/bot/responses",
                    {
                        "assignment_id": assignment["id"],
                        "comment_only": True,
                        "responses": [
                            {
                                "competency_id": competencies[0]["id"],
                                "score": 0,
                                "comment": f"Заметка от {name}",
                            }
                        ],
                    },
                    bot=True,
                    params={"telegram_id": telegram_id},
                )
        check(f"{name} completed {done}/4 assignments", done == 4, f"done={done}")

    print("\n8. Progress and close")
    status, progress = client.call("GET", f"/rounds/{round_['id']}")
    check("all assignments completed", progress["completed_assignments"] == 16,
          f"got={progress['completed_assignments']}")
    check("all participants done", progress["participants_done"] == 4,
          f"got={progress['participants_done']}")

    status, closed = client.call("POST", f"/rounds/{round_['id']}/close")
    check("round closed", status == 200 and closed["status"] == "closed", f"status={status}")

    print("\n9. Results and anonymity")
    status, results = client.call("GET", f"/rounds/{round_['id']}/results")
    check("results returned", status == 200, f"status={status}")
    check("results cover 4 people", len(results["members"]) == 4)

    anna = next(m for m in results["members"] if m["user"]["telegram_id"] == PEOPLE[0][0])
    check("self score is 4.0", anna["overall_self"] == 4.0, f"got={anna['overall_self']}")
    # Anna is the leader, so her own peers are the other 3 -> but the leader's
    # own rating of others is tagged `leader`, meaning Anna receives 3 peer
    # scores of 5.
    check("peer average is 5.0", anna["overall_peer"] == 5.0, f"got={anna['overall_peer']}")
    first = anna["scores"][0]
    check("peer answers counted (>=3)", first["responses_count"] >= 3,
          f"got={first['responses_count']}")
    check("nothing hidden once enough answers", first["hidden_for_anonymity"] is False)
    comments = anna.get("comments") or []
    check("anonymous comments came through", len(comments) >= 3, f"got={len(comments)}")
    check("comments carry no author", all(isinstance(c, str) for c in comments))

    print("\n10. Statistics were recorded")
    status, stats = client.call("GET", "/stats")
    check("stats endpoint works", status == 200, f"status={status}")
    if status == 200:
        check("events were logged", stats["counts"]["events"] > 0, f"got={stats['counts']}")
        # >= not == so the suite can be re-run against a live database
        check("responses stored", stats["counts"]["responses"] >= 80,
              f"got={stats['counts']['responses']}")

    print(f"\n{'-' * 46}")
    print(f"  {OK}passed: {passed}{RESET}   {ERR if failed else DIM}failed: {failed}{RESET}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
