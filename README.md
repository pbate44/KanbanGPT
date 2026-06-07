# KanbanGPT

A self-hostable Kanban board with AI chat built into every card. Bring your own AI API key and use any model available on [OpenRouter](https://openrouter.ai) — Claude, GPT, Gemini, Mistral, and more.

**Hosted site → [kanbangpt.ai](https://kanbangpt.ai)**

---
# Why did I make it?

I used to use Kanban alot for tracking client information and correspondence in a previous job. Cards would grow to 200+ logs, with multiple file attachments, and it would be difficult to go back and find details. I thought a Kanban board with AI built in to each task might be helpful. But it is quite a niche problem, so I am not sure it is that good of an idea. I also built it to get into programming. I admit I used AI to design the UI, so there may be improvements that could be made in that area. I plan to continue adding useful features as a hobby.

---

![KanbanGPT demo](kanbangpt-gif.gif)

---

## Features

- **Kanban boards** — drag-and-drop cards across columns, custom board backgrounds
- **Swimlanes** — group cards horizontally within a board
- **Subtasks** — checklist-style subtasks on every card
- **AI chat per card** — chat with any OpenRouter model in context of the card (title, description, activity log)
- **Web search in AI** — let the AI search the web as part of its answer
- **File attachments** — attach files to cards, stored securely on S3
- **Activity log** — full history of changes per card, exportable to PDF
- **2FA** — email-based two-factor authentication on login

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1, PostgreSQL |
| Frontend | Vanilla JS, Bootstrap |
| AI | [OpenRouter](https://openrouter.ai) |
| File storage | AWS S3 |
| Static files | WhiteNoise |
| Email | SMTP (Zoho) |

---

## Self-hosting

### Prerequisites

- Python 3.12+
- PostgreSQL
- An [OpenRouter](https://openrouter.ai) API key

### 1. Clone & install

```bash
git clone https://github.com/pbate44/workpalai.git
cd workpalai
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Open `.env` and fill in your values. At minimum for local dev you need:

```
SECRET_KEY=<generate one below>
DEBUG=True
DATABASE_URL=postgres://user:password@localhost:5432/kanbangpt
```

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Run migrations & start

```bash
python manage.py migrate
python manage.py runserver
```

Visit [http://localhost:8000](http://localhost:8000).

---

## AI Setup

### Hosted site ([kanbangpt.ai](https://kanbangpt.ai))

AI is available out of the box — no API key needed. All models on the hosted site are **free-tier models** provided via [OpenRouter](https://openrouter.ai). Because these are shared free-tier quotas, some models may be temporarily unavailable or slow during periods of high demand. If a model isn't responding, try switching to a different one in **Settings → AI Model**.

### Self-hosted

Set your own `OPENROUTER_API_KEY` in `.env`. Users can then pick from any model available on OpenRouter — including paid models — from **Settings → AI Model**.

---

## Project Structure

```
workpalai/
├── frontend/
│   ├── views/          # One file per feature area (board, card, ai, auth…)
│   ├── services/       # Business logic (ai_service.py, two_factor_service.py)
│   ├── models.py       # All models (Board → Column → Card, Swimlane, etc.)
│   ├── templates/      # Django HTML templates
│   └── static/         # CSS & vanilla JS
├── workpal/
│   ├── settings.py     # All config (reads from environment variables)
│   └── urls.py
├── .env.example        # Copy to .env and fill in your values
└── requirements.txt
```

---

## Known Structural Notes

This is my first open source project and I am aware there may be issues. All suggestions for improvements and fixes are more than welcome. Please feel free to raise an issue / PR if you spot something wrong. There are a few structural codebase changes that will be addressed in later versions. Some folders reference 'workpal' which was the original name.

---

## Contributing

Pull requests are welcome. For major changes please open an issue first.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a PR

---

## Disclaimer

KanbanGPT is not affiliated with, endorsed by, or connected to OpenAI or ChatGPT. "GPT" refers to the AI-assisted features available within the app, which are powered by multiple model providers via [OpenRouter](https://openrouter.ai).

---

## Licence

[MIT](LICENSE) © Patrick Bateson
