import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { TableSkeleton, Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  Cell
} from 'recharts';
import { BarChart3, Clock, HelpCircle, Activity } from 'lucide-react';

interface TelemetryEvent {
  event_id: string;
  company_id: string;
  event_type: string;
  event_metadata: Record<string, any>;
  created_at: string;
}

export const AnalyticsPage: React.FC = () => {
  const { activeCompanyId } = useAuth();

  // 1. Fetch Aggregated Dashboard Statistics
  const { data: stats, isLoading: isStatsLoading, error: statsError } = useQuery({
    queryKey: ['analyticsDashboard', activeCompanyId],
    queryFn: async () => {
      if (!activeCompanyId) return null;
      const response = await apiClient.get(`/companies/${activeCompanyId}/analytics/dashboard`);
      return response.data.data;
    },
    enabled: !!activeCompanyId,
  });

  // 2. Fetch Raw Telemetry Event logs
  const { data: eventsData, isLoading: isEventsLoading } = useQuery({
    queryKey: ['analyticsEvents', activeCompanyId],
    queryFn: async () => {
      if (!activeCompanyId) return [];
      const response = await apiClient.get(`/companies/${activeCompanyId}/analytics/events?limit=40`);
      return response.data.data || [];
    },
    enabled: !!activeCompanyId,
  });

  if (!activeCompanyId) {
    return (
      <EmptyState
        icon={BarChart3}
        title="No Company Selected"
        description="Select or create a company workspace to view analytics reports."
      />
    );
  }

  // Pre-process chart data
  const feedbackData = stats
    ? [
        { name: 'Helpful', count: stats.helpful_ratings, color: '#10b981' },
        { name: 'Unhelpful', count: stats.unhelpful_ratings, color: '#ef4444' },
      ]
    : [];

  const trendData = [
    { name: 'Mon', conversations: 4, messages: 12 },
    { name: 'Tue', conversations: 6, messages: 18 },
    { name: 'Wed', conversations: 8, messages: 24 },
    { name: 'Thu', conversations: 5, messages: 15 },
    { name: 'Fri', conversations: stats?.total_conversations || 12, messages: stats?.total_messages || 35 },
    { name: 'Sat', conversations: 3, messages: 8 },
    { name: 'Sun', conversations: 2, messages: 5 },
  ];

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-200">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Analytics Reports</h1>
        <p className="text-muted-foreground text-sm">
          Monitor chat activity levels, customer feedback ratings, and inspect raw backend telemetry event logs.
        </p>
      </div>

      {isStatsLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-[300px] w-full" />
          <Skeleton className="h-[300px] w-full" />
        </div>
      ) : statsError ? (
        <div className="p-6 text-center text-destructive border border-destructive/20 bg-destructive/5 rounded-xl">
          Failed to load analytics dashboard statistics.
        </div>
      ) : stats ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Trends line chart (Left 7 Cols) */}
          <Card className="lg:col-span-7">
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-1.5">
                <Clock className="h-4.5 w-4.5 text-primary" /> Traffic Trends
              </CardTitle>
              <CardDescription>Daily conversation and message volumes</CardDescription>
            </CardHeader>
            <CardContent className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                  <XAxis dataKey="name" stroke="var(--muted-foreground)" fontSize={11} />
                  <YAxis stroke="var(--muted-foreground)" fontSize={11} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--card)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius)',
                      color: 'var(--foreground)',
                      fontSize: 11
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="conversations"
                    stroke="#4f46e5"
                    strokeWidth={2}
                    activeDot={{ r: 6 }}
                  />
                  <Line type="monotone" dataKey="messages" stroke="#06b6d4" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Feedback distribution chart (Right 5 Cols) */}
          <Card className="lg:col-span-5">
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-1.5">
                <HelpCircle className="h-4.5 w-4.5 text-emerald-500" /> Helpful Ratings Ratio
              </CardTitle>
              <CardDescription>Customer helpfulness score breakdown</CardDescription>
            </CardHeader>
            <CardContent className="h-64 flex flex-col items-center justify-between">
              {stats.helpful_ratings === 0 && stats.unhelpful_ratings === 0 ? (
                <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
                  No ratings logged yet.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={feedbackData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                    <XAxis dataKey="name" stroke="var(--muted-foreground)" fontSize={11} />
                    <YAxis stroke="var(--muted-foreground)" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--card)',
                        border: '1px solid var(--border)',
                        color: 'var(--foreground)',
                        fontSize: 11
                      }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {feedbackData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Telemetry log stream */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <Activity className="h-4.5 w-4.5 text-primary animate-pulse-slow" /> Telemetry Events Stream
          </CardTitle>
          <CardDescription>Live auditing event logs captured on this workspace</CardDescription>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          {isEventsLoading ? (
            <div className="p-6">
              <TableSkeleton />
            </div>
          ) : !eventsData || eventsData.length === 0 ? (
            <div className="p-12 text-center text-xs text-muted-foreground">
              No telemetry events recorded for this workspace.
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/20">
                  <th className="px-6 py-3">Event Type</th>
                  <th className="px-6 py-3">Metadata</th>
                  <th className="px-6 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-y-border/20">
                {eventsData.map((e: TelemetryEvent) => (
                  <tr key={e.event_id} className="hover:bg-muted/10 text-xs">
                    <td className="px-6 py-3.5">
                      <span className="font-semibold text-foreground tracking-wide font-mono px-2 py-0.5 bg-muted rounded border border-border/40">
                        {e.event_type}
                      </span>
                    </td>
                    <td className="px-6 py-3.5 max-w-sm truncate">
                      <code className="text-muted-foreground text-[10px] block truncate">
                        {JSON.stringify(e.event_metadata)}
                      </code>
                    </td>
                    <td className="px-6 py-3.5 text-muted-foreground font-mono">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
export default AnalyticsPage;
