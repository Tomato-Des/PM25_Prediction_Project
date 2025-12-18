import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from backend.config import Config
from backend.database import Database

class EPACrawler:
    def __init__(self, db: Database = None):
        self.api_url = Config.EPA_API_URL
        self.api_key = Config.EPA_API_KEY
        self.site_name = Config.SITE_NAME
        self.db = db or Database()
        self.last_valid_pm25 = None
    
    def clean_pm25_value(self, raw_value) -> Optional[float]:
        """
        Clean PM2.5 value from API response.
        Handle 'x', 'NaN', '', None, and invalid strings.
        """
        if raw_value in ['x', 'NaN', '', None, 'ND']:
            return None
        try:
            return float(raw_value)
        except (ValueError, TypeError):
            print(f"[WARN] Invalid PM2.5 value: {raw_value}")
            return None
    
    def fetch_latest_data(self) -> List[Dict]:
        """
        Fetch latest PM2.5 data from EPA API.
        Returns list of {datetime, pm25, sitename} dicts.
        """
        try:
            params = {
                'api_key': self.api_key,
                'format': 'json'
            }
            
            print(f"📡 Fetching data from EPA API...")
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            records = data.get('records', [])
            
            # Filter for PM2.5 items and target site
            site_data = []
            for record in records:
                if record.get('itemengname') == 'PM2.5' and record.get('sitename') == self.site_name:
                    datetime_str = record.get('monitordate', '')  # Format: "2025-11-21 14:00"
                    pm25_raw = record.get('concentration', '')
                    
                    if datetime_str:
                        pm25_clean = self.clean_pm25_value(pm25_raw)
                        if pm25_clean is not None:
                            site_data.append({
                                'datetime': datetime_str,
                                'pm25': pm25_clean,
                                'sitename': self.site_name
                            })
            
            if site_data:
                print(f"✅ Fetched {len(site_data)} records for {self.site_name}")
            else:
                print(f"[WARN] No data found for {self.site_name}")
            
            return site_data
        
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] API request failed: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] Crawler failed: {e}")
            return []
    
    def forward_fill(self, data: List[Dict]) -> List[Dict]:
        """
        Apply forward-fill to missing PM2.5 values.
        Sort by datetime first to maintain temporal order.
        """
        if not data:
            return data
        
        # Sort by datetime
        data_sorted = sorted(data, key=lambda x: x['datetime'])
        
        filled_data = []
        for record in data_sorted:
            if record['pm25'] is None or record['pm25'] == '':
                if self.last_valid_pm25 is not None:
                    print(f"[DEBUG] Forward-fill at {record['datetime']}: using {self.last_valid_pm25}")
                    record['pm25'] = self.last_valid_pm25
                else:
                    print(f"[ERROR] No valid PM2.5 for forward-fill at {record['datetime']}, skipping")
                    continue
            else:
                self.last_valid_pm25 = record['pm25']
            
            filled_data.append(record)
        
        return filled_data
    
    def crawl_and_store(self):
        """
        Main crawler function:
        1. Fetch latest data from EPA API
        2. Clean and forward-fill missing values
        3. Store in database
        """
        print("\n" + "="*60)
        print(f"🕐 CRAWLER START: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Fetch data
        raw_data = self.fetch_latest_data()
        if not raw_data:
            print("[WARN] No data fetched, skipping this cycle")
            return
        
        # Get last valid PM2.5 from database for forward-fill continuity
        last_records = self.db.get_last_n_hours(1)
        if last_records:
            self.last_valid_pm25 = last_records[0]['pm25']
        
        # Apply forward-fill
        filled_data = self.forward_fill(raw_data)
        
        # Store in database
        if filled_data:
            bulk_data = [
                {
                    'datetime': record['datetime'],
                    'pm25': record['pm25'],
                    'sitename': record['sitename'],
                    'source': 'crawler'
                }
                for record in filled_data
            ]
            self.db.insert_measurements_bulk(bulk_data)
            print(f"✅ Crawled and Stored {len(bulk_data)} measurements")
            print(f"[INFO] Current total measurements in DB: {self.db.get_measurement_count()}")
            print(f"[INFO] Latest measurement datetime: {self.db.get_latest_datetime()}")
            print(f"[INFO] Current Predictions count: {len(self.db.get_latest_predictions())}")
        
        # No cleanup - preserve all historical data
        
        print("="*60)
        print(f"✅ CRAWLER END: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")