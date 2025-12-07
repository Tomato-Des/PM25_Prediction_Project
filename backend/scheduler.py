from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from backend.config import Config
from backend.database import Database
from backend.crawler import EPACrawler
from backend.prediction_service import PredictionService

class HourlyScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.timezone = pytz.timezone(Config.TIMEZONE)
        self.db = Database()
        self.crawler = EPACrawler(self.db)
        self.predictor = PredictionService(self.db)
    
    def hourly_task(self):
        """
        Main hourly task:
        1. Crawl new data from EPA API
        2. Run model inference
        3. Store predictions
        """
        print("\n" + "🔄"*30)
        print(f"⏰ HOURLY TASK TRIGGERED: {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("🔄"*30 + "\n")
        
        try:
            # Step 1: Crawl and store new data
            self.crawler.crawl_and_store()
            
            # Step 2: Check if we have enough data for prediction
            count = self.db.get_measurement_count()
            if count >= Config.SEQUENCE_LENGTH:
                # Step 3: Generate predictions
                self.predictor.predict_24h()
            else:
                print(f"[INFO] Not enough data for prediction: {count}/{Config.SEQUENCE_LENGTH} hours")
        
        except Exception as e:
            print(f"[ERROR] Hourly task failed: {e}")
            import traceback
            traceback.print_exc()
    
    def start(self):
        """Start the hourly scheduler"""
        # Schedule to run at the top of every hour (0 minutes)
        # Example: 00:00, 01:00, 02:00, etc.
        self.scheduler.add_job(
            self.hourly_task,
            trigger=CronTrigger(minute=0, timezone=self.timezone),
            id='hourly_crawler_predictor',
            name='Hourly EPA Crawler + Model Prediction',
            replace_existing=True
        )
        
        self.scheduler.start()
        print("\n" + "="*60)
        print("⏰ SCHEDULER STARTED")
        print("="*60)
        print(f"✅ Hourly task scheduled (runs at minute 0 of every hour)")
        print(f"   Timezone: {Config.TIMEZONE}")
        print(f"   Next run: {self.scheduler.get_jobs()[0].next_run_time}")
        print("="*60 + "\n")
    
    def run_now(self):
        """Run the hourly task immediately (for testing/initialization)"""
        print("🚀 Running hourly task immediately...")
        self.hourly_task()
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("⏹️  Scheduler stopped")