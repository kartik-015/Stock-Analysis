from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    trade_coins = db.Column(db.Integer, default=0)
    last_prediction = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'tradeCoins': self.trade_coins,
            'lastPrediction': self.last_prediction.isoformat() if self.last_prediction else None
        }

with app.app_context():
    db.create_all()

def generate_token(user_id):
    return jwt.encode(
        {'user_id': user_id, 'exp': datetime.utcnow() + timedelta(days=1)},
        app.config['SECRET_KEY'],
        algorithm='HS256'
    )

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400

    user = User(
        email=email,
        password=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    token = generate_token(user.id)
    return jsonify({
        'token': token,
        'user': user.to_dict()
    })

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = generate_token(user.id)
    return jsonify({
        'token': token,
        'user': user.to_dict()
    })

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is required'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        amount = data.get('amount')
        if not amount or amount < 100 or amount > user.trade_coins:
            return jsonify({'error': 'Invalid withdrawal amount'}), 400

        user.trade_coins -= amount
        db.session.commit()

        # Here you would integrate with a payment gateway to process the withdrawal
        # For now, we'll just return success
        return jsonify({
            'message': f'Successfully withdrawn {amount} Trade Coins (₹{amount/10})',
            'user': user.to_dict()
        })

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/api/update_prediction', methods=['POST'])
def update_prediction():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Token is required'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        coins_earned = data.get('coins_earned', 0)

        # Update user's trade coins and last prediction time
        user.trade_coins += coins_earned
        user.last_prediction = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message': 'Prediction recorded successfully',
            'user': user.to_dict()
        })

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

if __name__ == '__main__':
    app.run(debug=True) 