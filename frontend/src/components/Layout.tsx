import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Briefcase,
  TrendingUp,
  BarChart3,
  Activity,
} from 'lucide-react';

interface LayoutProps {
  children: ReactNode;
}

const navItems = [
  { path: '/', icon: LayoutDashboard, label: '대시보드' },
  { path: '/portfolio', icon: Briefcase, label: '포트폴리오' },
  { path: '/candidates', icon: TrendingUp, label: '후보종목' },
  { path: '/technical', icon: BarChart3, label: '기술분석' },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 사이드바 */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 z-30">
        {/* 로고 */}
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <Activity className="w-8 h-8 text-primary-600" />
          <span className="ml-3 text-xl font-bold text-gray-900">Quartz</span>
        </div>

        {/* 네비게이션 */}
        <nav className="mt-6 px-3">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path));
            const Icon = item.icon;

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 mb-1 rounded-lg transition-colors duration-200 ${
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-primary-600' : ''}`} />
                <span className="ml-3 font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* 하단 정보 */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="text-xs text-gray-500">
            <p>멀티에이전트 자동투자 플랫폼</p>
            <p className="mt-1">Quartz v1.0.0</p>
          </div>
        </div>
      </aside>

      {/* 메인 컨텐츠 */}
      <main className="pl-64">
        {/* 헤더 */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center px-8 sticky top-0 z-20">
          <h1 className="text-lg font-semibold text-gray-800">
            {navItems.find(item => 
              location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path))
            )?.label || '대시보드'}
          </h1>
          <div className="ml-auto flex items-center gap-4">
            <span className="text-sm text-gray-500">
              {new Date().toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                weekday: 'long',
              })}
            </span>
          </div>
        </header>

        {/* 페이지 컨텐츠 */}
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  );
}
