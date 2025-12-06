import re
from typing import List, Dict
from stock_match.stock_dictionary import StockDictionary
import logging

class StockMatcher:
    """뉴스 헤드라인에서 관련 종목 추출"""
    
    def __init__(self):
        self.dictionary = StockDictionary()
        self.logger = logging.getLogger(__name__)
    
    def match_stocks(self, headline: str) -> List[str]:
        """헤드라인에서 종목 티커 추출"""
        # 기본 매칭
        tickers = self.dictionary.find_tickers(headline)
        
        # 추가 패턴 매칭 (필요시)
        # 예: "005930(삼성전자)" 같은 패턴
        pattern = r'\b(\d{6})\b'
        matches = re.findall(pattern, headline)
        tickers.extend(matches)
        
        # 중복 제거
        return list(set(tickers))
    
    def add_tickers_to_news(self, news_items: List[Dict]) -> List[Dict]:
        """뉴스 아이템에 종목 정보 추가"""
        for item in news_items:
            headline = item.get('headline', '')
            summary = item.get('summary', '')
            
            # 헤드라인과 요약에서 종목 찾기
            text = f"{headline} {summary}"
            tickers = self.match_stocks(text)
            
            item['tickers'] = tickers
            item['ticker_names'] = [
                self.dictionary.get_name(ticker) for ticker in tickers
            ]
        
        return news_items
    
    def filter_by_ticker(self, news_items: List[Dict], ticker: str) -> List[Dict]:
        """특정 종목 뉴스만 필터링"""
        return [
            item for item in news_items 
            if ticker in item.get('tickers', [])
        ]


# 테스트
if __name__ == "__main__":
    import json
    
    matcher = StockMatcher()
    
    # 크롤링된 뉴스 로드
    with open('data/news_raw/20251202_09.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    news_items = data['news']  # 처음 10개만 테스트
    
    # 종목 매칭
    news_with_tickers = matcher.add_tickers_to_news(news_items)
    
    # 결과 출력
    for item in news_with_tickers:
        print(f"\n헤드라인: {item['headline']}")
        print(f"관련 종목: {item.get('tickers', [])}")
        print(f"종목명: {item.get('ticker_names', [])}")