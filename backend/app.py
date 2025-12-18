from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime
import os
from backend.config import Config
from backend.database import Database
from backend.scheduler import HourlyScheduler
from backend.rag_service import RAGChatbot

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../frontend',
            static_folder='../frontend/static')
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

# Initialize services
db = Database()
db.init_schema()
chatbot = RAGChatbot(db)
scheduler = HourlyScheduler()

# Start scheduler
scheduler.start()

# Run initial task if database is empty
if db.get_measurement_count() == 0:
    print("[ERROR] Database is empty! Please initialize with historical data first:")
    print("       python backend/init_db.py --csv path/to/your/historical_data.csv")
    exit(1)

@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('index.html')

@app.route('/api/current')
def api_current():
    """
    Get current PM2.5 measurement and next-hour prediction.
    
    Returns:
        {
            "datetime": "2025-11-23 14:00",
            "current_pm25": 15.3,
            "next_hour_prediction": 16.2,
            "status": "Good"
        }
    """
    try:
        # Get latest measurement
        latest = db.get_last_n_hours(1)
        if not latest:
            return jsonify({'error': 'No data available'}), 404
        
        current_pm25 = latest[0]['pm25']
        current_datetime = latest[0]['datetime']
        
        # Get predictions
        predictions = db.get_latest_predictions()
        next_hour_pred = predictions[0]['predicted_pm25'] if predictions else None
        
        # Determine status
        if current_pm25 <= 12:
            status = "Good"
        elif current_pm25 <= 35:
            status = "Moderate"
        elif current_pm25 <= 55:
            status = "Unhealthy for Sensitive"
        else:
            status = "Unhealthy"
        
        return jsonify({
            'datetime': current_datetime,
            'current_pm25': current_pm25,
            'next_hour_prediction': next_hour_pred,
            'status': status
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictions')
def api_predictions():
    """
    Get 24-hour predictions.
    
    Returns:
        {
            "predictions": [
                {"target_datetime": "2025-11-23 15:00", "predicted_pm25": 16.2},
                ...
            ]
        }
    """
    try:
        predictions = db.get_latest_predictions()
        return jsonify({'predictions': predictions})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history')
def api_history():
    """
    Get historical data for chart.
    
    Query params:
        hours: number of hours to retrieve (default: 168 = 7 days)
    
    Returns:
        {
            "history": [
                {"datetime": "2025-11-16 14:00", "pm25": 15.3},
                ...
            ]
        }
    """
    try:
        hours = request.args.get('hours', default=168, type=int)
        hours = min(hours, 720)  # Max 30 days
        
        history = db.get_last_n_hours(hours)
        return jsonify({'history': history})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """
    Chatbot endpoint using Gemini RAG.
    
    Request body:
        {"message": "What was the average PM2.5 last week?"}
    
    Returns:
        {"response": "The average PM2.5 last week was..."}
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Get response from RAG chatbot
        response = chatbot.query_data(user_message)
        
        return jsonify({'response': response})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """
    Get database statistics.
    
    Returns:
        {
            "total_measurements": 720,
            "latest_datetime": "2025-11-23 14:00",
            "prediction_count": 24
        }
    """
    try:
        count = db.get_measurement_count()
        latest = db.get_latest_datetime()
        predictions = db.get_latest_predictions()
        
        return jsonify({
            'total_measurements': count,
            'latest_datetime': latest,
            'prediction_count': len(predictions)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = Config.PORT
    print(f"\n🚀 Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=(Config.FLASK_ENV == 'development'))