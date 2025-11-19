Telegram AI Premium Bot — ZIP package
=====================================
What is inside:
- server.py         : Flask payment / admin server (Stripe + demo payment stub)
- bot.py            : Telegram bot (mini-analysis + premium report flow)
- requirements.txt  : Python dependencies
- orders.json       : simple JSON DB used by server
- run.sh            : helper to run server + bot locally
- .replit           : optional for Replit (runs run.sh)
- admin.html        : simple admin UI (open in browser)
- README.md         : this file

Quick start (locally)
1) Install Python 3.10+ and pip.
2) Create and activate a virtualenv (recommended):
   python -m venv venv
   source venv/bin/activate  (on Windows: venv\Scripts\activate)
3) Install requirements:
   pip install -r requirements.txt
4) Set environment variables (create a .env or export in shell):
   TELEGRAM_TOKEN        - your Telegram Bot token
   HF_API_KEY            - (optional) HuggingFace or other model key
   OPENAI_API_KEY        - (optional) OpenAI key (if you prefer OpenAI)
   STRIPE_SECRET         - (optional) Stripe secret key (sk_test_...)
   STRIPE_WEBHOOK_SECRET - (optional) Stripe webhook secret
   SERVER_SECRET         - a secret string used by bot <-> server (choose any)
   SERVER_URL            - public URL for server (used in Stripe webhook) e.g. https://your-repl.repl.co
5) Run locally:
   bash run.sh
   This will start the Flask server and the bot (polling).

Replit / Render
- For free 24/7 hosting, you can upload the project to Replit (create a new Replit, upload files, add Secrets)
- On Replit set SERVER_URL to https://<your-repl>.repl.co and set the env variables in Secrets.
- Start the Repl; it will run server + bot.

How payment flow works (demo):
- /buy in the bot calls server /create-checkout-session -> returns a checkout URL (Stripe or demo stub)
- After payment Stripe webhook or manual simulation (/webhook/simulate) marks order paid and activates user's premium
- User runs /redeem in bot to receive the premium report

Important security notes:
- Don't share your secret keys. Use environment variables.
- For production use proper database (Postgres, Mongo) and secure admin access.
