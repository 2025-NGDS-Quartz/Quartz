import logging
import time
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import signal
import sys

from news_crawler import MultiNewsCrawler
from news_pipeline import NewsPipeline

class AutomationScheduler:
    """자동화 스케줄러"""
    
    def __init__(self):
        self.setup_logging()
        self.scheduler = BackgroundScheduler()
        self.crawler = MultiNewsCrawler()
        self.pipeline = NewsPipeline()
        self.logger = logging.getLogger(__name__)
        
        # 실행 통계
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'last_run': None,
            'last_success': None,
            'last_error': None
        }
    
    def setup_logging(self):
        """로깅 설정"""
        log_dir = Path("./data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 핸들러
        file_handler = logging.FileHandler(
            log_dir / "scheduler.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        self.logger = logging.getLogger(__name__)
    
    def crawl_and_process(self):
        """크롤링 및 처리 작업"""
        self.logger.info("="*80)
        self.logger.info("🤖 AUTOMATED TASK STARTED")
        self.logger.info("="*80)
        
        self.stats['total_runs'] += 1
        self.stats['last_run'] = datetime.now().isoformat()
        
        try:
            # 1. 크롤링
            self.logger.info("📰 Step 1/2: Crawling news...")
            crawl_start = time.time()
            
            news_file = self.crawler.run(sources=['naver', 'hankyung', 'mk'], pages=3)
            
            crawl_time = time.time() - crawl_start
            self.logger.info(f"✅ Crawling completed in {crawl_time:.2f}s")
            self.logger.info(f"📁 Saved to: {news_file}")
            
            # 2. 파이프라인 처리
            self.logger.info("🔄 Step 2/2: Processing pipeline...")
            pipeline_start = time.time()
            
            result_file = self.pipeline.run(news_file)
            
            pipeline_time = time.time() - pipeline_start
            self.logger.info(f"✅ Pipeline completed in {pipeline_time:.2f}s")
            self.logger.info(f"📁 Results: {result_file}")
            
            # 성공
            self.stats['successful_runs'] += 1
            self.stats['last_success'] = datetime.now().isoformat()
            
            total_time = crawl_time + pipeline_time
            
            self.logger.info("="*80)
            self.logger.info(f"✅ AUTOMATED TASK COMPLETED (Total: {total_time:.2f}s)")
            self.logger.info(f"📊 Success Rate: {self.stats['successful_runs']}/{self.stats['total_runs']}")
            self.logger.info("="*80)
            
        except Exception as e:
            self.stats['failed_runs'] += 1
            self.stats['last_error'] = str(e)
            
            self.logger.error("="*80)
            self.logger.error(f"❌ AUTOMATED TASK FAILED")
            self.logger.error(f"Error: {e}", exc_info=True)
            self.logger.error("="*80)
    
    def get_statistics(self):
        """통계 출력"""
        self.logger.info("\n" + "="*80)
        self.logger.info("📊 SCHEDULER STATISTICS")
        self.logger.info("="*80)
        self.logger.info(f"Total runs: {self.stats['total_runs']}")
        self.logger.info(f"Successful: {self.stats['successful_runs']}")
        self.logger.info(f"Failed: {self.stats['failed_runs']}")
        
        if self.stats['last_run']:
            self.logger.info(f"Last run: {self.stats['last_run']}")
        if self.stats['last_success']:
            self.logger.info(f"Last success: {self.stats['last_success']}")
        if self.stats['last_error']:
            self.logger.info(f"Last error: {self.stats['last_error']}")
        
        self.logger.info("="*80 + "\n")
    
    def start(self, run_immediately: bool = True):
        """스케줄러 시작"""
        self.logger.info("🚀 Starting automation scheduler...")
        
        # 12시간마다 실행 (매일 0시, 12시 정각)
        self.scheduler.add_job(
            self.crawl_and_process,
            trigger=CronTrigger(hour='0,12', minute=0),  # 매일 0시, 12시
            id='twice_daily_crawl',
            name='Twice Daily News Crawling & Processing',
            max_instances=1  # 동시에 하나만 실행
        )
        
        # 매일 자정에 통계 출력
        self.scheduler.add_job(
            self.get_statistics,
            trigger=CronTrigger(hour=0, minute=0),
            id='daily_stats',
            name='Daily Statistics'
        )
        
        self.scheduler.start()
        
        self.logger.info("✅ Scheduler started")
        self.logger.info("⏰ Schedule: Every 12 hours (00:00, 12:00)")
        self.logger.info("📊 Stats: Daily at 00:00")
        
        # 즉시 실행 옵션
        if run_immediately:
            self.logger.info("🏃 Running immediately...")
            self.crawl_and_process()
        else:
            self.logger.info("⏳ Waiting for next scheduled time...")
        
        # 다음 실행 시간 출력
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            self.logger.info(f"📅 Next run of '{job.name}': {job.next_run_time}")
    
    def stop(self):
        """스케줄러 중지"""
        self.logger.info("🛑 Stopping scheduler...")
        self.scheduler.shutdown()
        self.get_statistics()
        self.logger.info("✅ Scheduler stopped")


def signal_handler(signum, frame):
    """종료 신호 처리"""
    print("\n⚠️  Received interrupt signal. Shutting down gracefully...")
    sys.exit(0)


def main():
    """메인 실행"""
    # 신호 핸들러 등록 (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 스케줄러 시작
    scheduler = AutomationScheduler()
    
    print("\n" + "🤖 "*30)
    print("AUTOMATED STOCK SELECTION AGENT")
    print("🤖 "*30)
    print("\n📋 Configuration:")
    print("  - Crawl & Process: Every 12 hours (00:00, 12:00)")
    print("  - Statistics: Daily at 00:00")
    print("  - Sources: Naver, Hankyung, MK")
    print("  - Pages per source: 3")
    print("\n💡 Press Ctrl+C to stop\n")
    print("="*80 + "\n")
    
    try:
        # 스케줄러 시작 (즉시 실행)
        scheduler.start(run_immediately=True)
        
        # 계속 실행
        while True:
            time.sleep(60)  # 1분마다 체크
            
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        print("\n👋 Goodbye!\n")


if __name__ == "__main__":
    main()