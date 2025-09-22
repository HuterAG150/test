from flask import Flask, render_template, request, redirect, flash, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://messager_user:ROBERT3@localhost/messenger'
app.config['SECRET_KEY'] = '1'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(15), unique=True)

class Mesagge(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)    
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.datetime.now)
    
    def to_public_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'message': self.message,
            'date': self.date.isoformat(),
            'is_my': self.sender_id == session.get('user_id')
        }

# create table users ( id SERIAL PRIMARY KEY, username VARCHAR(40) NOT NULL UNIQUE, phone VARCHAR(15) UNIQUE, email VARCHAR(256) UNIQUE, password TEXT NOT NULL);
# create table messages ( id SERIAL PRIMARY KEY, sender_id INT NOT NULL REFERENCES user (id), receiver_id INT NOT NULL REFERENCES users (id), message TEXT NOT NULL, date TIMESTAMP);
# create user messager_user1 with password 'ROBERT4'

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('index.html', user=user)
    return render_template('index.html', user=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['user_id'] = user.id
        flash('Вход выполнен успешно')
        return redirect(url_for('index'))
    else:
        flash('Неверное имя пользователя или пароль')
        return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    username = request.form.get('username')
    email = request.form.get('email')
    phone = request.form.get('phone')
    password = request.form.get('password')
    
    if phone:
        phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if len(phone) > 15:
            phone = phone[:15]
    
    exists = User.query.filter_by(username=username).first()
    if exists:
        flash('пользователь уже существует')
        return redirect(url_for('register'))
    
    user = User(username=username, email=email, phone=phone, password=password)
    db.session.add(user)
    db.session.commit()
    flash('Регистрация успешна')
    return redirect(url_for('login'))

@app.route('/users')
def users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_users = User.query.all()
    return render_template('users.html', users=all_users)

@app.route('/chat/<username>')
def chat(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    other_user = User.query.filter_by(username=username).first()
    if not other_user:
        flash('Пользователь не найден')
        return redirect(url_for('users'))
    
    current_user = User.query.get(session['user_id'])
    return render_template('chat.html', other_user=other_user, current_user=current_user)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Вы вышли из системы')
    return redirect(url_for('index'))

@app.post('/messages/send')
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    data = request.get_json()
    receiver_username = data.get('receiver_username')
    message_text = data.get('message')
    
    if not receiver_username or not message_text:
        return jsonify({'error': 'Неверные данные'}), 400
    
    receiver = User.query.filter_by(username=receiver_username).first()
    if not receiver:
        return jsonify({'error': 'Получатель не найден'}), 404
    
    new_message = Mesagge(
        sender_id=session['user_id'],
        receiver_id=receiver.id,
        message=message_text
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    return jsonify({'success': True})

@app.get('/messages/dialog/<username>')
def get_dialog(username):
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    me = session['user_id']
    other = User.query.filter_by(username=username).first()
    
    if not other:
        return jsonify({'error': 'Собеседник не найден'}), 404
    
    query = Mesagge.query.filter(
        db.or_(
            db.and_(Mesagge.sender_id == me, Mesagge.receiver_id == other.id),
            db.and_(Mesagge.sender_id == other.id, Mesagge.receiver_id == me)
        )
    ).order_by(Mesagge.date.asc())
    
    rows = query.all()
    
    return jsonify({
        'messages': [message.to_public_dict() for message in rows]
    })

def f(a,b):
    ...

if __name__ == '__main__':
    app.run(debug=True)