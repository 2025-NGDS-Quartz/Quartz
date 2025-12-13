// 에이전트 헬스체크 응답
export interface HealthStatus {
  status: string;
  healthy: boolean;
}

export interface AgentHealth {
  name: string;
  port: number;
  serviceName: string;
  live: boolean;
  ready: boolean;
  lastCheck: string;
}

// 포트폴리오 관련
export interface Position {
  ticker: string;
  name: string;
  shares: number;
  avg_price: number;
  current_price: number;
  eval_amount: number;
  profit_loss_rate: number;
  weight_in_portfolio: number;
}

export interface Portfolio {
  cash_krw: number;
  total_value: number;
  positions: Position[];
  last_updated: string;
}

// 종목 후보
export interface StockCandidate {
  ticker: string;
  name: string;
  sector: string;
  avg_sentiment: number;
  news_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  positive_ratio: number;
  negative_ratio: number;
  neutral_ratio: number;
  priority: 'HIGH' | 'MID' | 'LOW';
  market_cap_tier: 'LARGE' | 'MID' | 'SMALL';
  reasoning: string;
  top_headlines: string[];
  final_score: number;
}

export interface CandidatesResponse {
  timestamp: string;
  total_stocks: number;
  statistics: {
    high_priority: number;
    mid_priority: number;
    low_priority: number;
  };
  top_candidates: StockCandidate[];
}

// 기술적 분석
export interface MAData {
  ma5: number;
  ma10: number;
  ma20: number;
}

export interface MACDData {
  macd_line: number;
  signal_line: number;
  histogram: number;
  signal: 'bullish' | 'bearish' | 'neutral';
}

export interface BollingerBandData {
  top: number;
  middle: number;
  bottom: number;
}

export interface FibonacciData {
  trend: 'up' | 'down' | 'sideway';
  levels: Record<string, number>;
}

export interface PeriodAnalysis {
  rsi: number;
  ma: MAData;
  macd: MACDData;
  bollinger_band: BollingerBandData;
  fibonacci_retracement: FibonacciData;
}

export interface TechnicalAnalysisResult {
  ticker: string;
  current_price: number;
  analysis_time: string;
  day: PeriodAnalysis;
  week: PeriodAnalysis;
  month: PeriodAnalysis;
}

// 토큰 상태
export interface TokenStatus {
  is_valid: boolean;
  expires_at: string | null;
  remaining_seconds: number;
}

// 대시보드 전체 데이터
export interface DashboardData {
  agents: AgentHealth[];
  portfolio: Portfolio | null;
  candidates: CandidatesResponse | null;
  tokenStatus: TokenStatus | null;
}
