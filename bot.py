import os, requests, json, time
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')
SERVER_SECRET = os.environ.get('SERVER_SECRET', 'dev_secret')
HF_API_KEY = os.environ.get('HF_API_KEY')  # optional
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')  # optional

def ai_generate(prompt, max_tokens=800):
    hf_key = os.environ.get('HF_API_KEY')
    if hf_key:
        headers = {'Authorization': f'Bearer {hf_key}'}
        model_url = os.environ.get('HF_API_URL', 'https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct')
        r = requests.post(model_url, headers=headers, json={'inputs': prompt})
        try:
            j = r.json()
            if isinstance(j, list) and 'generated_text' in j[0]:
                return j[0]['generated_text']
            if isinstance(j, dict) and 'generated_text' in j:
                return j['generated_text']
            return str(j)
        except:
            return 'AI error'
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        import openai
        openai.api_key = openai_key
        resp = openai.Completion.create(engine='text-davinci-003', prompt=prompt, max_tokens=max_tokens)
        return resp.choices[0].text.strip()
    return 'No AI key configured. Set HF_API_KEY or OPENAI_API_KEY in env.'

def generate_mini_analysis(text):
    prompt = f"Give a friendly 3-paragraph mini psychological analysis of the following text:\n\n{text}\n\nKeep it concise and actionable."
    return ai_generate(prompt, max_tokens=300)

def generate_full_report(text):
    prompt = ("You are a professional psychologist and career coach. Produce a detailed premium report (sections): Summary, Personality Profile, Strengths & Weaknesses, 30/60/90-day plan, Long-term Potential and Career Paths. Use clear headings. Text:\n\n" + text)
    return ai_generate(prompt, max_tokens=1500)

bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dp = updater.dispatcher

def start(update: Update, context):
    update.message.reply_text('Welcome! Send any text to get a mini-analysis. Use /buy to purchase the full premium report.')

def buy_cmd(update: Update, context):
    user = update.effective_user
    telegram_id = user.id
    res = requests.post(f"{SERVER_URL}/create-checkout-session", json={'telegram_id': telegram_id, 'plan':'premium', 'secret': SERVER_SECRET, 'price': 3.99})
    data = res.json()
    if res.status_code==200 and data.get('checkout_url'):
        kb = InlineKeyboardMarkup([[InlineKeyboardButton('Open checkout', url=data['checkout_url'])]])
        update.message.reply_text('Open checkout to pay for premium report:', reply_markup=kb)
        update.message.reply_text('After payment, use /redeem to receive your full report.')
    else:
        update.message.reply_text('Payment creation error: ' + json.dumps(data))

def redeem_cmd(update: Update, context):
    user = update.effective_user
    telegram_id = user.id
    r = requests.get(f"{SERVER_URL}/user_status/{telegram_id}")
    data = r.json()
    if data.get('premium'):
        update.message.reply_text('You have active premium — generating your full report.')
        if context.user_data.get('last_text'):
            text = context.user_data.get('last_text')
        else:
            update.message.reply_text('Send the text you want the report on.')
            return
        report = generate_full_report(text)
        for chunk in [report[i:i+4000] for i in range(0, len(report), 4000)]:
            update.message.reply_text(chunk)
    else:
        update.message.reply_text('No active premium found. Use /buy to purchase.')

def echo_handler(update: Update, context):
    text = update.message.text
    context.user_data['last_text'] = text
    mini = generate_mini_analysis(text)
    update.message.reply_text('Mini-analysis (free):\n\n' + mini)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton('Get premium 5-7 page report — Buy', callback_data='buy')]])
    update.message.reply_text('Want the full premium report?', reply_markup=kb)

def callback_query(update: Update, context):
    q = update.callback_query
    q.answer()
    if q.data == 'buy':
        buy_cmd(update, context)

dp.add_handler(CommandHandler('start', start))
dp.add_handler(CommandHandler('buy', buy_cmd))
dp.add_handler(CommandHandler('redeem', redeem_cmd))
dp.add_handler(CallbackQueryHandler(callback_query))
dp.add_handler(MessageHandler(Filters.text & (~Filters.command), echo_handler))

if __name__ == '__main__':
    updater.start_polling()
    updater.idle()
