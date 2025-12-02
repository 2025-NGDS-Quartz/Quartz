import logging
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import time
from typing import List, Dict, Optional

# 크롤러 import
from crawlers.naver_crawler import NaverFinanceCrawler
from crawlers.hankyung_crawler import HankyungCrawler
from crawlers.mk_crawler import MKCrawler

class MultiNewsCrawler:
    """여러 뉴스 사이트를 통합 크롤링"""
    
    def __init__(self):
        self.setup_logging()
        self.crawlers = self._initialize_crawlers()
        
    def setup_logging(self):
        """로깅 설정"""
        log_dir = Path("./data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "multi_crawler.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_crawlers(self) -> Dict:
        """모든 크롤러 초기화"""
        return {
            'naver': NaverFinanceCrawler(),
            'hankyung': HankyungCrawler(),
            'mk': MKCrawler(),
        }
    
    def crawl_all_sources(self, pages_per_source: int = 3) -> List[Dict]:
        """모든 소스에서 뉴스 크롤링"""
        all_news = []
        
        self.logger.info("=" * 60)
        self.logger.info("Starting multi-source news crawling...")
        self.logger.info("=" * 60)
        
        for source_name, crawler in self.crawlers.items():
            self.logger.info(f"\n📰 Crawling from {source_name}...")
            
            try:
                news_items = crawler.crawl_multiple_pages(max_pages=pages_per_source)
                all_news.extend(news_items)
                self.logger.info(f"✅ {source_name}: {len(news_items)} news collected")
                
                # 소스 간 딜레이
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"❌ Error crawling {source_name}: {e}", exc_info=True)
                continue
        
        return all_news
    
    def crawl_specific_sources(self, sources: List[str], pages: int = 3) -> List[Dict]:
        """특정 소스만 크롤링"""
        all_news = []
        
        for source_name in sources:
            if source_name not in self.crawlers:
                self.logger.warning(f"Unknown source: {source_name}")
                continue
            
            crawler = self.crawlers[source_name]
            self.logger.info(f"Crawling from {source_name}...")
            
            try:
                news_items = crawler.crawl_multiple_pages(max_pages=pages)
                all_news.extend(news_items)
                self.logger.info(f"✅ {source_name}: {len(news_items)} news")
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
                continue
        
        return all_news
    
    def save_to_file(self, news_items: List[Dict], filename: Optional[str] = None) -> str:
        """뉴스 저장"""
        output_dir = Path("./data/news_raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            now = datetime.now()
            filename = now.strftime("%Y%m%d_%H.json")
        
        filepath = output_dir / filename
        
        # 소스별 통계
        source_stats = {}
        for item in news_items:
            source = item.get('source', 'Unknown')
            source_stats[source] = source_stats.get(source, 0) + 1
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_count': len(news_items),
            'sources': list(source_stats.keys()),
            'source_stats': source_stats,
            'news': news_items
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\n💾 Saved {len(news_items)} news to {filepath}")
        self.logger.info(f"📊 Source breakdown: {source_stats}")
        
        return str(filepath)
    
    def run(self, sources: Optional[List[str]] = None, pages: int = 3) -> str:
        """크롤링 실행"""
        start_time = time.time()
        
        if sources:
            news_items = self.crawl_specific_sources(sources, pages)
        else:
            news_items = self.crawl_all_sources(pages)
        
        filepath = self.save_to_file(news_items)
        
        elapsed = time.time() - start_time
        self.logger.info(f"\n⏱️  Completed in {elapsed:.2f} seconds")
        self.logger.info(f"📈 Total news collected: {len(news_items)}")
        
        return filepath


def main():
    """실행 예시"""
    crawler = MultiNewsCrawler()
    
    # 옵션 1: 모든 소스에서 크롤링
    # filepath = crawler.run(pages=3)
    
    # 옵션 2: 특정 소스만
    filepath = crawler.run(sources=['naver', 'hankyung', 'mk'], pages=3)
    
    print(f"\n✅ Crawling completed!")
    print(f"📁 Output: {filepath}")


if __name__ == "__main__":
    main()