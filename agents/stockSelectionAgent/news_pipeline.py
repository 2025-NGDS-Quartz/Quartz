# news_pipeline.py (완전 버전)

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from stock_matcher import StockMatcher
from sentiment.sentiment_analyzer import SentimentAnalyzer
from stock_aggregator import StockAggregator

class NewsPipeline:
    """뉴스 크롤링 → 종목 매칭 → 감성 분석 → 종목별 집계 통합 파이프라인"""
    
    def __init__(self):
        self.setup_logging()
        self.stock_matcher = StockMatcher()
        self.sentiment_analyzer = SentimentAnalyzer(batch_size=20)
        self.aggregator = StockAggregator()
        self.logger = logging.getLogger(__name__)
    
    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    
    def load_news_file(self, filepath: str) -> List[Dict]:
        """크롤링된 뉴스 파일 로드"""
        self.logger.info(f"📂 Loading news from {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        news_items = data.get('news', [])
        self.logger.info(f"✅ Loaded {len(news_items)} news items")
        
        return news_items
    
    def process_news(self, news_items: List[Dict]) -> List[Dict]:
        """뉴스 처리: 종목 매칭 + 감성 분석"""
        
        # 1. 종목 매칭
        self.logger.info("\n" + "="*60)
        self.logger.info("🔍 Step 1: Stock Matching")
        self.logger.info("="*60)
        
        news_items = self.stock_matcher.add_tickers_to_news(news_items)
        
        matched_count = sum(1 for item in news_items if item.get('tickers'))
        self.logger.info(f"✅ Matched {matched_count}/{len(news_items)} news to stocks")
        
        # 2. 감성 분석
        self.logger.info("\n" + "="*60)
        self.logger.info("😊 Step 2: Sentiment Analysis")
        self.logger.info("="*60)
        
        # 헤드라인 추출
        headlines = [item['headline'] for item in news_items]
        
        # 감성 분석
        sentiment_results = self.sentiment_analyzer.analyze_headlines(headlines)
        
        # 결과 병합
        for i, item in enumerate(news_items):
            if i < len(sentiment_results):
                sentiment = sentiment_results[i]
                item['sentiment'] = sentiment.get('sentiment', 'neutral')
                item['sentiment_score'] = sentiment.get('score', 0.5)
                item['sentiment_confidence'] = sentiment.get('confidence', 0.0)
                item['sentiment_reasoning'] = sentiment.get('reasoning', '')
        
        # 통계
        stats = self.sentiment_analyzer.get_statistics()
        self.logger.info(f"\n📊 Sentiment Analysis Statistics:")
        for key, value in stats.items():
            self.logger.info(f"  {key}: {value}")
        
        return news_items
    
    def save_processed_news(self, news_items: List[Dict], output_file: Optional[str] = None) -> str:
        """처리된 뉴스 저장"""
        output_dir = Path("./data/processed")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not output_file:
            now = datetime.now()
            output_file = now.strftime("processed_%Y%m%d_%H.json")
        
        filepath = output_dir / output_file
        
        # 통계 계산
        total = len(news_items)
        with_tickers = sum(1 for item in news_items if item.get('tickers'))
        sentiment_dist = {
            'positive': sum(1 for item in news_items if item.get('sentiment') == 'positive'),
            'negative': sum(1 for item in news_items if item.get('sentiment') == 'negative'),
            'neutral': sum(1 for item in news_items if item.get('sentiment') == 'neutral')
        }
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_count': total,
            'statistics': {
                'news_with_stocks': with_tickers,
                'stock_match_rate': f"{with_tickers/total*100:.1f}%" if total > 0 else "0%",
                'sentiment_distribution': sentiment_dist
            },
            'news': news_items
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"\n💾 Saved processed news to {filepath}")
        return str(filepath)
    
    def run(self, input_file: str, output_file: Optional[str] = None) -> str:
        """전체 파이프라인 실행"""
        self.logger.info("\n" + "🚀 "*30)
        self.logger.info("NEWS PROCESSING PIPELINE START")
        self.logger.info("🚀 "*30)
        
        start_time = datetime.now()
        
        try:
            # 1. 뉴스 로드
            news_items = self.load_news_file(input_file)
            
            # 2. 처리 (종목 매칭 + 감성 분석)
            processed_news = self.process_news(news_items)
            
            # 3. 저장
            output_path = self.save_processed_news(processed_news, output_file)
            
            # ✅ 4. 종목별 집계 (새로 추가)
            self.logger.info("\n" + "="*60)
            self.logger.info("📊 Step 3: Stock Aggregation")
            self.logger.info("="*60)
            
            aggregated = self.aggregator.aggregate_by_stock(processed_news)
            candidate_path = self.aggregator.save_candidates(aggregated)
            
            # 상위 10개 출력
            self.aggregator.print_summary(aggregated, top_n=10)
            
            # 완료
            elapsed = (datetime.now() - start_time).total_seconds()
            
            self.logger.info("\n" + "✅ "*30)
            self.logger.info(f"PIPELINE COMPLETED in {elapsed:.2f}s")
            self.logger.info("✅ "*30)
            self.logger.info(f"\n📁 Outputs:")
            self.logger.info(f"  - Processed news: {output_path}")
            self.logger.info(f"  - Stock candidates: {candidate_path}")
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
            raise


def main():
    """실행 예시"""
    pipeline = NewsPipeline()
    
    # 가장 최근 크롤링 파일 찾기
    news_dir = Path("./data/news_raw")
    news_files = sorted(news_dir.glob("*.json"), reverse=True)
    
    if not news_files:
        print("❌ 크롤링된 뉴스 파일이 없습니다.")
        print("먼저 multi_news_crawler.py를 실행하세요.")
        return
    
    # 최신 파일 사용
    latest_file = news_files[0]
    print(f"\n📁 Processing file: {latest_file.name}")
    
    # 파이프라인 실행
    output_path = pipeline.run(str(latest_file))
    
    print(f"\n✅ Done!")


if __name__ == "__main__":
    main()