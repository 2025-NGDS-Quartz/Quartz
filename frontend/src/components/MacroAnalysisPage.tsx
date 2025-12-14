import { useQuery } from '@tanstack/react-query';
import {
  RefreshCw,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  HelpCircle,
  FileText,
  Clock,
} from 'lucide-react';
import { getMacroAnalysis } from '../api/client';
import type { MacroAnalysis } from '../types';

// 시장 편향 배지 컴포넌트
function MarketBiasBadge({ bias }: { bias: MacroAnalysis['market_bias_hint'] }) {
  const config = {
    bullish: {
      icon: TrendingUp,
      label: '강세',
      className: 'bg-green-100 text-green-700 border-green-200',
      iconClass: 'text-green-600',
    },
    bearish: {
      icon: TrendingDown,
      label: '약세',
      className: 'bg-red-100 text-red-700 border-red-200',
      iconClass: 'text-red-600',
    },
    neutral: {
      icon: Minus,
      label: '중립',
      className: 'bg-gray-100 text-gray-700 border-gray-200',
      iconClass: 'text-gray-600',
    },
    uncertain: {
      icon: HelpCircle,
      label: '불확실',
      className: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      iconClass: 'text-yellow-600',
    },
  };

  const { icon: Icon, label, className, iconClass } = config[bias] || config.uncertain;

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border ${className}`}>
      <Icon className={`w-5 h-5 ${iconClass}`} />
      <span className="font-semibold">{label}</span>
    </div>
  );
}

// 마크다운 렌더링 컴포넌트 (간단 버전)
function MarkdownContent({ content }: { content: string }) {
  // 간단한 마크다운 파싱: 줄바꿈 처리
  const lines = content.split('\n');
  
  return (
    <div className="prose prose-sm max-w-none">
      {lines.map((line, index) => {
        // 빈 줄
        if (!line.trim()) {
          return <br key={index} />;
        }
        
        // 제목 (# 로 시작)
        if (line.startsWith('### ')) {
          return (
            <h4 key={index} className="text-md font-semibold text-gray-800 mt-4 mb-2">
              {line.replace('### ', '')}
            </h4>
          );
        }
        if (line.startsWith('## ')) {
          return (
            <h3 key={index} className="text-lg font-semibold text-gray-900 mt-4 mb-2">
              {line.replace('## ', '')}
            </h3>
          );
        }
        if (line.startsWith('# ')) {
          return (
            <h2 key={index} className="text-xl font-bold text-gray-900 mt-4 mb-2">
              {line.replace('# ', '')}
            </h2>
          );
        }
        
        // 불릿 포인트
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <li key={index} className="text-gray-700 ml-4 list-disc">
              {line.replace(/^[-*] /, '')}
            </li>
          );
        }
        
        // 번호 매기기
        const numberedMatch = line.match(/^(\d+)\. (.+)/);
        if (numberedMatch) {
          return (
            <li key={index} className="text-gray-700 ml-4 list-decimal">
              {numberedMatch[2]}
            </li>
          );
        }
        
        // 일반 텍스트
        return (
          <p key={index} className="text-gray-700 leading-relaxed">
            {line}
          </p>
        );
      })}
    </div>
  );
}

// 보고서 카드 컴포넌트
function ReportCard({
  title,
  content,
  type,
  isLoading,
}: {
  title: string;
  content: string;
  type: 'positive' | 'negative';
  isLoading: boolean;
}) {
  const borderColor = type === 'positive' ? 'border-l-green-500' : 'border-l-red-500';
  const titleColor = type === 'positive' ? 'text-green-700' : 'text-red-700';
  const bgColor = type === 'positive' ? 'bg-green-50' : 'bg-red-50';
  const Icon = type === 'positive' ? TrendingUp : TrendingDown;

  return (
    <div className={`card border-l-4 ${borderColor}`}>
      <div className={`card-header ${bgColor} -mx-6 -mt-6 px-6 py-4 mb-4 rounded-t-lg`}>
        <Icon className={`w-5 h-5 ${titleColor}`} />
        <span className={titleColor}>{title}</span>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-48">
          <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
        </div>
      ) : content && content.length > 100 ? (
        <div className="max-h-[500px] overflow-y-auto pr-2">
          <MarkdownContent content={content} />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-48 text-gray-500">
          <AlertCircle className="w-8 h-8 mb-2" />
          <p>보고서 데이터가 없습니다</p>
          <p className="text-sm mt-1">거시경제 에이전트 실행 후 생성됩니다</p>
        </div>
      )}
    </div>
  );
}

// 메인 페이지 컴포넌트
export default function MacroAnalysisPage() {
  const {
    data: macroData,
    isLoading,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ['macroAnalysis'],
    queryFn: getMacroAnalysis,
    refetchInterval: 300000, // 5분마다 갱신
  });

  const formatDateTime = (dateString: string | null) => {
    if (!dateString) return '알 수 없음';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  return (
    <div className="space-y-6">
      {/* 헤더 섹션 */}
      <div className="card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">거시경제 분석 보고서</h2>
              <p className="text-sm text-gray-500">
                Gemini AI 기반 거시경제 분석 (ECOS, FRED, World Bank 데이터)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* 시장 편향 */}
            {macroData && (
              <MarketBiasBadge bias={macroData.market_bias_hint} />
            )}

            {/* 새로고침 버튼 */}
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="btn-secondary flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              새로고침
            </button>
          </div>
        </div>

        {/* 마지막 업데이트 정보 */}
        <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-4 text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>보고서 생성: {formatDateTime(macroData?.last_update ?? null)}</span>
          </div>
          <div className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            <span>
              마지막 조회: {dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString('ko-KR') : '-'}
            </span>
          </div>
        </div>
      </div>

      {/* 보고서 그리드 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 긍정적 분석 */}
        <ReportCard
          title="긍정적 관점 (Bullish View)"
          content={macroData?.positive_summary || ''}
          type="positive"
          isLoading={isLoading}
        />

        {/* 부정적 분석 */}
        <ReportCard
          title="부정적 관점 (Bearish View)"
          content={macroData?.negative_summary || ''}
          type="negative"
          isLoading={isLoading}
        />
      </div>

      {/* 안내 문구 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div className="text-sm text-blue-700">
            <p className="font-medium mb-1">안내</p>
            <ul className="list-disc list-inside space-y-1 text-blue-600">
              <li>거시경제 보고서는 12시간마다 자동으로 갱신됩니다</li>
              <li>ECOS(한국은행), FRED(미국), World Bank의 데이터를 기반으로 분석됩니다</li>
              <li>포트폴리오 관리 에이전트는 이 보고서의 요약본을 참고하여 투자 결정을 내립니다</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
