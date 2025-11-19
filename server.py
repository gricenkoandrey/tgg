import os, json, time
from uuid import uuid4
from flask import Flask, request, jsonify
import stripe

DB_FILE = 'orders.json'
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump({'orders': [], 'users': {}, 'promos': {}, 'audit': []}, f, indent=2)

def read_db():
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_db(d):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2)

STRIPE_SECRET = os.environ.get('STRIPE_SECRET')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
SERVER_SECRET = os.environ.get('SERVER_SECRET', 'dev_secret')
BASE_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')

if STRIPE_SECRET:
    stripe.api_key = STRIPE_SECRET

app = Flask(__name__)

@app.route('/')
def index():
    return 'AI Premium Bot Payment Server is running.'

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.json or {}
    if data.get('secret') != SERVER_SECRET:
        return jsonify({'error': 'bad secret'}), 403
    telegram_id = str(data.get('telegram_id'))
    plan = data.get('plan', 'premium')
    price = float(data.get('price', 3.99))
    currency = data.get('currency', 'usd')
    db = read_db()
    order_id = 'ord_' + uuid4().hex[:12]
    order = {'id': order_id, 'telegram_id': telegram_id, 'plan': plan, 'status': 'pending', 'created_at': int(time.time()), 'price': price, 'currency': currency}
    db['orders'].append(order)
    write_db(db)

    if STRIPE_SECRET:
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': currency,
                        'product_data': {'name': f'Premium AI Report ({plan})'},
                        'unit_amount': int(price*100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}&order_id={order_id}',
                cancel_url=f'{BASE_URL}/cancel?order_id={order_id}',
                metadata={'order_id': order_id, 'telegram_id': telegram_id}
            )
            return jsonify({'checkout_url': checkout_session.url, 'order_id': order_id})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        payment_url = f'{BASE_URL}/pay_stub/{order_id}'
        return jsonify({'checkout_url': payment_url, 'order_id': order_id})

@app.route('/pay_stub/<order_id>')
def pay_stub(order_id):
    return f"Demo payment page for order {order_id}. To simulate payment call POST /webhook/simulate with {{'orderId':'{order_id}','paid':true}}"

@app.route('/order/<order_id>')
def get_order(order_id):
    db = read_db()
    for o in db.get('orders', []):
        if o['id'] == order_id:
            return jsonify(o)
    return jsonify({'error': 'not found'}), 404

@app.route('/user_status/<telegram_id>')
def user_status(telegram_id):
    db = read_db()
    users = db.get('users', {})
    status = users.get(str(telegram_id), {})
    return jsonify(status)

@app.route('/webhook/simulate', methods=['POST'])
def webhook_simulate():
    payload = request.json or {}
    orderId = payload.get('orderId')
    paid = payload.get('paid')
    db = read_db()
    for o in db['orders']:
        if o['id'] == orderId:
            o['status'] = 'paid' if paid else 'failed'
            if paid:
                tg = str(o.get('telegram_id'))
                db['users'][tg] = {'premium': True, 'plan': o.get('plan'), 'order_id': orderId, 'expires_at': int(time.time()) + 30*24*3600}
            write_db(db)
            return jsonify({'ok': True})
    return jsonify({'error': 'order not found'}), 404

@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    if not STRIPE_SECRET:
        return 'stripe not configured', 400
    payload = request.data
    sig_header = request.headers.get('stripe-signature')
    event = None
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            event = json.loads(payload)
    except Exception as e:
        print('Webhook signature error', e)
        return jsonify({'error': str(e)}), 400

    if event and event.get('type') == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id')
        telegram_id = session.get('metadata', {}).get('telegram_id')
        db = read_db()
        for o in db['orders']:
            if o['id'] == order_id:
                o['status'] = 'paid'
                db['users'][str(telegram_id)] = {'premium': True, 'plan': o.get('plan'), 'order_id': order_id, 'expires_at': int(time.time()) + 30*24*3600}
                write_db(db)
                break
    return jsonify({'received': True}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
