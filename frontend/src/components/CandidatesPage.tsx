import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  TrendingUp,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  Newspaper,
  ThumbsUp,
  ThumbsDown,
  Minus,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { getCandidates } from '../api/client';

export default function CandidatesPage() {
  const { data: candidates, isLoading, error, refetch } = useQuery({
    queryKey: ['candidates', 10],
    queryFn: () => getCandidates(10),
    refetchInterval: 60000,
  });

  // 감성 점수 차트 데이터
  const chartData =
    candidates?.top_candidates.map((c) => ({
      name: c.name.length > 6 ? c.name.substring(0, 6) + '...' : c.name,
      score: c.avg_sentiment * 100,
      ticker: c.ticker,
    })) || [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <AlertCircle className="w-12 h-12 mb-4" />
          <p className="text-lg font-medium">후보 종목 데이터를 불러올 수 없습니다</p>
          <button onClick={() => refetch()} className="mt-4 btn btn-primary">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (!candidates || candidates.top_candidates.length === 0) {
    return (
      <div className="card">
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <Newspaper className="w-12 h-12 mb-4" />
          <p className="text-lg font-medium">분석된 후보 종목이 없습니다</p>
          <p className="text-sm mt-2">
            뉴스 크롤링 파이프라인이 실행되면 후보 종목이 표시됩니다
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 통계 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <p className="stat-label">분석 종목 수</p>
          <p className="stat-value">{candidates.total_stocks}개</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full" />
            <p className="stat-label">HIGH 우선순위</p>
          </div>
          <p className="stat-value text-green-600">
            {candidates.statistics.high_priority}개
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded-full" />
            <p className="stat-label">MID 우선순위</p>
          </div>
          <p className="stat-value text-yellow-600">
            {candidates.statistics.mid_priority}개
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full" />
            <p className="stat-label">LOW 우선순위</p>
          </div>
          <p className="stat-value text-blue-600">
            {candidates.statistics.low_priority}개
          </p>
        </div>
      </div>

      {/* 감성 점수 차트 */}
      <div className="card">
        <h3 className="card-header">
          <TrendingUp className="w-5 h-5 text-primary-600" />
          종목별 감성 점수
        </h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} unit="%" />
              <YAxis type="category" dataKey="name" width={80} />
              <Tooltip
                formatter={(value: number) => [`${value.toFixed(1)}%`, '감성 점수']}
              />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={
                      entry.score >= 70
                        ? '#10b981'
                        : entry.score >= 50
                        ? '#f59e0b'
                        : '#ef4444'
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 후보 종목 리스트 */}
      <div className="card">
        <h3 className="card-header">
          <Newspaper className="w-5 h-5 text-primary-600" />
          후보 종목 상세
        </h3>
        <div className="space-y-4">
          {candidates.top_candidates.map((candidate, index) => (
            <div
              key={candidate.ticker}
              className="border border-gray-200 rounded-xl p-5 hover:border-primary-300 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-4">
                  <span className="w-8 h-8 flex items-center justify-center bg-primary-100 text-primary-700 rounded-full text-sm font-bold">
                    {index + 1}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-gray-900">
                        {candidate.name}
                      </h4>
                      <Link
                        to={`/technical/${candidate.ticker}`}
                        className="text-primary-600 hover:text-primary-700"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm text-gray-500">
                        {candidate.ticker}
                      </span>
                      <span className="text-sm text-gray-400">|</span>
                      <span className="text-sm text-gray-500">
                        {candidate.sector}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`badge ${
                      candidate.market_cap_tier === 'LARGE'
                        ? 'bg-purple-100 text-purple-800'
                        : candidate.market_cap_tier === 'MID'
                        ? 'bg-indigo-100 text-indigo-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {candidate.market_cap_tier === 'LARGE'
                      ? '대형주'
                      : candidate.market_cap_tier === 'MID'
                      ? '중형주'
                      : '소형주'}
                  </span>
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
                </div>
              </div>

              {/* 감성 분석 결과 */}
              <div className="mt-4 grid grid-cols-4 gap-4">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">종합 감성점수</p>
                  <p className="text-xl font-bold text-gray-900">
                    {(candidate.avg_sentiment * 100).toFixed(0)}%
                  </p>
                </div>
                <div className="bg-green-50 rounded-lg p-3">
                  <div className="flex items-center gap-1 mb-1">
                    <ThumbsUp className="w-3 h-3 text-green-600" />
                    <p className="text-xs text-green-600">긍정</p>
                  </div>
                  <p className="text-xl font-bold text-green-700">
                    {candidate.positive_count}건
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center gap-1 mb-1">
                    <Minus className="w-3 h-3 text-gray-600" />
                    <p className="text-xs text-gray-600">중립</p>
                  </div>
                  <p className="text-xl font-bold text-gray-700">
                    {candidate.neutral_count}건
                  </p>
                </div>
                <div className="bg-red-50 rounded-lg p-3">
                  <div className="flex items-center gap-1 mb-1">
                    <ThumbsDown className="w-3 h-3 text-red-600" />
                    <p className="text-xs text-red-600">부정</p>
                  </div>
                  <p className="text-xl font-bold text-red-700">
                    {candidate.negative_count}건
                  </p>
                </div>
              </div>

              {/* 최근 헤드라인 */}
              {candidate.top_headlines.length > 0 && (
                <div className="mt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    주요 헤드라인
                  </p>
                  <div className="space-y-2">
                    {candidate.top_headlines.slice(0, 3).map((headline, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 text-sm text-gray-600"
                      >
                        <span className="text-primary-600 mt-0.5">•</span>
                        <span>{headline}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 분석 사유 */}
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">{candidate.reasoning}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 마지막 업데이트 */}
      <div className="text-center text-sm text-gray-500">
        마지막 업데이트: {new Date(candidates.timestamp).toLocaleString('ko-KR')}
      </div>
    </div>
  );
}
