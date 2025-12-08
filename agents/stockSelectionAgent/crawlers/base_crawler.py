from abc import ABC, abstractmethod  # ✅ 추가
from bs4 import BeautifulSoup
import requests
import logging
import random
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin
from datetime import datetime


class BaseCrawler(ABC):
    """모든 뉴스 크롤러의 베이스 클래스"""
    
    def __init__(self, name: str):
        self.name = name
        self.session = self._create_session()
        self.crawled_urls = set()
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    def _create_session(self) -> requests.Session:
        """HTTP 세션 생성"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        return session
    
    def _get_random_user_agent(self) -> str:
        """랜덤 User-Agent 반환"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
        return random.choice(user_agents)
    
    def _request_with_retry(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """재시도 로직이 포함된 HTTP 요청"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                wait_time = 2 * (2 ** attempt)
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to fetch {url}")
                    return None
        return None
    
    @abstractmethod
    def get_news_list_url(self, page: int = 1) -> str:
        """뉴스 리스트 페이지 URL 반환 (반드시 구현해야 함)"""
        pass
    
    @abstractmethod
    def parse_news_list(self, html: str) -> List[Dict]:
        """HTML에서 뉴스 리스트 파싱 (반드시 구현해야 함)"""
        pass
    
    def crawl_page(self, page: int = 1) -> List[Dict]:
        """한 페이지 크롤링"""
        url = self.get_news_list_url(page)
        self.logger.info(f"Crawling {self.name} page {page}: {url}")
        
        response = self._request_with_retry(url)
        if not response:
            return []
        
        news_items = self.parse_news_list(response.text)
        
        # 중복 제거
        unique_items = []
        for item in news_items:
            if item['url'] not in self.crawled_urls:
                unique_items.append(item)
                self.crawled_urls.add(item['url'])
        
        self.logger.info(f"Parsed {len(unique_items)} unique news items from {self.name}")
        return unique_items
    
    def crawl_multiple_pages(self, max_pages: int = 3, delay: tuple = (1, 3)) -> List[Dict]:
        """여러 페이지 크롤링"""
        all_news = []
        
        for page in range(1, max_pages + 1):
            news = self.crawl_page(page)
            all_news.extend(news)
            
            if page < max_pages:
                wait_time = random.uniform(*delay)
                self.logger.info(f"Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
        
        return all_news