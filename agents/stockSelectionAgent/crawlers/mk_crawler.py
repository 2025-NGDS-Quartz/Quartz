# crawlers/mk_crawler.py

from .base_crawler import BaseCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from typing import List, Dict

class MKCrawler(BaseCrawler):
    """매일경제 뉴스 크롤러"""
    
    BASE_URL = "https://www.mk.co.kr"
    
    def __init__(self):
        super().__init__("MK")
    
    def get_news_list_url(self, page: int = 1) -> str:
        """매일경제 뉴스 리스트 URL"""
        return f"{self.BASE_URL}/news/economy/?page={page}"
    
    def parse_news_list(self, html: str) -> List[Dict]:
        """매일경제 HTML 파싱"""
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # 매일경제 구조 (실제 확인 필요)
        items = soup.select('.news_list li') or soup.select('.news_node')
        
        for item in items:
            try:
                link = item.select_one('a .news_ttl') or item.select_one('div h3')
                if not link:
                    continue
                
                headline = link.get_text(strip=True)
                href_raw = link.get('href', '')
                href = str(href_raw) if href_raw else ''
                
                if not headline or len(headline) < 5:
                    continue
                
                url = urljoin(self.BASE_URL, href)
                
                time_tag = item.select_one('.time')
                published_time = time_tag.get_text(strip=True) if time_tag else ""
                
                summary_tag = item.select_one('.news_desc')
                summary = summary_tag.get_text(strip=True) if summary_tag else ""
                
                news_items.append({
                    'headline': headline,
                    'url': url,
                    'press': "매일경제",
                    'published_time': published_time,
                    'summary': summary,
                    'source': self.name,
                    'crawled_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Error parsing item: {e}")
                continue
        
        return news_items