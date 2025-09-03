/**
 * Canvas 공유 분석 컴포넌트
 */

import React, { useState, useEffect } from 'react';
import {
  X,
  Eye,
  Download,
  Users,
  Globe,
  MapPin,
  Monitor,
  Smartphone,
  Tablet,
  Chrome,
  Calendar,
  Clock,
  TrendingUp,
  TrendingDown
} from 'lucide-react';

interface ShareAnalytics {
  share_id: string;
  total_views: number;
  total_downloads: number;
  unique_visitors: number;
  views_today: number;
  views_this_week: number;
  views_this_month: number;
  top_countries: Array<{ country: string; views: number }>;
  top_cities: Array<{ city: string; views: number }>;
  device_breakdown: Record<string, number>;
  browser_breakdown: Record<string, number>;
  os_breakdown: Record<string, number>;
  referrer_breakdown: Record<string, number>;
  daily_views: Array<{ date: string; views: number }>;
  hourly_views: Array<{ hour: number; views: number }>;
}

interface CanvasShareAnalyticsProps {
  shareToken: string;
  shareTitle: string;
  isOpen: boolean;
  onClose: () => void;
}

const CanvasShareAnalytics: React.FC<CanvasShareAnalyticsProps> = ({
  shareToken,
  shareTitle,
  isOpen,
  onClose
}) => {
  const [analytics, setAnalytics] = useState<ShareAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadAnalytics = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v1/canvas/share/${shareToken}/analytics`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
      } else {
        setError('Failed to load analytics');
      }
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError('Network error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadAnalytics();
    }
  }, [isOpen, shareToken]);

  const getDeviceIcon = (device: string) => {
    switch (device.toLowerCase()) {
      case 'mobile': return <Smartphone className="h-4 w-4" />;
      case 'tablet': return <Tablet className="h-4 w-4" />;
      default: return <Monitor className="h-4 w-4" />;
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getPercentage = (value: number, total: number) => {
    return total > 0 ? Math.round((value / total) * 100) : 0;
  };

  const getTrendIcon = (current: number, previous: number) => {
    if (current > previous) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (current < previous) return <TrendingDown className="h-4 w-4 text-red-500" />;
    return null;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold">Share Analytics</h2>
            <p className="text-gray-600 text-sm mt-1">{shareTitle}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-md"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* 내용 */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          )}

          {error && (
            <div className="text-center text-red-500 py-8">
              <p>{error}</p>
              <button
                onClick={loadAnalytics}
                className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
              >
                Retry
              </button>
            </div>
          )}

          {analytics && (
            <div className="space-y-8">
              {/* 메인 메트릭 */}
              <div className="grid grid-cols-4 gap-6">
                <div className="bg-blue-50 p-6 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-blue-600 text-sm font-medium">Total Views</p>
                      <p className="text-2xl font-bold text-blue-900">{formatNumber(analytics.total_views)}</p>
                    </div>
                    <Eye className="h-8 w-8 text-blue-500" />
                  </div>
                  <div className="flex items-center mt-2 text-sm text-blue-600">
                    {getTrendIcon(analytics.views_this_week, analytics.views_this_month - analytics.views_this_week)}
                    <span>Today: {analytics.views_today}</span>
                  </div>
                </div>

                <div className="bg-green-50 p-6 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-green-600 text-sm font-medium">Downloads</p>
                      <p className="text-2xl font-bold text-green-900">{formatNumber(analytics.total_downloads)}</p>
                    </div>
                    <Download className="h-8 w-8 text-green-500" />
                  </div>
                  <div className="text-sm text-green-600 mt-2">
                    Rate: {getPercentage(analytics.total_downloads, analytics.total_views)}%
                  </div>
                </div>

                <div className="bg-purple-50 p-6 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-purple-600 text-sm font-medium">Unique Visitors</p>
                      <p className="text-2xl font-bold text-purple-900">{formatNumber(analytics.unique_visitors)}</p>
                    </div>
                    <Users className="h-8 w-8 text-purple-500" />
                  </div>
                  <div className="text-sm text-purple-600 mt-2">
                    Return Rate: {getPercentage(analytics.total_views - analytics.unique_visitors, analytics.total_views)}%
                  </div>
                </div>

                <div className="bg-orange-50 p-6 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-orange-600 text-sm font-medium">This Week</p>
                      <p className="text-2xl font-bold text-orange-900">{formatNumber(analytics.views_this_week)}</p>
                    </div>
                    <Calendar className="h-8 w-8 text-orange-500" />
                  </div>
                  <div className="text-sm text-orange-600 mt-2">
                    This Month: {analytics.views_this_month}
                  </div>
                </div>
              </div>

              {/* 차트 섹션 */}
              <div className="grid grid-cols-2 gap-6">
                {/* 일별 조회수 */}
                <div className="bg-white border rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Daily Views (Last 30 Days)</h3>
                  <div className="h-48 flex items-end space-x-1">
                    {analytics.daily_views.map((day, index) => (
                      <div key={index} className="flex-1 flex flex-col items-center">
                        <div
                          className="bg-blue-500 w-full min-h-[4px] rounded-t"
                          style={{
                            height: `${Math.max(4, (day.views / Math.max(...analytics.daily_views.map(d => d.views))) * 160)}px`
                          }}
                        />
                        <div className="text-xs text-gray-500 mt-1 transform -rotate-45">
                          {new Date(day.date).getDate()}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 시간별 조회수 */}
                <div className="bg-white border rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Hourly Views (Today)</h3>
                  <div className="h-48 flex items-end space-x-1">
                    {Array.from({ length: 24 }, (_, hour) => {
                      const hourData = analytics.hourly_views.find(h => h.hour === hour);
                      const views = hourData?.views || 0;
                      return (
                        <div key={hour} className="flex-1 flex flex-col items-center">
                          <div
                            className="bg-green-500 w-full min-h-[4px] rounded-t"
                            style={{
                              height: `${Math.max(4, views > 0 ? (views / Math.max(...analytics.hourly_views.map(h => h.views))) * 160 : 4)}px`
                            }}
                          />
                          <div className="text-xs text-gray-500 mt-1">
                            {hour}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* 지역 및 디바이스 분석 */}
              <div className="grid grid-cols-3 gap-6">
                {/* 상위 국가 */}
                <div className="bg-white border rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Top Countries</h3>
                  <div className="space-y-3">
                    {analytics.top_countries.slice(0, 5).map((country, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Globe className="h-4 w-4 text-gray-400" />
                          <span className="text-sm">{country.country}</span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium">{country.views}</div>
                          <div className="text-xs text-gray-500">
                            {getPercentage(country.views, analytics.total_views)}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 디바이스 유형 */}
                <div className="bg-white border rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Device Types</h3>
                  <div className="space-y-3">
                    {Object.entries(analytics.device_breakdown).map(([device, views]) => (
                      <div key={device} className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {getDeviceIcon(device)}
                          <span className="text-sm capitalize">{device}</span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium">{views}</div>
                          <div className="text-xs text-gray-500">
                            {getPercentage(views, analytics.total_views)}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 브라우저 */}
                <div className="bg-white border rounded-lg p-6">
                  <h3 className="text-lg font-semibold mb-4">Browsers</h3>
                  <div className="space-y-3">
                    {Object.entries(analytics.browser_breakdown).slice(0, 5).map(([browser, views]) => (
                      <div key={browser} className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Chrome className="h-4 w-4 text-gray-400" />
                          <span className="text-sm capitalize">{browser}</span>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium">{views}</div>
                          <div className="text-xs text-gray-500">
                            {getPercentage(views, analytics.total_views)}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* 트래픽 소스 */}
              <div className="bg-white border rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Traffic Sources</h3>
                <div className="grid grid-cols-2 gap-4">
                  {Object.entries(analytics.referrer_breakdown).slice(0, 8).map(([referrer, views]) => (
                    <div key={referrer} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span className="text-sm">{referrer === 'direct' ? 'Direct' : referrer}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">{views}</div>
                        <div className="text-xs text-gray-500">
                          {getPercentage(views, analytics.total_views)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 푸터 */}
        <div className="border-t p-6 bg-gray-50">
          <div className="flex justify-between items-center">
            <div className="text-sm text-gray-600">
              Data refreshes every hour. Last updated: {new Date().toLocaleString()}
            </div>
            <button
              onClick={loadAnalytics}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              Refresh Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CanvasShareAnalytics;