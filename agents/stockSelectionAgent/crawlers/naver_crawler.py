from .base_crawler import BaseCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict

class NaverFinanceCrawler(BaseCrawler):
    """네이버 금융 뉴스 크롤러"""
    
    BASE_URL = "https://finance.naver.com"
    NEWS_LIST_URL = f"{BASE_URL}/news/news_list.naver"
    
    def __init__(self):
        super().__init__("NaverFinance")
    
    def get_news_list_url(self, page: int = 1) -> str:
        """뉴스 리스트 URL"""
        return f"{self.NEWS_LIST_URL}?mode=LSS2D&section_id=101&section_id2=258&page={page}"
    
    def parse_news_list(self, html: str) -> List[Dict]:
        """네이버 금융 HTML 파싱"""
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # dd 또는 li 구조
        items = soup.select('.newsList dd') or soup.select('.newsList li')
        
        for item in items:
            try:
                link = item.select_one('a')
                if not link:
                    continue
                
                headline = link.get_text(strip=True)
                href_raw = link.get('href', '')
                href = str(href_raw) if href_raw else ''
                
                if not headline or len(headline) < 5:
                    continue
                
                url = urljoin(self.BASE_URL, href)
                
                # 추가 정보
                press_tag = item.select_one('.press')
                press = press_tag.get_text(strip=True) if press_tag else "Unknown"
                
                time_tag = item.select_one('.wdate')
                published_time = time_tag.get_text(strip=True) if time_tag else ""
                
                summary_tag = item.select_one('.articleSummary')
                summary = summary_tag.get_text(strip=True) if summary_tag else ""
                
                news_items.append({
                    'headline': headline,
                    'url': url,
                    'press': press,
                    'published_time': published_time,
                    'summary': summary,
                    'source': self.name,
                    'crawled_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error parsing item: {e}")
                continue
        
        return news_items