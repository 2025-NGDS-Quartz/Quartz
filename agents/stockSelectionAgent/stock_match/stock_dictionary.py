# stock_dictionary.py

from typing import Dict, List, Set
import json
from pathlib import Path

class StockDictionary:
    """한국 주식 종목 사전 (확장 버전)"""
    
    def __init__(self):
        self.ticker_to_name: Dict[str, str] = {}
        self.name_to_ticker: Dict[str, str] = {}
        self.keywords: Dict[str, List[str]] = {}
        self.sectors: Dict[str, str] = {}  # 종목별 섹터
        self.market_cap_tiers: Dict[str, str] = {}  # 시총 등급 (LARGE/MID/SMALL)
        self._load_stock_data()
    
    def _load_stock_data(self):
        """종목 데이터 로드 (100개 이상)"""
        # 시총 등급: LARGE (10조원 이상), MID (1조~10조원), SMALL (1조원 미만)
        stocks = {
            # ==================== 반도체/전자 ====================
            '005930': {
                'name': '삼성전자',
                'keywords': ['삼성전자', '삼성', 'Samsung', '삼성 전자'],
                'sector': '반도체/전자',
                'market_cap_tier': 'LARGE'
            },
            '000660': {
                'name': 'SK하이닉스',
                'keywords': ['SK하이닉스', 'SK하이닉', 'SKhynix', 'SK 하이닉스', 'sk하이닉스'],
                'sector': '반도체/전자',
                'market_cap_tier': 'LARGE'
            },
            '066570': {
                'name': 'LG전자',
                'keywords': ['LG전자', 'LG 전자', '엘지전자'],
                'sector': '반도체/전자',
                'market_cap_tier': 'LARGE'
            },
            '042700': {
                'name': '한미반도체',
                'keywords': ['한미반도체', '한미 반도체'],
                'sector': '반도체/전자',
                'market_cap_tier': 'MID'
            },
            '039030': {
                'name': '이오테크닉스',
                'keywords': ['이오테크닉스', '이오 테크닉스'],
                'sector': '반도체/전자',
                'market_cap_tier': 'MID'
            },
            '357780': {
                'name': '솔브레인',
                'keywords': ['솔브레인'],
                'sector': '반도체/전자',
                'market_cap_tier': 'MID'
            },
            '000990': {
                'name': 'DB하이텍',
                'keywords': ['DB하이텍', 'DB 하이텍'],
                'sector': '반도체/전자',
                'market_cap_tier': 'SMALL'
            },
            
            # ==================== 배터리/2차전지 ====================
            '373220': {
                'name': 'LG에너지솔루션',
                'keywords': ['LG에너지솔루션', 'LG에너지', 'LGES', 'LG 에너지', '엘지에너지'],
                'sector': '배터리',
                'market_cap_tier': 'LARGE'
            },
            '006400': {
                'name': '삼성SDI',
                'keywords': ['삼성SDI', '삼성 SDI', '삼성에스디아이'],
                'sector': '배터리',
                'market_cap_tier': 'LARGE'
            },
            '096770': {
                'name': 'SK이노베이션',
                'keywords': ['SK이노베이션', 'SK이노', 'SK 이노베이션'],
                'sector': '배터리',
                'market_cap_tier': 'LARGE'
            },
            '247540': {
                'name': '에코프로비엠',
                'keywords': ['에코프로비엠', '에코프로 비엠', '에코프로BM'],
                'sector': '배터리',
                'market_cap_tier': 'MID'
            },
            '086520': {
                'name': '에코프로',
                'keywords': ['에코프로'],
                'sector': '배터리',
                'market_cap_tier': 'MID'
            },
            '361610': {
                'name': 'SK아이이테크놀로지',
                'keywords': ['SK아이이테크놀로지', 'SKiet', 'SK 아이이'],
                'sector': '배터리',
                'market_cap_tier': 'MID'
            },
            '137400': {
                'name': '피엔티',
                'keywords': ['피엔티', 'PNT'],
                'sector': '배터리',
                'market_cap_tier': 'SMALL'
            },
            '348370': {
                'name': '알테오젠',
                'keywords': ['알테오젠'],
                'sector': '배터리',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 자동차/부품 ====================
            '005380': {
                'name': '현대차',
                'keywords': ['현대차', '현대자동차', '현대 자동차', '현대 차'],
                'sector': '자동차',
                'market_cap_tier': 'LARGE'
            },
            '000270': {
                'name': '기아',
                'keywords': ['기아', '기아차', 'KIA', '기아자동차'],
                'sector': '자동차',
                'market_cap_tier': 'LARGE'
            },
            '012330': {
                'name': '현대모비스',
                'keywords': ['현대모비스', '모비스', '현대 모비스'],
                'sector': '자동차부품',
                'market_cap_tier': 'LARGE'
            },
            '012450': {
                'name': '한화에어로스페이스',
                'keywords': ['한화에어로스페이스', '한화 에어로스페이스', '한화에어로'],
                'sector': '자동차부품',
                'market_cap_tier': 'LARGE'
            },
            '011210': {
                'name': '현대위아',
                'keywords': ['현대위아', '현대 위아'],
                'sector': '자동차부품',
                'market_cap_tier': 'MID'
            },
            '010950': {
                'name': 'S-Oil',
                'keywords': ['S-Oil', '에스오일', 'S오일'],
                'sector': '자동차',
                'market_cap_tier': 'LARGE'
            },
            '009830': {
                'name': '한화솔루션',
                'keywords': ['한화솔루션', '한화 솔루션'],
                'sector': '자동차',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 화학/제약/바이오 ====================
            '051910': {
                'name': 'LG화학',
                'keywords': ['LG화학', 'LG 화학', '엘지화학'],
                'sector': '화학',
                'market_cap_tier': 'LARGE'
            },
            '068270': {
                'name': '셀트리온',
                'keywords': ['셀트리온'],
                'sector': '바이오',
                'market_cap_tier': 'LARGE'
            },
            '207940': {
                'name': '삼성바이오로직스',
                'keywords': ['삼성바이오로직스', '삼성바이오', '삼성 바이오'],
                'sector': '바이오',
                'market_cap_tier': 'LARGE'
            },
            '091990': {
                'name': '셀트리온헬스케어',
                'keywords': ['셀트리온헬스케어', '셀트리온 헬스케어'],
                'sector': '바이오',
                'market_cap_tier': 'MID'
            },
            '068760': {
                'name': '셀트리온제약',
                'keywords': ['셀트리온제약', '셀트리온 제약'],
                'sector': '제약',
                'market_cap_tier': 'MID'
            },
            '326030': {
                'name': 'SK바이오팜',
                'keywords': ['SK바이오팜', 'SK 바이오팜'],
                'sector': '제약',
                'market_cap_tier': 'MID'
            },
            '028300': {
                'name': 'HLB',
                'keywords': ['HLB', '에이치엘비'],
                'sector': '바이오',
                'market_cap_tier': 'MID'
            },
            '196170': {
                'name': '알테오젠',
                'keywords': ['알테오젠'],
                'sector': '바이오',
                'market_cap_tier': 'LARGE'
            },
            '302440': {
                'name': 'SK바이오사이언스',
                'keywords': ['SK바이오사이언스', 'SK 바이오사이언스'],
                'sector': '바이오',
                'market_cap_tier': 'MID'
            },
            '185750': {
                'name': '종근당',
                'keywords': ['종근당'],
                'sector': '제약',
                'market_cap_tier': 'MID'
            },
            
            # ==================== IT/인터넷/게임 ====================
            '035420': {
                'name': 'NAVER',
                'keywords': ['네이버', 'NAVER', 'Naver', '네이버웹툰', '네이버 웹툰'],
                'sector': 'IT/인터넷',
                'market_cap_tier': 'LARGE'
            },
            '035720': {
                'name': '카카오',
                'keywords': ['카카오', 'Kakao', '카카오톡'],
                'sector': 'IT/인터넷',
                'market_cap_tier': 'LARGE'
            },
            '259960': {
                'name': '크래프톤',
                'keywords': ['크래프톤', 'KRAFTON', '배틀그라운드', '배그'],
                'sector': '게임',
                'market_cap_tier': 'LARGE'
            },
            '251270': {
                'name': '넷마블',
                'keywords': ['넷마블', 'Netmarble'],
                'sector': '게임',
                'market_cap_tier': 'MID'
            },
            '036570': {
                'name': '엔씨소프트',
                'keywords': ['엔씨소프트', 'NC소프트', 'NCSoft', '엔씨'],
                'sector': '게임',
                'market_cap_tier': 'MID'
            },
            '352820': {
                'name': '하이브',
                'keywords': ['하이브', 'HYBE', 'BTS', '방탄소년단'],
                'sector': '엔터테인먼트',
                'market_cap_tier': 'LARGE'
            },
            '041510': {
                'name': 'SM',
                'keywords': ['SM', '에스엠', 'SM엔터테인먼트'],
                'sector': '엔터테인먼트',
                'market_cap_tier': 'MID'
            },
            '122870': {
                'name': 'YG',
                'keywords': ['YG', '와이지', 'YG엔터테인먼트'],
                'sector': '엔터테인먼트',
                'market_cap_tier': 'SMALL'
            },
            '035900': {
                'name': 'JYP Ent.',
                'keywords': ['JYP', '제이와이피', 'JYP엔터테인먼트'],
                'sector': '엔터테인먼트',
                'market_cap_tier': 'MID'
            },
            '293490': {
                'name': '카카오게임즈',
                'keywords': ['카카오게임즈', '카카오 게임즈'],
                'sector': '게임',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 금융 ====================
            '105560': {
                'name': 'KB금융',
                'keywords': ['KB금융', 'KB', 'KB국민은행', 'KB금융지주'],
                'sector': '금융',
                'market_cap_tier': 'LARGE'
            },
            '055550': {
                'name': '신한지주',
                'keywords': ['신한지주', '신한은행', '신한', '신한금융지주'],
                'sector': '금융',
                'market_cap_tier': 'LARGE'
            },
            '086790': {
                'name': '하나금융지주',
                'keywords': ['하나금융지주', '하나은행', '하나금융', '하나'],
                'sector': '금융',
                'market_cap_tier': 'LARGE'
            },
            '316140': {
                'name': '우리금융지주',
                'keywords': ['우리금융지주', '우리은행', '우리금융', '우리'],
                'sector': '금융',
                'market_cap_tier': 'LARGE'
            },
            '032830': {
                'name': '삼성생명',
                'keywords': ['삼성생명', '삼성 생명'],
                'sector': '금융',
                'market_cap_tier': 'LARGE'
            },
            '000810': {
                'name': '삼성화재',
                'keywords': ['삼성화재', '삼성 화재'],
                'sector': '금융',
                'market_cap_tier': 'LARGE'
            },
            '138930': {
                'name': 'BNK금융지주',
                'keywords': ['BNK금융지주', 'BNK', '부산은행'],
                'sector': '금융',
                'market_cap_tier': 'MID'
            },
            '024110': {
                'name': '기업은행',
                'keywords': ['기업은행', 'IBK'],
                'sector': '금융',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 통신 ====================
            '017670': {
                'name': 'SK텔레콤',
                'keywords': ['SK텔레콤', 'SKT', 'SK 텔레콤', 'sk텔레콤'],
                'sector': '통신',
                'market_cap_tier': 'LARGE'
            },
            '030200': {
                'name': 'KT',
                'keywords': ['KT', '케이티'],
                'sector': '통신',
                'market_cap_tier': 'LARGE'
            },
            '032640': {
                'name': 'LG유플러스',
                'keywords': ['LG유플러스', 'LG 유플러스', 'LG유플', '엘지유플러스'],
                'sector': '통신',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 유통/서비스 ====================
            '139480': {
                'name': '이마트',
                'keywords': ['이마트', 'E마트', '신세계이마트'],
                'sector': '유통',
                'market_cap_tier': 'MID'
            },
            '282330': {
                'name': 'BGF리테일',
                'keywords': ['BGF리테일', 'BGF', 'CU', '씨유'],
                'sector': '유통',
                'market_cap_tier': 'MID'
            },
            '007070': {
                'name': 'GS리테일',
                'keywords': ['GS리테일', 'GS25', 'GS 리테일'],
                'sector': '유통',
                'market_cap_tier': 'MID'
            },
            '069960': {
                'name': '현대백화점',
                'keywords': ['현대백화점', '현대 백화점'],
                'sector': '유통',
                'market_cap_tier': 'MID'
            },
            '004370': {
                'name': '농심',
                'keywords': ['농심', '신라면'],
                'sector': '식품',
                'market_cap_tier': 'MID'
            },
            '097950': {
                'name': 'CJ제일제당',
                'keywords': ['CJ제일제당', 'CJ', '씨제이'],
                'sector': '식품',
                'market_cap_tier': 'MID'
            },
            '004990': {
                'name': '롯데칠성',
                'keywords': ['롯데칠성', '롯데 칠성'],
                'sector': '식품',
                'market_cap_tier': 'MID'
            },
            '271560': {
                'name': '오리온',
                'keywords': ['오리온', '초코파이'],
                'sector': '식품',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 건설/조선/중공업 ====================
            '028260': {
                'name': '삼성물산',
                'keywords': ['삼성물산', '삼성 물산'],
                'sector': '건설',
                'market_cap_tier': 'LARGE'
            },
            '000720': {
                'name': '현대건설',
                'keywords': ['현대건설', '현대 건설'],
                'sector': '건설',
                'market_cap_tier': 'MID'
            },
            '047810': {
                'name': '한국항공우주',
                'keywords': ['한국항공우주', 'KAI', '한국 항공우주'],
                'sector': '항공우주',
                'market_cap_tier': 'LARGE'
            },
            '009540': {
                'name': '한국조선해양',
                'keywords': ['한국조선해양', '한국 조선해양', '현대중공업'],
                'sector': '조선',
                'market_cap_tier': 'LARGE'
            },
            '010140': {
                'name': '삼성중공업',
                'keywords': ['삼성중공업', '삼성 중공업'],
                'sector': '조선',
                'market_cap_tier': 'MID'
            },
            '042660': {
                'name': '한화오션',
                'keywords': ['한화오션', '한화 오션', '대우조선해양'],
                'sector': '조선',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 철강/소재 ====================
            '005490': {
                'name': 'POSCO홀딩스',
                'keywords': ['POSCO홀딩스', 'POSCO', '포스코', '포스코홀딩스'],
                'sector': '철강',
                'market_cap_tier': 'LARGE'
            },
            '003670': {
                'name': '포스코퓨처엠',
                'keywords': ['포스코퓨처엠', 'POSCO퓨처엠', '포스코 퓨처엠'],
                'sector': '소재',
                'market_cap_tier': 'LARGE'
            },
            '267250': {
                'name': '현대중공업지주',
                'keywords': ['현대중공업지주', '현대중공업', '현대 중공업'],
                'sector': '중공업',
                'market_cap_tier': 'LARGE'
            },
            
            # ==================== SK 계열 ====================
            '034730': {
                'name': 'SK',
                'keywords': ['SK', '에스케이'],
                'sector': 'SK계열',
                'market_cap_tier': 'LARGE'
            },
            '018260': {
                'name': 'SK에너지',
                'keywords': ['SK에너지', 'SK 에너지'],
                'sector': 'SK계열',
                'market_cap_tier': 'MID'
            },
            '018670': {
                'name': 'SK가스',
                'keywords': ['SK가스', 'SK 가스'],
                'sector': 'SK계열',
                'market_cap_tier': 'MID'
            },
            '011790': {
                'name': 'SK증권',
                'keywords': ['SK증권', 'SK 증권'],
                'sector': '금융',
                'market_cap_tier': 'SMALL'
            },
            
            # ==================== LG 계열 ====================
            '003550': {
                'name': 'LG',
                'keywords': ['LG', '엘지', 'LG그룹'],
                'sector': 'LG계열',
                'market_cap_tier': 'LARGE'
            },
            '004020': {
                'name': '현대제철',
                'keywords': ['현대제철', '현대 제철'],
                'sector': '철강',
                'market_cap_tier': 'MID'
            },
            '011070': {
                'name': 'LG이노텍',
                'keywords': ['LG이노텍', 'LG 이노텍'],
                'sector': '전자부품',
                'market_cap_tier': 'LARGE'
            },
            '034220': {
                'name': 'LG디스플레이',
                'keywords': ['LG디스플레이', 'LG 디스플레이', 'LGD'],
                'sector': '디스플레이',
                'market_cap_tier': 'MID'
            },
            
            # ==================== 기타 주요 종목 ====================
            '009150': {
                'name': '삼성전기',
                'keywords': ['삼성전기', '삼성 전기'],
                'sector': '전자부품',
                'market_cap_tier': 'LARGE'
            },
            '010130': {
                'name': '고려아연',
                'keywords': ['고려아연', '고려 아연'],
                'sector': '금속',
                'market_cap_tier': 'LARGE'
            },
            '006800': {
                'name': '미래에셋증권',
                'keywords': ['미래에셋증권', '미래에셋', '미래에셋 증권'],
                'sector': '금융',
                'market_cap_tier': 'MID'
            },
            '003490': {
                'name': '대한항공',
                'keywords': ['대한항공', '대한 항공', 'KAL'],
                'sector': '항공',
                'market_cap_tier': 'LARGE'
            },
            '020560': {
                'name': '아시아나항공',
                'keywords': ['아시아나항공', '아시아나', '아시아나 항공'],
                'sector': '항공',
                'market_cap_tier': 'MID'
            },
            '064350': {
                'name': '현대로템',
                'keywords': ['현대로템', '현대 로템'],
                'sector': '운송장비',
                'market_cap_tier': 'MID'
            },
            '145720': {
                'name': '덴티움',
                'keywords': ['덴티움'],
                'sector': '의료기기',
                'market_cap_tier': 'MID'
            },
            '214150': {
                'name': '클래시스',
                'keywords': ['클래시스'],
                'sector': '의료기기',
                'market_cap_tier': 'MID'
            },
        }
        
        # 데이터 로드
        for ticker, info in stocks.items():
            self.ticker_to_name[ticker] = info['name']
            self.name_to_ticker[info['name']] = ticker
            self.keywords[ticker] = info['keywords']
            self.sectors[ticker] = info.get('sector', 'Unknown')
            self.market_cap_tiers[ticker] = info.get('market_cap_tier', 'SMALL')
    
    def find_tickers(self, text: str) -> List[str]:
        """텍스트에서 종목 티커 찾기"""
        found_tickers = set()
        
        # 키워드 매칭
        for ticker, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in text:
                    found_tickers.add(ticker)
                    break
        
        return list(found_tickers)
    
    def get_name(self, ticker: str) -> str:
        """티커로 종목명 조회"""
        return self.ticker_to_name.get(ticker, "Unknown")
    
    def get_ticker(self, name: str) -> str:
        """종목명으로 티커 조회"""
        return self.name_to_ticker.get(name, "")
    
    def get_sector(self, ticker: str) -> str:
        """티커로 섹터 조회"""
        return self.sectors.get(ticker, "Unknown")
    
    def get_market_cap_tier(self, ticker: str) -> str:
        """티커로 시총 등급 조회 (LARGE/MID/SMALL)"""
        return self.market_cap_tiers.get(ticker, "SMALL")
    
    def get_market_cap_weight(self, ticker: str) -> float:
        """시총 등급에 따른 가중치 반환 (LARGE=1.0, MID=0.6, SMALL=0.3)"""
        tier = self.get_market_cap_tier(ticker)
        weights = {'LARGE': 1.0, 'MID': 0.6, 'SMALL': 0.3}
        return weights.get(tier, 0.3)
    
    def get_tickers_by_sector(self, sector: str) -> List[str]:
        """섹터별 종목 리스트"""
        return [
            ticker for ticker, sec in self.sectors.items() 
            if sec == sector
        ]
    
    def get_all_sectors(self) -> List[str]:
        """모든 섹터 리스트"""
        return list(set(self.sectors.values()))
    
    def get_statistics(self) -> Dict:
        """통계 정보"""
        # 시총 등급별 개수
        market_cap_counts = {'LARGE': 0, 'MID': 0, 'SMALL': 0}
        for tier in self.market_cap_tiers.values():
            market_cap_counts[tier] = market_cap_counts.get(tier, 0) + 1
        
        return {
            'total_stocks': len(self.ticker_to_name),
            'total_sectors': len(set(self.sectors.values())),
            'sectors': {
                sector: len(self.get_tickers_by_sector(sector))
                for sector in self.get_all_sectors()
            },
            'market_cap_tiers': market_cap_counts
        }
    
    def save_to_file(self, filepath: str = "data/stock_dictionary.json"):
        """사전을 파일로 저장"""
        data = {
            'ticker_to_name': self.ticker_to_name,
            'keywords': self.keywords,
            'sectors': self.sectors,
            'market_cap_tiers': self.market_cap_tiers
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Saved to {filepath}")
    
    def load_from_file(self, filepath: str = "data/stock_dictionary.json"):
        """파일에서 사전 로드"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.ticker_to_name = data['ticker_to_name']
        self.keywords = data['keywords']
        self.sectors = data.get('sectors', {})
        self.market_cap_tiers = data.get('market_cap_tiers', {})
        
        # name_to_ticker 재생성
        self.name_to_ticker = {
            name: ticker for ticker, name in self.ticker_to_name.items()
        }
        
        print(f"✅ Loaded from {filepath}")


# 테스트 및 통계
if __name__ == "__main__":
    dictionary = StockDictionary()
    
    # 통계 출력
    stats = dictionary.get_statistics()
    print("\n📊 종목 사전 통계")
    print("=" * 50)
    print(f"총 종목 수: {stats['total_stocks']}개")
    print(f"총 섹터 수: {stats['total_sectors']}개")
    print("\n섹터별 종목 수:")
    for sector, count in sorted(stats['sectors'].items(), key=lambda x: -x[1]):
        print(f"  {sector}: {count}개")
    
    # 테스트 헤드라인
    print("\n\n🧪 테스트")
    print("=" * 50)
    headlines = [
        "삼성전자·SK하이닉스, 반도체 수출 증가",
        "네이버·카카오, AI 챗봇 경쟁 가속화",
        "현대차·기아, 전기차 판매 호조",
        "셀트리온, 바이오시밀러 미국 시장 진출",
        "POSCO, 2차전지 소재 사업 확대",
        "KB금융·신한지주, 디지털 금융 투자 확대",
        "LG에너지솔루션, 북미 공장 증설",
        "하이브, BTS 컴백 앨범 발표"
    ]
    
    for headline in headlines:
        tickers = dictionary.find_tickers(headline)
        print(f"\n헤드라인: {headline}")
        print(f"관련 종목 ({len(tickers)}개):")
        for ticker in tickers:
            name = dictionary.get_name(ticker)
            sector = dictionary.get_sector(ticker)
            print(f"  - {ticker}: {name} ({sector})")
    
    # 파일로 저장
    print("\n\n💾 저장 중...")
    dictionary.save_to_file()
    print("✅ 완료!")