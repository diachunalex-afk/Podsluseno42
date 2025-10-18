from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import random
import string
from collections import deque

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace-with-your-secret'  # для сесій (можна змінити)
socketio = SocketIO(app, cors_allowed_origins="*")  # для простоти дозволяємо всі джерела

# Зберігаємо останні N повідомлень
MAX_HISTORY = 100
message_history = deque(maxlen=MAX_HISTORY)  # кожен елемент: dict {name, text, ts}

# Мапа sid -> display name
clients = {}

def gen_anon_name():
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"Anon-{suffix}"

@app.route("/")
def index():
    return render_template("index.html")

@socketio.on('connect')
def on_connect():
    sid = request.sid
    name = gen_anon_name()
    clients[sid] = name
    # Надсилаємо клієнту його ім'я та історію
    emit('welcome', {'name': name, 'history': list(message_history)})
    # Повідомляємо іншим, що підключився новий анонім
    emit('system', {'msg': f"{name} приєднався(лась)."}, broadcast=True, include_self=False)

@socketio.on('set_name')
def on_set_name(data):
    """Опціонально дозволяємо користувачу задати короткий нік (необов'язково)."""
    sid = request.sid
    desired = (data.get('name') or "").strip()
    if not desired:
        return
    # обмежимо довжину
    desired = desired[:32]
    old = clients.get(sid, gen_anon_name())
    clients[sid] = desired
    emit('system', {'msg': f"{old} тепер відображається як {desired}."}, broadcast=True)

@socketio.on('message')
def on_message(data):
    """Очікуємо data = {'text': '...'}"""
    sid = request.sid
    text = (data.get('text') or "").strip()
    if not text:
        return
    name = clients.get(sid, gen_anon_name())
    # Побудуємо повідомлення
    msg = {'name': name, 'text': text}
    # Додамо до історії та широкомовимо
    message_history.append(msg)
    emit('message', msg, broadcast=True)

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    name = clients.pop(sid, None)
    if name:
        emit('system', {'msg': f"{name} покинув(ла) чат."}, broadcast=True)

if __name__ == '__main__':
    # Використовуємо eventlet для WebSocket
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
