import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional
from backend.config import Config

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database directory if not exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def init_schema(self):
        """Initialize database schema"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Table 1: Historical measurements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                datetime TEXT PRIMARY KEY,
                pm25 REAL NOT NULL,
                sitename TEXT NOT NULL,
                source TEXT NOT NULL
            )
        ''')
        
        # Table 2: Model predictions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                prediction_time TEXT NOT NULL,
                target_datetime TEXT NOT NULL,
                predicted_pm25 REAL NOT NULL,
                PRIMARY KEY (prediction_time, target_datetime)
            )
        ''')
        
        # Create indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_datetime ON measurements(datetime DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pred_time ON predictions(prediction_time DESC)')
        
        conn.commit()
        conn.close()
        print("✅ Database schema initialized")
    
    def insert_measurement(self, datetime_str: str, pm25: float, sitename: str, source: str = 'crawler'):
        """Insert single measurement"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO measurements (datetime, pm25, sitename, source)
                VALUES (?, ?, ?, ?)
            ''', (datetime_str, pm25, sitename, source))
            conn.commit()
        except Exception as e:
            print(f"[ERROR] Failed to insert measurement: {e}")
        finally:
            conn.close()
    
    def insert_measurements_bulk(self, data: List[Dict]):
        """Insert multiple measurements"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.executemany('''
                INSERT OR REPLACE INTO measurements (datetime, pm25, sitename, source)
                VALUES (:datetime, :pm25, :sitename, :source)
            ''', data)
            conn.commit()
            print(f"✅ Inserted {len(data)} measurements")
        except Exception as e:
            print(f"[ERROR] Bulk insert failed: {e}")
        finally:
            conn.close()
    
    def get_latest_datetime(self) -> Optional[str]:
        """Get the most recent datetime in database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT MAX(datetime) FROM measurements')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else None
    
    def get_last_n_hours(self, n: int = 720) -> List[Dict]:
        """Get last N hours of data, ordered by datetime ASC"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT datetime, pm25, sitename
            FROM measurements
            ORDER BY datetime DESC
            LIMIT ?
        ''', (n,))
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order (oldest first)
        rows.reverse()
        return [{'datetime': r[0], 'pm25': r[1], 'sitename': r[2]} for r in rows]
    
    def get_measurement_count(self) -> int:
        """Get total number of measurements"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM measurements')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def cleanup_old_data(self, keep_hours: int = 720):
        """
        DISABLED: Keep all historical data for RAG queries.
        This method is kept for backward compatibility but does nothing.
        """
        pass  # No cleanup - preserve all historical data
    
    def insert_predictions(self, prediction_time: str, predictions: List[Dict]):
        """Insert model predictions"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            data = [(prediction_time, p['target_datetime'], p['predicted_pm25']) for p in predictions]
            cursor.executemany('''
                INSERT OR REPLACE INTO predictions (prediction_time, target_datetime, predicted_pm25)
                VALUES (?, ?, ?)
            ''', data)
            conn.commit()
            print(f"✅ Stored {len(predictions)} predictions")
        except Exception as e:
            print(f"[ERROR] Failed to insert predictions: {e}")
        finally:
            conn.close()
    
    def get_latest_predictions(self) -> List[Dict]:
        """Get the most recent 24-hour predictions"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT target_datetime, predicted_pm25
            FROM predictions
            WHERE prediction_time = (SELECT MAX(prediction_time) FROM predictions)
            ORDER BY target_datetime ASC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [{'target_datetime': r[0], 'predicted_pm25': r[1]} for r in rows]
    
    def query_date_range(self, start_date: str, end_date: str) -> Dict:
        """
        Query PM2.5 statistics for a specific date range.
        Returns avg, min, max, count.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                AVG(pm25) as avg_pm25,
                MIN(pm25) as min_pm25,
                MAX(pm25) as max_pm25,
                COUNT(*) as count
            FROM measurements
            WHERE datetime BETWEEN ? AND ?
        ''', (start_date, end_date))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[3] > 0:
            return {
                'start_date': start_date,
                'end_date': end_date,
                'avg_pm25': round(row[0], 2),
                'min_pm25': round(row[1], 2),
                'max_pm25': round(row[2], 2),
                'count': row[3]
            }
        return None
    
    def query_exact_datetime(self, datetime_str: str) -> Dict:
        """Query exact PM2.5 value at specific datetime"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pm25, sitename
            FROM measurements
            WHERE datetime = ?
        ''', (datetime_str,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'datetime': datetime_str,
                'pm25': round(row[0], 2),
                'sitename': row[1]
            }
        return None
    
    def query_worst_day(self, start_date: str, end_date: str) -> Dict:
        """Find the day with highest average PM2.5"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                DATE(datetime) as day,
                AVG(pm25) as avg_pm25,
                MAX(pm25) as max_pm25
            FROM measurements
            WHERE datetime BETWEEN ? AND ?
            GROUP BY DATE(datetime)
            ORDER BY avg_pm25 DESC
            LIMIT 1
        ''', (start_date, end_date))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'date': row[0],
                'avg_pm25': round(row[1], 2),
                'max_pm25': round(row[2], 2)
            }
        return None
    
    def query_monthly_average(self, year: int, month: int) -> Dict:
        """Get monthly average PM2.5"""
        start_date = f"{year}-{month:02d}-01 00:00"
        end_date = f"{year}-{month:02d}-31 23:59"
        return self.query_date_range(start_date, end_date)
    
    def get_data_range(self) -> Dict:
        """Get the available data range in database"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT MIN(datetime), MAX(datetime) FROM measurements')
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'earliest': row[0],
                'latest': row[1]
            }
        return None