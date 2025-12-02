# crawlers/hankyung_crawler.py

from .base_crawler import BaseCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict

class HankyungCrawler(BaseCrawler):
    """한국경제 뉴스 크롤러"""
    
    BASE_URL = "https://www.hankyung.com"
    
    def __init__(self):
        super().__init__("Hankyung")
    
    def get_news_list_url(self, page: int = 1) -> str:
        """한국경제 뉴스 리스트 URL"""
        return f"{self.BASE_URL}/economy/macro?page={page}"
    
    def parse_news_list(self, html: str) -> List[Dict]:
        """한국경제 HTML 파싱"""
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # 한국경제 구조에 맞게 조정 (실제 구조 확인 필요)
        items = soup.select('.news-list li') or soup.select('article')
        
        for item in items:
            try:
                # 제목 링크
                link = item.select_one('.news-tit a') or item.select_one('h2 a')
                if not link:
                    continue
                
                headline = link.get_text(strip=True)
                href_raw = link.get('href', '')
                href = str(href_raw) if href_raw else ''
                
                if not headline or len(headline) < 5:
                    continue
                
                # URL 완성
                if href.startswith('http'):
                    url = href
                else:
                    url = urljoin(self.BASE_URL, href)
                
                # 추가 정보
                time_tag = item.select_one('.date') or item.select_one('time')
                published_time = time_tag.get_text(strip=True) if time_tag else ""
                
                summary_tag = item.select_one('.summary') or item.select_one('p')
                summary = summary_tag.get_text(strip=True) if summary_tag else ""
                
                news_items.append({
                    'headline': headline,
                    'url': url,
                    'press': "한국경제",
                    'published_time': published_time,
                    'summary': summary,
                    'source': self.name,
                    'crawled_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error parsing item: {e}")
                continue
        
        return news_items