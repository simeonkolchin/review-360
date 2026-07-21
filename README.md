<div align="center">

<img src="frontend/public/logo.png" width="92" alt="Review 360"/>

# Review 360

**360° feedback for teams, run entirely from a Telegram group — add the bot to your work chat, drag people into teams on the web, and everyone answers in their own DM.**

[![Live](https://img.shields.io/badge/live-tgreview360.ru-3b82f6)](https://tgreview360.ru)
[![Bot](https://img.shields.io/badge/bot-@tgreview360bot-2CA5E0?logo=telegram&logoColor=white)](https://t.me/tgreview360bot)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://aiogram.dev/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<!-- DEMO: drop docs/demo.gif in place and uncomment the line below
<img src="docs/demo.gif" width="82%" alt="Review 360 — demo"/>
-->

**🎥 Demo — coming up:** a full walkthrough from an empty group chat to a finished 360° review — enrolment, drag-and-drop team building, the review inside Telegram, and the results dashboard.

<sub>Meanwhile the live instance is at <a href="https://tgreview360.ru">tgreview360.ru</a>.</sub>

</div>

---

## 📋 Contents

[The problem](#-the-problem) · [The idea](#-the-idea) · [How it works](#-how-it-works) · [Telegram limits](#-two-telegram-limits-and-the-way-around-them) · [Architecture](#️-architecture) · [Anonymity](#-anonymity-is-a-rule-not-a-setting) · [Scoring](#-scoring) · [Interface](#-interface) · [Quick start](#-quick-start) · [Deployment](#-production-deployment) · [API](#-api) · [Data model](#️-data-model) · [Testing](#-testing) · [Roadmap](#️-roadmap)

---

## 🎯 The problem

360° review is one of the few HR instruments that actually changes behaviour: you learn how the team sees you, not how your manager summarises it. The method is not the hard part — **the logistics are**.

The usual attempt looks like this:

- **A spreadsheet.** Someone builds a matrix of who rates whom, exports it, and mails out links.
- **Two weeks of chasing.** Half the team forgets, the other half fills it in on the last day.
- **Manual aggregation.** Averages are computed by hand, so mistakes are invisible.
- **Broken anonymity.** In a team of four, "the average of your peers" plus a bit of arithmetic identifies the author of a low score immediately — and everyone knows it, so nobody writes anything honest.
- **Stale results.** By the time the deck is ready, the quarter is over.

The instrument is fine. The delivery kills it.

## 💡 The idea

Run the whole thing **where the team already talks**. No accounts, no invitation emails, no forms — a Telegram group, a button, and about five minutes per person.

1. The bot joins the work chat; people **enrol themselves** with one tap.
2. Teams are assembled on the web by **dragging** members into a team and putting a crown on the leader.
3. One press of *Start* and the bot tags everyone in the group, handing each person a **personal deep link**.
4. Each participant answers **in their own DM** — with the reviewee's Telegram photo in front of them, so they always know who they are rating.
5. Results appear on the dashboard and inside the bot, with anonymity enforced by the backend rather than by good intentions.

And the number that matters is never the average. It is the **gap between self-assessment and how the team sees you** — every chart here is built around that axis.

## 🔄 How it works

```
  ┌── Telegram group ──────────────┐          ┌── Web ──────────────────┐
  │  /enroll → "Участвую" button   │          │  log in through the bot │
  │  people opt in themselves      │─────────▶│  drag members into      │
  │  bot learns who they are       │          │  teams, pick a leader   │
  └────────────────────────────────┘          │  press "Запустить"      │
                 ▲                            └───────────┬─────────────┘
                 │  bot posts in the group,               │
                 │  tags everyone, hands out              │
                 │  personal deep links                   ▼
  ┌── Telegram DM ─────────────────┐          ┌── Dashboard ────────────┐
  │  photo of the person being     │          │  radar per person,      │
  │  rated + 1–5 per competency    │─────────▶│  self vs team,          │
  │  then an anonymous note        │          │  anonymous comments     │
  └────────────────────────────────┘          └─────────────────────────┘
```

Every round creates three kinds of assignment per member: **self**, **peer** (everyone else), and **leader** — the leader's view is stored separately so it never dilutes the peer average, because one strong opinion from above is not the same signal as the team's.

## 🔐 Two Telegram limits, and the way around them

This is the part that decides whether such a product is even possible.

| Limit | Reality | What we do |
|---|---|---|
| **A bot cannot list group members** | The method was removed from the Bot API for privacy — only `getChatAdministrators`, `getChatMemberCount` and per-user lookups remain | People **enrol themselves** with one button. It is not a workaround so much as the honest version: being reviewed requires consent |
| **A bot cannot message someone first** | Telegram requires the user to open the dialog | The group post carries a **personal deep link** (`t.me/bot?start=<token>`). Pressing *Start* opens the dialog *and* begins that person's review in one motion |

The same mechanism powers **login**. The site has no Telegram Login Widget — it needs a BotFather-registered domain and never works on localhost. Instead the site mints a **one-time token**, opens the bot with it, and polls until the bot confirms. Tokens are single-use and expire in ten minutes; the session then lives in an httpOnly cookie.

## 🏗️ Architecture

Four services behind a single nginx entry point. Nothing except nginx is exposed.

```
                    ┌──────────────────────────────────────────┐
   browser ───────▶ │  nginx                                   │
                    │  /       → React SPA (static build)      │
                    │  /api/*  → gateway                       │
                    └────────────────┬─────────────────────────┘
                                     │
   Telegram ──▶ bot ─────────────────┤  X-Bot-Token
   (aiogram long polling)            ▼
                    ┌──────────────────────────────────────────┐
                    │  gateway  :8010                          │
                    │  who you are: JWT in an httpOnly cookie, │
                    │  every route behind a dependency,        │
                    │  an event written for every action       │
                    └────────────────┬─────────────────────────┘
                                     │  X-Service-Token
                                     ▼
                    ┌──────────────────────────────────────────┐
                    │  data-service  :8011                     │
                    │  what is true: the only service with     │
                    │  database access; scoring and anonymity  │
                    └────────────────┬─────────────────────────┘
                                     ▼
                              PostgreSQL 17
```

**Why split the gateway from the data-service?** Because the anonymity rule has to live in exactly one place. The gateway owns identity — sessions, cookies, statistics. The data-service owns truth — schema, aggregation, the minimum-responses threshold. Neither the browser nor the bot can reach the data layer without the service token, so there is no path that returns an individual peer score, whatever the caller asks for.

Both FastAPI services share the same skeleton: app-factory, `routes / schemas / services / engine / utils`, Prometheus metrics on `/metrics`, and an OpenAPI spec written to `openapi_spec/` on every boot.

```
review-360/
├── gateway/         public API: auth, chats, teams, rounds, bot bridge
│   └── app/{routes,schemas,services,utils}
├── data-service/    database, scoring engine, anonymity
│   └── app/{routes,schemas,engine,models,utils}
├── bot/             aiogram 3 — enrolment, DM review, results
│   └── app/{handlers,keyboards,services}
├── frontend/        React 18 + TypeScript + Vite + Tailwind v4
├── nginx/           single entry point
├── openapi_spec/    generated on boot
├── tests/           end-to-end flow test, 35 assertions, no mocks
├── docs/            architecture notes, demo material
└── docker-compose.yaml
```

More detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 🕶️ Anonymity is a rule, not a setting

The method collapses the moment people suspect they can be identified — so this is enforced in the aggregation engine, with no switch in the UI to turn it off:

- Peer averages are returned **only when at least three people have answered** (`MIN_RESPONSES_FOR_RESULTS`). Below that the card shows a lock and no number at all.
- **Individual peer scores are never returned by any endpoint** — only averages. There is no "raw answers" view, not even for the leader.
- Free-text notes come back as a **shuffled list of strings with no author**, held back by the same threshold.
- **Self and leader assessments are labelled**, precisely because they are attributable by construction: everyone knows there is exactly one of each, so pretending otherwise would be the dishonest choice.

## 📊 Scoring

Five competencies are seeded on first boot and can be edited in the database:

| Competency | What it asks about |
|---|---|
| Коммуникация | Explains clearly, listens, gives feedback |
| Ответственность | Keeps promises, finishes what was started |
| Экспертиза | Knows the craft, solves problems well |
| Инициатива | Proposes improvements without being asked |
| Командность | Helps colleagues, works for the shared result |

Each is rated 1–5. For every person the engine produces the self score, the peer average, the leader's score and the overall figures — and the dashboard draws all of it as a radar chart with self and team overlaid, because the shape of the gap is more informative than any single number.

## 🖥️ Interface

- **Login** — a decoding headline (rAF text-scramble, stepped on a timer, `aria-label` for screen readers, instant for `prefers-reduced-motion`) and a three-step card that opens the bot.
- **Overview** — connected chats as bento tiles, with an onboarding path for the first one.
- **Team builder** — drag members from the participant list into the team zone, crown the leader, create. Everything is also clickable, so it works without a mouse drag.
- **Round** — live progress, participants done, and a modal confirming exactly who is about to be pinged.
- **Results** — a radar per person, self-vs-team bars per competency, and the anonymous comments underneath.

Dark UI, Geist, blue accent, motion on every transition — page enters, staggered cards, scrim modals, pressed-button feedback.

<!-- SCREENSHOTS: drop the files into docs/ and uncomment
<div align="center">
<img src="docs/screen-login.png" width="47%" alt="Login"/>
<img src="docs/screen-teams.png" width="47%" alt="Team builder"/>
<img src="docs/screen-results.png" width="47%" alt="Results"/>
<img src="docs/screen-bot.png" width="47%" alt="The review inside Telegram"/>
</div>
-->

## 🚀 Quick start

```bash
git clone https://github.com/simeonkolchin/review-360.git
cd review-360
make env                    # creates .env from the template
```

Put your bot credentials in `.env` — from [@BotFather](https://t.me/BotFather):

```ini
TELEGRAM_BOT_TOKEN=1234567890:AA...
TELEGRAM_BOT_USERNAME=your_bot        # without the @
```

Then:

```bash
make up-bot                 # database + data-service + gateway + bot + web
open http://localhost:8080
```

| | |
|---|---|
| App | http://localhost:8080 |
| Swagger (gateway) | http://localhost:8080/docs |
| Metrics | `gateway:8010/metrics`, `data-service:8011/metrics` |

```bash
make test        # end-to-end flow against the running stack
make logs        # gateway + data-service
make logs-bot    # bot
make reset       # wipe the database and start clean
make help        # every target
```

**Before going live:** replace `SERVICE_TOKEN`, `BOT_API_TOKEN` and `JWT_SECRET` with real secrets and set `DEV_LOGIN_ENABLED=false` — that flag enables a signature-free login meant strictly for local work.

## 🌍 Production deployment

The live instance runs at **[tgreview360.ru](https://tgreview360.ru)** on a Docker host behind a shared nginx edge proxy:

```
Internet :443 ──▶ edge-proxy (SNI routing) ──▶ TLS termination for tgreview360.ru
                                          └──▶ review360-frontend:80 ──▶ gateway ──▶ data-service ──▶ postgres
```

- Let's Encrypt certificates, issued over the ACME webroot the edge proxy serves on port 80 and renewed on a timer.
- The project keeps its own internal nginx, so the container is identical locally and in production; only the edge proxy knows about domains and certificates.
- The bot uses long polling — no webhook, no inbound port, so it works from anywhere.

Step-by-step: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## 🔌 API

Public surface, all under `/api`, all behind the session cookie:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/auth/config` | Bot username, which login methods are enabled |
| `POST` | `/auth/login-link` | Mint a one-time token + bot deep link |
| `GET` | `/auth/login-status` | Poll until the bot confirms; sets the cookie |
| `GET` / `POST` | `/auth/me`, `/auth/logout` | Session |
| `GET` | `/chats` | Chats you belong to |
| `GET` | `/chats/{id}/members` | People who enrolled themselves |
| `GET` `POST` | `/chats/{id}/teams` | List / create teams |
| `DELETE` | `/teams/{id}` | Delete a team |
| `POST` | `/teams/{id}/rounds` | Start a round — posts into the group |
| `GET` | `/rounds/{id}` | Live progress |
| `POST` | `/rounds/{id}/close` | Close a round |
| `GET` | `/rounds/{id}/results` | Aggregated results |
| `GET` | `/stats` | Usage statistics |

Bot-only routes live under `/bot/*` behind `X-Bot-Token`: `enroll`, `tasks`, `responses`, `results`, `confirm-login`.
Generated specs: [`openapi_spec/`](openapi_spec/).

## 🗄️ Data model

```
TgUser ──┬── Membership ── Chat ──── Team ──┬── TeamMember ── TgUser
         │                                  │
         │                                  └── ReviewRound ── Assignment ── Response
         └── LoginToken                          draft/active/closed   reviewer → reviewee
                                                                       kind: self | peer | leader
Competency        Event  (every gateway action is recorded for statistics)
```

`Assignment` is the unit of work: one reviewer, one reviewee, one kind. A round for a team of *n* creates *n²* assignments — everyone rates everyone, including themselves.

## 🧪 Testing

```bash
make test
```

Drives the real HTTP stack end to end — no mocks, no fixtures poked into the database:

enrolment → auth is genuinely required → login through the bot bridge → team creation → round start (16 assignments for a team of 4) → every answer submitted → free-text comments → close → aggregation and the anonymity threshold → statistics. **35 assertions.**

## 🗺️ Roadmap

- [ ] Custom competency sets per team, editable from the web
- [ ] Round history and dynamics: how the gap moves quarter over quarter
- [ ] PDF export of an individual report
- [ ] Reminders for people who have not finished
- [ ] Telegram Mini App as an alternative to the DM flow

## 👤 Author

**Simeon Kolchin** — [@simeon_kolchin](https://t.me/simeon_kolchin) · [github.com/simeonkolchin](https://github.com/simeonkolchin)

## 📄 License

MIT — see [LICENSE](LICENSE).
