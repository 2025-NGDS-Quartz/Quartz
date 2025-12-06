import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from collections import defaultdict
from stock_match.stock_dictionary import StockDictionary

class StockAggregator:
    """종목별 뉴스 집계 및 분석"""
    
    def __init__(self):
        self.dictionary = StockDictionary()
        self.logger = logging.getLogger(__name__)
    
    def aggregate_by_stock(self, news_items: List[Dict]) -> Dict[str, Dict]:
        """종목별로 뉴스 집계"""
        self.logger.info("📊 Aggregating news by stock...")
        
        # 종목별 뉴스 그룹화
        stock_news = defaultdict(list)
        
        for item in news_items:
            tickers = item.get('tickers', [])
            for ticker in tickers:
                stock_news[ticker].append(item)
        
        self.logger.info(f"✅ Found {len(stock_news)} unique stocks")
        
        # 종목별 통계 계산
        aggregated = {}
        
        for ticker, news_list in stock_news.items():
            aggregated[ticker] = self._calculate_stock_stats(ticker, news_list)
        
        return aggregated
    
    def _calculate_stock_stats(self, ticker: str, news_list: List[Dict]) -> Dict:
        """개별 종목 통계 계산"""
        # 기본 정보
        name = self.dictionary.get_name(ticker)
        sector = self.dictionary.get_sector(ticker)
        
        # 감성 점수 수집
        sentiment_scores = []
        sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for news in news_list:
            score = news.get('sentiment_score', 0.5)
            sentiment_scores.append(score)
            
            sentiment = news.get('sentiment', 'neutral')
            sentiments[sentiment] += 1
        
        # 통계
        total_news = len(news_list)
        avg_sentiment = sum(sentiment_scores) / total_news if total_news > 0 else 0.5
        
        positive_ratio = sentiments['positive'] / total_news if total_news > 0 else 0
        negative_ratio = sentiments['negative'] / total_news if total_news > 0 else 0
        neutral_ratio = sentiments['neutral'] / total_news if total_news > 0 else 0
        
        # 우선순위 결정
        priority = self._determine_priority(avg_sentiment, total_news, positive_ratio)
        
        # 추천 이유
        reasoning = self._generate_reasoning(
            avg_sentiment, total_news, 
            sentiments['positive'], sentiments['negative']
        )
        
        # 상위 헤드라인 (최대 5개)
        top_headlines = [
            news['headline'] 
            for news in sorted(news_list, key=lambda x: x.get('sentiment_score', 0), reverse=True)[:5]
        ]
        
        return {
            'ticker': ticker,
            'name': name,
            'sector': sector,
            'avg_sentiment': round(avg_sentiment, 3),
            'news_count': total_news,
            'positive_count': sentiments['positive'],
            'negative_count': sentiments['negative'],
            'neutral_count': sentiments['neutral'],
            'positive_ratio': round(positive_ratio, 3),
            'negative_ratio': round(negative_ratio, 3),
            'neutral_ratio': round(neutral_ratio, 3),
            'priority': priority,
            'reasoning': reasoning,
            'top_headlines': top_headlines
        }
    
    def _determine_priority(self, avg_sentiment: float, news_count: int, positive_ratio: float) -> str:
        """우선순위 결정 로직"""
        # HIGH: 평균 감성 0.7 이상 + 뉴스 3개 이상
        if avg_sentiment >= 0.7 and news_count >= 3:
            return "HIGH"
        
        # MID: 평균 감성 0.5 이상 + 뉴스 2개 이상
        elif avg_sentiment >= 0.5 and news_count >= 2:
            return "MID"
        
        # LOW: 그 외
        else:
            return "LOW"
    
    def _generate_reasoning(self, avg_sentiment: float, news_count: int, 
                           positive_count: int, negative_count: int) -> str:
        """추천 이유 생성"""
        sentiment_desc = "긍정적" if avg_sentiment >= 0.6 else "부정적" if avg_sentiment <= 0.4 else "중립적"
        
        reasoning = f"평균 감성 {avg_sentiment:.2f}({sentiment_desc}), "
        reasoning += f"총 {news_count}개 뉴스, "
        reasoning += f"긍정 {positive_count}개, 부정 {negative_count}개"
        
        return reasoning
    
    def get_top_stocks(self, aggregated: Dict[str, Dict], top_n: int = 20) -> List[Dict]:
        """상위 N개 종목 선정"""
        # 우선순위 점수 계산
        def calculate_score(stock_data: Dict) -> float:
            priority_weight = {'HIGH': 3.0, 'MID': 2.0, 'LOW': 1.0}
            
            score = stock_data['avg_sentiment'] * 0.7  # 감성 점수 70%
            score += (stock_data['news_count'] / 10) * 0.2  # 뉴스 개수 20%
            score += priority_weight[stock_data['priority']] * 0.1  # 우선순위 10%
            
            return score
        
        # 점수 계산 및 정렬
        stock_list = list(aggregated.values())
        for stock in stock_list:
            stock['final_score'] = calculate_score(stock)
        
        # 상위 N개 선정
        top_stocks = sorted(stock_list, key=lambda x: x['final_score'], reverse=True)[:top_n]
        
        return top_stocks
    
    def save_candidates(self, aggregated: Dict[str, Dict], 
                       output_file: str = "data/stock_candidates.json") -> str:
        """거래 후보 종목 저장"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 상위 종목 선정
        top_stocks = self.get_top_stocks(aggregated, top_n=20)
        
        # 통계
        total_stocks = len(aggregated)
        high_priority = sum(1 for s in aggregated.values() if s['priority'] == 'HIGH')
        mid_priority = sum(1 for s in aggregated.values() if s['priority'] == 'MID')
        low_priority = sum(1 for s in aggregated.values() if s['priority'] == 'LOW')
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'total_stocks': total_stocks,
            'statistics': {
                'high_priority': high_priority,
                'mid_priority': mid_priority,
                'low_priority': low_priority
            },
            'top_candidates': top_stocks,
            'all_stocks': aggregated
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"💾 Saved {len(top_stocks)} top candidates to {output_path}")
        return str(output_path)
    
    def print_summary(self, aggregated: Dict[str, Dict], top_n: int = 10):
        """결과 요약 출력"""
        top_stocks = self.get_top_stocks(aggregated, top_n=top_n)
        
        print("\n" + "="*80)
        print(f"📊 TOP {top_n} STOCK CANDIDATES")
        print("="*80)
        
        for i, stock in enumerate(top_stocks, 1):
            priority_emoji = {
                'HIGH': '🔥',
                'MID': '⚡',
                'LOW': '💡'
            }
            emoji = priority_emoji.get(stock['priority'], '❓')
            
            print(f"\n[{i}] {emoji} {stock['priority']} - {stock['ticker']}: {stock['name']}")
            print(f"    섹터: {stock['sector']}")
            print(f"    평균 감성: {stock['avg_sentiment']:.3f} (뉴스 {stock['news_count']}개)")
            print(f"    긍정/부정: {stock['positive_count']}개 / {stock['negative_count']}개")
            print(f"    최종 점수: {stock['final_score']:.3f}")
            print(f"    이유: {stock['reasoning']}")
            print(f"    대표 헤드라인: {stock['top_headlines'][0][:60]}...")


# 테스트
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    aggregator = StockAggregator()
    
    # 처리된 뉴스 파일 로드
    processed_dir = Path("./data/processed")
    processed_files = sorted(processed_dir.glob("*.json"), reverse=True)
    
    if not processed_files:
        print("❌ 처리된 뉴스 파일이 없습니다.")
        print("먼저 news_pipeline.py를 실행하세요.")
    else:
        latest_file = processed_files[0]
        print(f"📁 Loading: {latest_file.name}\n")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        news_items = data['news']
        
        # 집계
        aggregated = aggregator.aggregate_by_stock(news_items)
        
        # 요약 출력
        aggregator.print_summary(aggregated, top_n=10)
        
        # 저장
        output_path = aggregator.save_candidates(aggregated)
        print(f"\n✅ Saved to: {output_path}")