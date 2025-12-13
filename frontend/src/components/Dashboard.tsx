import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  TrendingUp,
  TrendingDown,
  Wallet,
  PieChart,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import {
  checkAgentHealth,
  getPortfolio,
  getCandidates,
  getTokenStatus,
  AGENTS,
} from '../api/client';
import type { AgentHealth, Portfolio, CandidatesResponse, TokenStatus } from '../types';

// 숫자 포맷팅 (한국 원화)
const formatKRW = (value: number) => {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
    maximumFractionDigits: 0,
  }).format(value);
};

// 퍼센트 포맷팅
const formatPercent = (value: number) => {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(2)}%`;
};

// 에이전트 상태 카드
function AgentStatusCard({ agents, isLoading }: { agents?: AgentHealth[]; isLoading: boolean }) {
  return (
    <div className="card">
      <div className="card-header">
        <Activity className="w-5 h-5 text-primary-600" />
        에이전트 상태
      </div>
      <div className="space-y-3">
        {AGENTS.map((agent) => {
          const health = agents?.find(a => a.serviceName === agent.serviceName);
          const isHealthy = health?.live && health?.ready;
          
          return (
            <div
              key={agent.serviceName}
              className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {isLoading ? (
                  <RefreshCw className="w-4 h-4 text-gray-400 animate-spin" />
                ) : isHealthy ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
                <span className="text-sm font-medium text-gray-700">{agent.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500">:{agent.port}</span>
                <span
                  className={`badge ${
                    isLoading
                      ? 'bg-gray-100 text-gray-600'
                      : isHealthy
                      ? 'badge-success'
                      : 'badge-danger'
                  }`}
                >
                  {isLoading ? '확인중' : isHealthy ? '정상' : '오류'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// 포트폴리오 요약 카드
function PortfolioSummaryCard({ portfolio, isLoading }: { portfolio?: Portfolio | null; isLoading: boolean }) {
  const totalProfit = portfolio?.positions.reduce((sum, pos) => {
    return sum + (pos.current_price - pos.avg_price) * pos.shares;
  }, 0) || 0;

  const totalProfitRate = portfolio && portfolio.total_value > 0
    ? totalProfit / (portfolio.total_value - totalProfit)
    : 0;

  return (
    <div className="card">
      <div className="card-header">
        <Wallet className="w-5 h-5 text-primary-600" />
        포트폴리오 요약
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
        </div>
      ) : portfolio ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="stat-label">총 평가금액</p>
              <p className="stat-value">{formatKRW(portfolio.total_value)}</p>
            </div>
            <div>
              <p className="stat-label">가용 현금</p>
              <p className="stat-value text-lg">{formatKRW(portfolio.cash_krw)}</p>
            </div>
          </div>
          
          <div className="pt-4 border-t border-gray-100">
            <div className="flex items-center justify-between">
              <span className="stat-label">총 손익</span>
              <div className="flex items-center gap-2">
                {totalProfit >= 0 ? (
                  <TrendingUp className="w-4 h-4 text-green-500" />
                ) : (
                  <TrendingDown className="w-4 h-4 text-red-500" />
                )}
                <span
                  className={`font-semibold ${
                    totalProfit >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {formatKRW(totalProfit)} ({formatPercent(totalProfitRate)})
                </span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-100">
            <p className="stat-label mb-2">보유종목</p>
            <div className="text-2xl font-bold text-gray-900">
              {portfolio.positions.length}개
            </div>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-32 text-gray-500">
          <AlertCircle className="w-5 h-5 mr-2" />
          데이터를 불러올 수 없습니다
        </div>
      )}
    </div>
  );
}

// 후보 종목 미리보기 카드
function CandidatesPreviewCard({ candidates, isLoading }: { candidates?: CandidatesResponse | null; isLoading: boolean }) {
  return (
    <div className="card">
      <div className="card-header">
        <PieChart className="w-5 h-5 text-primary-600" />
        후보 종목
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
        </div>
      ) : candidates && candidates.top_candidates.length > 0 ? (
        <div className="space-y-3">
          {candidates.top_candidates.slice(0, 5).map((candidate, index) => (
            <div
              key={candidate.ticker}
              className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 flex items-center justify-center bg-primary-100 text-primary-700 rounded-full text-xs font-bold">
                  {index + 1}
                </span>
                <div>
                  <p className="text-sm font-medium text-gray-900">{candidate.name}</p>
                  <p className="text-xs text-gray-500">{candidate.ticker}</p>
                </div>
              </div>
              <div className="text-right">
                <span
                  className={`badge ${
                    candidate.priority === 'HIGH'
                      ? 'badge-success'
                      : candidate.priority === 'MID'
                      ? 'badge-warning'
                      : 'badge-info'
                  }`}
                >
                  {candidate.priority}
                </span>
                <p className="text-xs text-gray-500 mt-1">
                  감성 {(candidate.avg_sentiment * 100).toFixed(0)}%
                </p>
              </div>
            </div>
          ))}
          
          <div className="pt-2 text-center">
            <span className="text-xs text-gray-500">
              총 {candidates.total_stocks}개 종목 중 상위 {candidates.top_candidates.length}개
            </span>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center h-32 text-gray-500">
          <AlertCircle className="w-5 h-5 mr-2" />
          후보 종목 데이터 없음
        </div>
      )}
    </div>
  );
}

// 토큰 상태 카드
function TokenStatusCard({ tokenStatus, isLoading }: { tokenStatus?: TokenStatus | null; isLoading: boolean }) {
  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}시간 ${minutes}분`;
  };

  return (
    <div className="card">
      <div className="card-header">
        <Activity className="w-5 h-5 text-primary-600" />
        인증 토큰 상태
      </div>
      
      {isLoading ? (
        <div className="flex items-center justify-center h-20">
          <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
        </div>
      ) : tokenStatus ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="stat-label">상태</span>
            <span
              className={`badge ${
                tokenStatus.is_valid ? 'badge-success' : 'badge-danger'
              }`}
            >
              {tokenStatus.is_valid ? '유효' : '만료'}
            </span>
          </div>
          {tokenStatus.remaining_seconds > 0 && (
            <div className="flex items-center justify-between">
              <span className="stat-label">남은 시간</span>
              <span className="text-sm font-medium text-gray-700">
                {formatTime(tokenStatus.remaining_seconds)}
              </span>
            </div>
          )}
        </div>
      ) : (
        <div className="flex items-center justify-center h-20 text-gray-500">
          토큰 상태 확인 불가
        </div>
      )}
    </div>
  );
}

// 메인 대시보드 컴포넌트
export default function Dashboard() {
  // API 쿼리
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: checkAgentHealth,
    refetchInterval: 10000, // 10초마다 갱신
  });

  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    refetchInterval: 30000,
  });

  const { data: candidates, isLoading: candidatesLoading } = useQuery({
    queryKey: ['candidates'],
    queryFn: () => getCandidates(5),
    refetchInterval: 60000, // 1분마다 갱신
  });

  const { data: tokenStatus, isLoading: tokenLoading } = useQuery({
    queryKey: ['tokenStatus'],
    queryFn: getTokenStatus,
    refetchInterval: 60000,
  });

  return (
    <div className="space-y-6">
      {/* 상단 통계 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-label">총 평가금액</p>
              <p className="stat-value">
                {portfolio ? formatKRW(portfolio.total_value) : '-'}
              </p>
            </div>
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <Wallet className="w-6 h-6 text-primary-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-label">가용 현금</p>
              <p className="stat-value">
                {portfolio ? formatKRW(portfolio.cash_krw) : '-'}
              </p>
            </div>
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-label">보유 종목 수</p>
              <p className="stat-value">
                {portfolio ? `${portfolio.positions.length}개` : '-'}
              </p>
            </div>
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <PieChart className="w-6 h-6 text-purple-600" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="stat-label">활성 에이전트</p>
              <p className="stat-value">
                {agents
                  ? `${agents.filter(a => a.live && a.ready).length}/${AGENTS.length}`
                  : '-'}
              </p>
            </div>
            <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* 메인 콘텐츠 그리드 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 에이전트 상태 */}
        <AgentStatusCard agents={agents} isLoading={agentsLoading} />

        {/* 포트폴리오 요약 */}
        <PortfolioSummaryCard portfolio={portfolio} isLoading={portfolioLoading} />

        {/* 후보 종목 미리보기 */}
        <CandidatesPreviewCard candidates={candidates} isLoading={candidatesLoading} />
      </div>

      {/* 토큰 상태 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <TokenStatusCard tokenStatus={tokenStatus} isLoading={tokenLoading} />
      </div>
    </div>
  );
}
