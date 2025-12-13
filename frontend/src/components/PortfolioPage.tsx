import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  AlertCircle,
  ExternalLink,
  Wallet,
  PiggyBank,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';
import { getPortfolio } from '../api/client';

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

// 차트 색상
const COLORS = [
  '#0ea5e9',
  '#8b5cf6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
];

export default function PortfolioPage() {
  const { data: portfolio, isLoading, error, refetch } = useQuery({
    queryKey: ['portfolio'],
    queryFn: getPortfolio,
    refetchInterval: 30000,
  });

  // 파이 차트 데이터 준비
  const pieData = portfolio
    ? [
        ...portfolio.positions.map((pos) => ({
          name: pos.name,
          value: pos.eval_amount,
          ticker: pos.ticker,
        })),
        {
          name: '현금',
          value: portfolio.cash_krw,
          ticker: 'CASH',
        },
      ]
    : [];

  // 전체 손익 계산
  const totalInvestment = portfolio?.positions.reduce(
    (sum, pos) => sum + pos.avg_price * pos.shares,
    0
  ) || 0;
  const totalEvaluation = portfolio?.positions.reduce(
    (sum, pos) => sum + pos.eval_amount,
    0
  ) || 0;
  const totalProfit = totalEvaluation - totalInvestment;
  const totalProfitRate = totalInvestment > 0 ? totalProfit / totalInvestment : 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    );
  }

  if (error || !portfolio) {
    return (
      <div className="card">
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <AlertCircle className="w-12 h-12 mb-4" />
          <p className="text-lg font-medium">포트폴리오 데이터를 불러올 수 없습니다</p>
          <button
            onClick={() => refetch()}
            className="mt-4 btn btn-primary"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 상단 요약 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <Wallet className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <p className="stat-label">총 평가금액</p>
              <p className="stat-value">{formatKRW(portfolio.total_value)}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <PiggyBank className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="stat-label">가용 현금</p>
              <p className="stat-value">{formatKRW(portfolio.cash_krw)}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                totalProfit >= 0 ? 'bg-green-100' : 'bg-red-100'
              }`}
            >
              {totalProfit >= 0 ? (
                <TrendingUp className="w-6 h-6 text-green-600" />
              ) : (
                <TrendingDown className="w-6 h-6 text-red-600" />
              )}
            </div>
            <div>
              <p className="stat-label">총 손익</p>
              <p
                className={`stat-value ${
                  totalProfit >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {formatKRW(totalProfit)}
              </p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-4">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                totalProfitRate >= 0 ? 'bg-green-100' : 'bg-red-100'
              }`}
            >
              {totalProfitRate >= 0 ? (
                <TrendingUp className="w-6 h-6 text-green-600" />
              ) : (
                <TrendingDown className="w-6 h-6 text-red-600" />
              )}
            </div>
            <div>
              <p className="stat-label">총 수익률</p>
              <p
                className={`stat-value ${
                  totalProfitRate >= 0 ? 'text-green-600' : 'text-red-600'
                }`}
              >
                {formatPercent(totalProfitRate)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 포트폴리오 구성 차트 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="card-header">포트폴리오 구성</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(1)}%`
                  }
                >
                  {pieData.map((_, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => formatKRW(value)}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 보유 종목 리스트 */}
        <div className="card">
          <h3 className="card-header">보유 종목</h3>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {portfolio.positions.length > 0 ? (
              portfolio.positions.map((position) => (
                <div
                  key={position.ticker}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-gray-900">
                        {position.name}
                      </p>
                      <Link
                        to={`/technical/${position.ticker}`}
                        className="text-primary-600 hover:text-primary-700"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Link>
                    </div>
                    <p className="text-sm text-gray-500">{position.ticker}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">
                      {formatKRW(position.eval_amount)}
                    </p>
                    <p
                      className={`text-sm ${
                        position.profit_loss_rate >= 0
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {formatPercent(position.profit_loss_rate)}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <div className="flex items-center justify-center h-40 text-gray-500">
                보유 종목이 없습니다
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 상세 테이블 */}
      <div className="card">
        <h3 className="card-header">보유 종목 상세</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">
                  종목명
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">
                  보유수량
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">
                  매입가
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">
                  현재가
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">
                  평가금액
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">
                  손익률
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-500">
                  비중
                </th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map((position) => (
                <tr
                  key={position.ticker}
                  className="border-b border-gray-100 hover:bg-gray-50"
                >
                  <td className="py-3 px-4">
                    <div>
                      <p className="font-medium text-gray-900">
                        {position.name}
                      </p>
                      <p className="text-sm text-gray-500">{position.ticker}</p>
                    </div>
                  </td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    {position.shares.toLocaleString()}주
                  </td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    {formatKRW(position.avg_price)}
                  </td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    {formatKRW(position.current_price)}
                  </td>
                  <td className="text-right py-3 px-4 font-medium text-gray-900">
                    {formatKRW(position.eval_amount)}
                  </td>
                  <td
                    className={`text-right py-3 px-4 font-medium ${
                      position.profit_loss_rate >= 0
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}
                  >
                    {formatPercent(position.profit_loss_rate)}
                  </td>
                  <td className="text-right py-3 px-4 text-gray-900">
                    {(position.weight_in_portfolio * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 마지막 업데이트 */}
      <div className="text-center text-sm text-gray-500">
        마지막 업데이트: {new Date(portfolio.last_updated).toLocaleString('ko-KR')}
      </div>
    </div>
  );
}
