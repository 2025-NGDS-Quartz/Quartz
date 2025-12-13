import axios from 'axios';
import type {
  Portfolio,
  CandidatesResponse,
  TechnicalAnalysisResult,
  TokenStatus,
  AgentHealth,
  MacroAnalysis,
} from '../types';

// API 베이스 URL (프록시 서버 경유)
const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 에이전트 정보
export const AGENTS = [
  { name: '인증관리', port: 8006, serviceName: 'auth-agent' },
  { name: '거시경제분석', port: 8001, serviceName: 'macro-agent' },
  { name: '거래종목선택', port: 8002, serviceName: 'ticker-selector' },
  { name: '기술분석', port: 8003, serviceName: 'technical-agent' },
  { name: '포트폴리오관리', port: 8004, serviceName: 'portfolio-manager' },
  { name: '거래', port: 8005, serviceName: 'trading-agent' },
];

// 에이전트 헬스체크
export const checkAgentHealth = async (): Promise<AgentHealth[]> => {
  const response = await api.get<AgentHealth[]>('/health/agents');
  return response.data;
};

// 포트폴리오 조회
export const getPortfolio = async (): Promise<Portfolio> => {
  const response = await api.get<Portfolio>('/portfolio');
  return response.data;
};

// 종목 후보 조회
export const getCandidates = async (topN: number = 5): Promise<CandidatesResponse> => {
  const response = await api.post<CandidatesResponse>('/candidates', { top_n: topN });
  return response.data;
};

// 기술적 분석 조회
export const getTechnicalAnalysis = async (ticker: string): Promise<TechnicalAnalysisResult> => {
  const response = await api.post<TechnicalAnalysisResult>('/technical-analysis', { ticker });
  return response.data;
};

// 토큰 상태 조회
export const getTokenStatus = async (): Promise<TokenStatus> => {
  const response = await api.get<TokenStatus>('/token-status');
  return response.data;
};

// 수동 매매 결정 트리거
export const triggerDecision = async (): Promise<{
  decision: Record<string, unknown>;
  execution_results: Record<string, unknown>[];
}> => {
  const response = await api.post('/decision');
  return response.data;
};

// 거시경제 분석 요약 조회 (포트폴리오 에이전트용)
export const getMacroSummary = async (): Promise<MacroAnalysis> => {
  const response = await api.get<MacroAnalysis>('/macro-summary');
  return response.data;
};

// 거시경제 분석 원본 조회 (프론트엔드용)
export const getMacroAnalysis = async (): Promise<MacroAnalysis> => {
  const response = await api.get<MacroAnalysis>('/macro-full');
  return response.data;
};

export default api;
