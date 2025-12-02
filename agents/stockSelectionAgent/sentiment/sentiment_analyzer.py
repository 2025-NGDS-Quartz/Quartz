# sentiment_analyzer.py

import os
import json
import logging
import hashlib
from typing import List, Dict, Optional
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
import time

# .env 파일 로드
load_dotenv()

class SentimentAnalyzer:
    """GPT 기반 뉴스 감성 분석"""
    
    def __init__(self, batch_size: int = 20):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.batch_size = batch_size
        self.cache_file = Path("data/sentiment_cache.json")
        self.cache = self._load_cache()
        self.logger = logging.getLogger(__name__)
        
        # 통계
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'total_analyzed': 0
        }
    
    def _load_cache(self) -> Dict:
        """캐시 로드"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """캐시 저장"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _get_cache_key(self, headline: str) -> str:
        """헤드라인의 해시 키 생성"""
        return hashlib.md5(headline.encode()).hexdigest()
    
    def _create_prompt(self, headlines: List[str]) -> str:
        """배치 분석용 프롬프트 생성"""
        headlines_json = json.dumps(headlines, ensure_ascii=False)
        
        prompt = f"""다음 뉴스 헤드라인들에 대해 감성 분석을 수행하세요.

헤드라인 목록:
{headlines_json}

각 헤드라인에 대해 다음 정보를 JSON 배열로 반환하세요:

1. sentiment: "positive" (긍정), "negative" (부정), "neutral" (중립)
2. score: 0.0~1.0 사이 점수 (0=매우 부정, 0.5=중립, 1.0=매우 긍정)
3. confidence: 0.0~1.0 사이 신뢰도
4. reasoning: 간단한 분석 이유 (20자 이내)

분석 기준:
- 실적 호조, 수익 증가, 성장 등 → 긍정
- 실적 부진, 손실, 하락 등 → 부정
- 단순 사실 전달, 중립적 표현 → 중립

반드시 다음 형식의 JSON만 반환하세요 (다른 텍스트 포함 금지):
[
  {{
    "headline": "원본 헤드라인",
    "sentiment": "positive",
    "score": 0.75,
    "confidence": 0.85,
    "reasoning": "분석 이유"
  }},
  ...
]

**중요: JSON 배열만 반환하고, ```json이나 다른 마크다운 포맷을 사용하지 마세요.**"""
        
        return prompt
    
    def _parse_response(self, response_text: str) -> List[Dict]:
        """GPT 응답 파싱"""
        try:
            # 마크다운 코드 블록 제거
            text = response_text.strip()
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]
            text = text.strip()
            
            # JSON 파싱
            results = json.loads(text)
            return results
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}")
            self.logger.debug(f"원본 응답: {response_text}")
            return []
    
    def analyze_batch(self, headlines: List[str]) -> List[Dict]:
        """헤드라인 배치 분석"""
        if not headlines:
            return []
        
        self.logger.info(f"📊 Analyzing batch of {len(headlines)} headlines...")
        
        # 프롬프트 생성
        prompt = self._create_prompt(headlines)
        
        # API 호출
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 비용 효율적인 모델
                messages=[
                    {"role": "system", "content": "당신은 금융 뉴스 감성 분석 전문가입니다. JSON 형식으로만 응답하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # 일관성을 위해 낮은 온도
                max_tokens=2000
            )
            
            self.stats['api_calls'] += 1
            
            # 응답 파싱
            response_text = response.choices[0].message.content or ""
            
            if not response_text:
                self.logger.error("API 응답이 비어있습니다.")
                return []
            
            results = self._parse_response(response_text)
            
            self.logger.info(f"✅ Analyzed {len(results)} headlines")
            return results
            
        except Exception as e:
            self.logger.error(f"API 호출 실패: {e}")
            return []
    
    def analyze_headlines(self, headlines: List[str]) -> List[Dict]:
        """헤드라인 리스트 전체 분석 (캐싱 + 배치)"""
        results = []
        to_analyze = []
        cached_results = {}
        
        # 1. 캐시 확인
        for headline in headlines:
            cache_key = self._get_cache_key(headline)
            if cache_key in self.cache:
                cached_results[headline] = self.cache[cache_key]
                self.stats['cache_hits'] += 1
            else:
                to_analyze.append(headline)
        
        self.logger.info(f"💾 Cache: {len(cached_results)} hits, {len(to_analyze)} to analyze")
        
        # 2. 배치 분석
        batch_results = {}
        for i in range(0, len(to_analyze), self.batch_size):
            batch = to_analyze[i:i + self.batch_size]
            
            self.logger.info(f"🔄 Processing batch {i//self.batch_size + 1}/{(len(to_analyze)-1)//self.batch_size + 1}")
            
            batch_analysis = self.analyze_batch(batch)
            
            # 결과 매핑
            for item in batch_analysis:
                headline = item.get('headline', '')
                if headline in batch:
                    batch_results[headline] = item
                    
                    # 캐시에 저장
                    cache_key = self._get_cache_key(headline)
                    self.cache[cache_key] = item
            
            # API 호출 간 딜레이 (Rate limit 방지)
            if i + self.batch_size < len(to_analyze):
                time.sleep(1)
        
        # 3. 결과 병합 (원본 순서 유지)
        for headline in headlines:
            if headline in cached_results:
                results.append(cached_results[headline])
            elif headline in batch_results:
                results.append(batch_results[headline])
            else:
                # 분석 실패한 경우 기본값
                results.append({
                    'headline': headline,
                    'sentiment': 'neutral',
                    'score': 0.5,
                    'confidence': 0.0,
                    'reasoning': '분석 실패'
                })
        
        # 4. 캐시 저장
        self._save_cache()
        
        # 5. 통계 업데이트
        self.stats['total_analyzed'] = len(results)
        
        return results
    
    def get_statistics(self) -> Dict:
        """분석 통계"""
        total = self.stats['total_analyzed']
        cache_rate = (self.stats['cache_hits'] / total * 100) if total > 0 else 0
        
        return {
            'total_analyzed': total,
            'api_calls': self.stats['api_calls'],
            'cache_hits': self.stats['cache_hits'],
            'cache_rate': f"{cache_rate:.1f}%",
            'estimated_cost': f"${self.stats['api_calls'] * 0.01:.2f}"  # 대략적 추정
        }


# 테스트
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    analyzer = SentimentAnalyzer(batch_size=20)
    
    # 테스트 헤드라인
    test_headlines = [
        "삼성전자, 3분기 영업이익 10조원 돌파...시장 예상 상회",
        "SK하이닉스, 반도체 수출 급감으로 실적 악화 우려",
        "네이버, AI 챗봇 서비스 '하이퍼클로바X' 정식 출시",
        "현대차·기아, 미국 전기차 판매 호조 지속",
        "LG에너지솔루션, 북미 배터리 공장 가동률 저조",
        "카카오, 메신저 광고 매출 증가세",
        "셀트리온, 바이오시밀러 승인 지연으로 주가 하락",
        "POSCO, 철강 가격 상승으로 수익성 개선",
    ]
    
    # 분석
    print("\n🔍 감성 분석 시작...")
    print("=" * 60)
    
    results = analyzer.analyze_headlines(test_headlines)
    
    # 결과 출력
    print("\n📊 분석 결과:")
    print("=" * 60)
    for result in results:
        sentiment_emoji = {
            'positive': '😊',
            'negative': '😞',
            'neutral': '😐'
        }
        
        emoji = sentiment_emoji.get(result['sentiment'], '❓')
        print(f"\n{emoji} {result['sentiment'].upper()} (점수: {result['score']:.2f})")
        print(f"헤드라인: {result['headline']}")
        print(f"이유: {result['reasoning']}")
        print(f"신뢰도: {result['confidence']:.2f}")
    
    # 통계
    print("\n\n📈 통계:")
    print("=" * 60)
    stats = analyzer.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")