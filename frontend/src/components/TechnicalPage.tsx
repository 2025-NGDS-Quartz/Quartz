import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  BarChart3,
  RefreshCw,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
} from 'lucide-react';
import { getTechnicalAnalysis } from '../api/client';
import type { PeriodAnalysis } from '../types';

// RSI 게이지 컴포넌트
function RSIGauge({ value }: { value: number }) {
  const getColor = () => {
    if (value >= 70) return 'text-red-500';
    if (value <= 30) return 'text-green-500';
    return 'text-gray-700';
  };

  const getLabel = () => {
    if (value >= 70) return '과매수';
    if (value <= 30) return '과매도';
    return '중립';
  };

  return (
    <div className="text-center">
      <div className="relative inline-flex items-center justify-center">
        <svg className="w-24 h-24 transform -rotate-90">
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke="#e5e7eb"
            strokeWidth="8"
          />
          <circle
            cx="48"
            cy="48"
            r="40"
            fill="none"
            stroke={value >= 70 ? '#ef4444' : value <= 30 ? '#10b981' : '#6b7280'}
            strokeWidth="8"
            strokeDasharray={`${(value / 100) * 251.2} 251.2`}
            strokeLinecap="round"
          />
        </svg>
        <span className={`absolute text-2xl font-bold ${getColor()}`}>
          {value.toFixed(1)}
        </span>
      </div>
      <p className={`mt-2 text-sm font-medium ${getColor()}`}>{getLabel()}</p>
    </div>
  );
}

// MACD 시그널 컴포넌트
function MACDSignal({ macd }: { macd: PeriodAnalysis['macd'] }) {
  const getSignalColor = () => {
    if (macd.signal === 'bullish') return 'text-green-600 bg-green-100';
    if (macd.signal === 'bearish') return 'text-red-600 bg-red-100';
    return 'text-gray-600 bg-gray-100';
  };

  const getSignalIcon = () => {
    if (macd.signal === 'bullish') return <TrendingUp className="w-5 h-5" />;
    if (macd.signal === 'bearish') return <TrendingDown className="w-5 h-5" />;
    return <Minus className="w-5 h-5" />;
  };

  return (
    <div className="space-y-3">
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${getSignalColor()}`}>
        {getSignalIcon()}
        <span className="font-medium capitalize">{macd.signal}</span>
      </div>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-gray-500">MACD</p>
          <p className="font-medium">{macd.macd_line.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-gray-500">Signal</p>
          <p className="font-medium">{macd.signal_line.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-gray-500">Histogram</p>
          <p className={`font-medium ${macd.histogram >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {macd.histogram.toLocaleString()}
          </p>
        </div>
      </div>
    </div>
  );
}

// 볼린저밴드 시각화
function BollingerBandChart({ bb, currentPrice }: { bb: PeriodAnalysis['bollinger_band']; currentPrice: number }) {
  const position = ((currentPrice - bb.bottom) / (bb.top - bb.bottom)) * 100;

  return (
    <div className="space-y-3">
      <div className="relative h-4 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="absolute top-0 left-0 h-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-400"
          style={{ width: '100%' }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-primary-600 rounded-full border-2 border-white shadow-md"
          style={{ left: `${Math.min(Math.max(position, 0), 100)}%`, transform: 'translate(-50%, -50%)' }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-500">
        <span>하단: {bb.bottom.toLocaleString()}</span>
        <span className="font-medium text-gray-700">현재: {currentPrice.toLocaleString()}</span>
        <span>상단: {bb.top.toLocaleString()}</span>
      </div>
    </div>
  );
}

// 피보나치 레벨 시각화
function FibonacciLevels({ fib, currentPrice }: { fib: PeriodAnalysis['fibonacci_retracement']; currentPrice: number }) {
  const levels = Object.entries(fib.levels).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <span className={`badge ${
          fib.trend === 'up' ? 'badge-success' : fib.trend === 'down' ? 'badge-danger' : 'badge-info'
        }`}>
          추세: {fib.trend === 'up' ? '상승' : fib.trend === 'down' ? '하락' : '횡보'}
        </span>
      </div>
      {levels.map(([level, value]) => {
        const isCurrentLevel = currentPrice >= value && 
          levels.findIndex(([_, v]) => v === value) > 0 &&
          currentPrice < levels[levels.findIndex(([_, v]) => v === value) - 1][1];
        
        return (
          <div
            key={level}
            className={`flex justify-between py-1 px-2 rounded ${
              isCurrentLevel ? 'bg-primary-50' : ''
            }`}
          >
            <span className="text-sm text-gray-600">
              {level.replace('level_', '')}%
            </span>
            <span className={`text-sm font-medium ${
              isCurrentLevel ? 'text-primary-700' : 'text-gray-900'
            }`}>
              {value.toLocaleString()}원
            </span>
          </div>
        );
      })}
    </div>
  );
}

// 이동평균선 표시
function MADisplay({ ma, currentPrice }: { ma: PeriodAnalysis['ma']; currentPrice: number }) {
  const data = [
    { name: 'MA5', value: ma.ma5, color: '#ef4444' },
    { name: 'MA10', value: ma.ma10, color: '#f59e0b' },
    { name: 'MA20', value: ma.ma20, color: '#10b981' },
    { name: '현재가', value: currentPrice, color: '#0ea5e9' },
  ].sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-3">
      {data.map((item) => (
        <div key={item.name} className="flex items-center gap-3">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-sm text-gray-600 w-16">{item.name}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-2">
            <div
              className="h-full rounded-full"
              style={{
                width: `${(item.value / Math.max(...data.map(d => d.value))) * 100}%`,
                backgroundColor: item.color,
              }}
            />
          </div>
          <span className="text-sm font-medium text-gray-900 w-24 text-right">
            {item.value.toLocaleString()}원
          </span>
        </div>
      ))}
    </div>
  );
}

// 기간별 분석 카드
function PeriodAnalysisCard({ 
  title, 
  analysis, 
  currentPrice 
}: { 
  title: string; 
  analysis: PeriodAnalysis; 
  currentPrice: number;
}) {
  return (
    <div className="card">
      <h3 className="card-header">{title} 분석</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* RSI */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700 mb-3">RSI (14)</h4>
          <RSIGauge value={analysis.rsi} />
        </div>

        {/* MACD */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700 mb-3">MACD</h4>
          <MACDSignal macd={analysis.macd} />
        </div>

        {/* 볼린저밴드 */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700 mb-3">볼린저밴드</h4>
          <BollingerBandChart bb={analysis.bollinger_band} currentPrice={currentPrice} />
        </div>

        {/* 이동평균선 */}
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700 mb-3">이동평균선</h4>
          <MADisplay ma={analysis.ma} currentPrice={currentPrice} />
        </div>
      </div>

      {/* 피보나치 */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-700 mb-3">피보나치 되돌림</h4>
        <FibonacciLevels fib={analysis.fibonacci_retracement} currentPrice={currentPrice} />
      </div>
    </div>
  );
}

export default function TechnicalPage() {
  const { ticker: paramTicker } = useParams();
  const [inputTicker, setInputTicker] = useState(paramTicker || '');
  const [searchTicker, setSearchTicker] = useState(paramTicker || '');

  const { data: analysis, isLoading, error } = useQuery({
    queryKey: ['technical', searchTicker],
    queryFn: () => getTechnicalAnalysis(searchTicker),
    enabled: !!searchTicker && searchTicker.length === 6,
    retry: 1,
  });

  const handleSearch = () => {
    if (inputTicker.length === 6) {
      setSearchTicker(inputTicker);
    }
  };

  return (
    <div className="space-y-6">
      {/* 검색 */}
      <div className="card">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={inputTicker}
              onChange={(e) => setInputTicker(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="종목코드 입력 (예: 005930)"
              maxLength={6}
              className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={inputTicker.length !== 6}
            className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            분석
          </button>
        </div>
      </div>

      {/* 로딩 */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 text-primary-600 animate-spin" />
        </div>
      )}

      {/* 에러 */}
      {error && (
        <div className="card">
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <AlertCircle className="w-12 h-12 mb-4" />
            <p className="text-lg font-medium">기술 분석 데이터를 불러올 수 없습니다</p>
            <p className="text-sm mt-2">종목코드를 확인해주세요</p>
          </div>
        </div>
      )}

      {/* 분석 결과 */}
      {analysis && (
        <>
          {/* 헤더 */}
          <div className="card">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
                  <BarChart3 className="w-6 h-6 text-primary-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{analysis.ticker}</h2>
                  <p className="text-sm text-gray-500">기술적 분석 결과</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-gray-900">
                  {analysis.current_price.toLocaleString()}원
                </p>
                <p className="text-sm text-gray-500">
                  분석 시간: {new Date(analysis.analysis_time).toLocaleString('ko-KR')}
                </p>
              </div>
            </div>
          </div>

          {/* 일봉 분석 */}
          <PeriodAnalysisCard
            title="일봉"
            analysis={analysis.day}
            currentPrice={analysis.current_price}
          />

          {/* 주봉 분석 */}
          <PeriodAnalysisCard
            title="주봉"
            analysis={analysis.week}
            currentPrice={analysis.current_price}
          />

          {/* 월봉 분석 */}
          <PeriodAnalysisCard
            title="월봉"
            analysis={analysis.month}
            currentPrice={analysis.current_price}
          />
        </>
      )}

      {/* 미검색 상태 */}
      {!searchTicker && !isLoading && (
        <div className="card">
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <BarChart3 className="w-12 h-12 mb-4" />
            <p className="text-lg font-medium">종목코드를 입력하세요</p>
            <p className="text-sm mt-2">6자리 종목코드를 입력하면 기술적 분석 결과가 표시됩니다</p>
          </div>
        </div>
      )}
    </div>
  );
}
