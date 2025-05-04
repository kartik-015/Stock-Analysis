from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime
import os
import pandas as pd
import sys

# Get the absolute path of the current directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

# Configure the database path
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "instance", "users.db")}'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['DEBUG'] = True

db = SQLAlchemy(app)

# Load the stock data
try:
    stock_data = pd.read_csv(os.path.join(BASE_DIR, 'dump.csv'))
    # Convert date column to datetime if it exists
    if 'date' in stock_data.columns:
        stock_data['date'] = pd.to_datetime(stock_data['date'])
except Exception as e:
    print(f"Error loading stock data: {e}")
    stock_data = None

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
        }

# Ensure the instance directory exists
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return send_from_directory(os.path.join(BASE_DIR, '..', 'frontend'), 'index.html')

@app.route('/api/stock-data/<company_id>')
def get_stock_data(company_id):
    if stock_data is None:
        return jsonify({'error': 'Stock data not available'}), 500
    
    try:
        # Filter data for the specific company
        company_data = stock_data[stock_data['company_id'] == company_id]
        
        # Sort by date
        company_data = company_data.sort_values('date')
        
        # Prepare the response
        response = {
            'dates': company_data['date'].dt.strftime('%Y-%m-%d').tolist(),
            'prices': company_data['price'].tolist()
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
    user = User(email=email, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return jsonify({'user': user.to_dict()})

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
    return jsonify({'user': user.to_dict()})

@app.route('/api/forecast/<company_name>')
def get_forecast(company_name):
    try:
        # Convert company name to match the actual file names
        # Remove "NIFTY" prefix and convert to proper case
        clean_name = company_name.replace('NIFTY ', '').title()
        filename = f"NIFTY {clean_name}.csv"
        filepath = os.path.join(BASE_DIR, 'forecast_output', filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': f'Forecast not found for {company_name}'}), 404
            
        # Read the forecast data
        forecast_data = pd.read_csv(filepath)
        
        # Convert to the required format
        data = []
        for _, row in forecast_data.iterrows():
            data.append({
                'ds': row['ds'],
                'yhat': row['yhat']
            })
            
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_forecast: {str(e)}", file=sys.stderr)
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Ensure all required directories exist
    os.makedirs(os.path.join(BASE_DIR, 'forecast_output'), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    
    # Run the app
    app.run(debug=True, port=5000)