import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

from stock_match.stock_dictionary import StockDictionary

# AWS S3 설정
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "quartz-bucket")
S3_CANDIDATES_KEY = "select-ticker/stock_candidates.json"


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
    
    def get_top_stocks(self, aggregated: Dict[str, Dict], top_n: int = 5) -> List[Dict]:
        """
        상위 N개 종목 선정 (중요도 기반 필터링)
        
        중요도 점수 계산:
        - 시총 등급 가중치: 25% (LARGE=1.0, MID=0.6, SMALL=0.3)
        - 감성 점수: 40%
        - 뉴스 개수 (언론 언급): 25%
        - 우선순위: 10%
        """
        def calculate_importance_score(stock_data: Dict) -> float:
            ticker = stock_data['ticker']
            
            # 시총 가중치 (25%)
            market_cap_weight = self.dictionary.get_market_cap_weight(ticker)
            
            # 우선순위 가중치
            priority_weight = {'HIGH': 1.0, 'MID': 0.6, 'LOW': 0.3}
            
            # 뉴스 개수 정규화 (최대 10개 기준)
            news_score = min(stock_data['news_count'] / 10, 1.0)
            
            # 최종 점수 계산
            score = market_cap_weight * 0.25  # 시총 25%
            score += stock_data['avg_sentiment'] * 0.40  # 감성 40%
            score += news_score * 0.25  # 뉴스 개수 25%
            score += priority_weight.get(stock_data['priority'], 0.3) * 0.10  # 우선순위 10%
            
            return score
        
        # 점수 계산 및 정렬
        stock_list = list(aggregated.values())
        for stock in stock_list:
            stock['final_score'] = calculate_importance_score(stock)
            stock['market_cap_tier'] = self.dictionary.get_market_cap_tier(stock['ticker'])
        
        # 상위 N개 선정 (기본 5개)
        top_stocks = sorted(stock_list, key=lambda x: x['final_score'], reverse=True)[:top_n]
        
        return top_stocks
    
    def save_candidates(self, aggregated: Dict[str, Dict], 
                       output_file: str = "data/stock_candidates.json") -> str:
        """거래 후보 종목 저장 (로컬 + S3)"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 상위 종목 선정 (중요도 기반, 최대 5개)
        top_stocks = self.get_top_stocks(aggregated, top_n=5)
        
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
        
        # 로컬 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"💾 Saved {len(top_stocks)} top candidates to {output_path}")
        
        # S3 업로드
        self._upload_to_s3(data)
        
        return str(output_path)
    
    def _upload_to_s3(self, data: Dict) -> bool:
        """S3에 후보 종목 데이터 업로드"""
        try:
            s3_client = boto3.client('s3', region_name=AWS_REGION)
            
            json_content = json.dumps(data, ensure_ascii=False, indent=2)
            
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=S3_CANDIDATES_KEY,
                Body=json_content.encode('utf-8'),
                ContentType="application/json"
            )
            
            self.logger.info(f"☁️ Uploaded candidates to S3: s3://{S3_BUCKET_NAME}/{S3_CANDIDATES_KEY}")
            return True
            
        except ClientError as e:
            self.logger.error(f"Failed to upload to S3: {e}")
            return False
        except Exception as e:
            self.logger.error(f"S3 upload error: {e}")
            return False
    
    def print_summary(self, aggregated: Dict[str, Dict], top_n: int = 5):
        """결과 요약 출력 (중요도 기반 상위 종목)"""
        top_stocks = self.get_top_stocks(aggregated, top_n=top_n)
        
        print("\n" + "="*80)
        print(f"📊 TOP {top_n} STOCK CANDIDATES (Importance-Based)")
        print("="*80)
        
        market_cap_emoji = {'LARGE': '🏢', 'MID': '🏠', 'SMALL': '🏚️'}
        priority_emoji = {'HIGH': '🔥', 'MID': '⚡', 'LOW': '💡'}
        
        for i, stock in enumerate(top_stocks, 1):
            p_emoji = priority_emoji.get(stock['priority'], '❓')
            m_emoji = market_cap_emoji.get(stock.get('market_cap_tier', 'SMALL'), '❓')
            
            print(f"\n[{i}] {p_emoji} {stock['priority']} | {m_emoji} {stock.get('market_cap_tier', 'N/A')} - {stock['ticker']}: {stock['name']}")
            print(f"    섹터: {stock['sector']}")
            print(f"    평균 감성: {stock['avg_sentiment']:.3f} (뉴스 {stock['news_count']}개)")
            print(f"    긍정/부정: {stock['positive_count']}개 / {stock['negative_count']}개")
            print(f"    중요도 점수: {stock['final_score']:.3f}")
            print(f"    이유: {stock['reasoning']}")
            if stock['top_headlines']:
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