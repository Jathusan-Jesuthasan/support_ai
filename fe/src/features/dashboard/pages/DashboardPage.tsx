import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';
import {
  MessageSquare,
  MessageCircle,
  ThumbsUp,
  ThumbsDown,
  TrendingUp,
  ArrowRight,
  BookOpen,
  Sliders,
  AlertCircle
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const { activeCompanyId, companies } = useAuth();

  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboardStats', activeCompanyId],
    queryFn: async () => {
      if (!activeCompanyId) return null;
      const response = await apiClient.get(`/companies/${activeCompanyId}/analytics/dashboard`);
      return response.data.data;
    },
    enabled: !!activeCompanyId,
  });

  if (companies.length === 0) {
    return (
      <EmptyState
        icon={AlertCircle}
        title="No Company Workspace Found"
        description="You are not associated with any tenant company workspace yet. Please create or manage workspaces to continue."
        actionText="Manage Workspaces"
        onAction={() => window.location.href = '/companies'}
      />
    );
  }

  if (!activeCompanyId) {
    return (
      <div className="flex flex-col items-center justify-center p-8 border border-border rounded-xl bg-card text-center min-h-[300px]">
        <h3 className="font-semibold text-lg mb-1">Select a Workspace</h3>
        <p className="text-sm text-muted-foreground mb-4">Please select a company workspace from the switcher at the top to view dashboard metrics.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Overview</h1>
        <p className="text-muted-foreground text-sm">
          Here is a summary of customer support metrics and activities for your active workspace.
        </p>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      ) : error ? (
        <div className="p-6 border border-destructive/20 bg-destructive/5 text-destructive rounded-xl flex flex-col items-center gap-4 text-center">
          <p className="font-medium text-sm">Failed to load analytics metrics. Please ensure backend services are active.</p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      ) : stats ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-in fade-in-50 duration-200">
          {/* Card 1: Total Conversations */}
          <Card className="hover:border-primary/30 transition-all">
            <CardContent className="p-6 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Conversations
                </p>
                <h3 className="text-2xl font-bold">{stats.total_conversations}</h3>
              </div>
              <div className="p-3 bg-primary/10 text-primary rounded-xl">
                <MessageSquare className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          {/* Card 2: Total Messages */}
          <Card className="hover:border-primary/30 transition-all">
            <CardContent className="p-6 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Messages Logged
                </p>
                <h3 className="text-2xl font-bold">{stats.total_messages}</h3>
              </div>
              <div className="p-3 bg-indigo-500/10 text-indigo-500 rounded-xl">
                <MessageCircle className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          {/* Card 3: Feedback Score */}
          <Card className="hover:border-primary/30 transition-all">
            <CardContent className="p-6 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Helpfulness Ratings
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs flex items-center gap-1 text-emerald-600 font-medium">
                    <ThumbsUp className="h-3 w-3" /> {stats.helpful_ratings}
                  </span>
                  <span className="text-muted-foreground/40 text-xs">|</span>
                  <span className="text-xs flex items-center gap-1 text-destructive font-medium">
                    <ThumbsDown className="h-3 w-3" /> {stats.unhelpful_ratings}
                  </span>
                </div>
              </div>
              <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-xl">
                <ThumbsUp className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>

          {/* Card 4: Escalation Rate */}
          <Card className="hover:border-primary/30 transition-all">
            <CardContent className="p-6 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Escalation Rate
                </p>
                <h3 className="text-2xl font-bold">{stats.escalation_rate.toFixed(1)}%</h3>
              </div>
              <div className="p-3 bg-amber-500/10 text-amber-500 rounded-xl">
                <TrendingUp className="h-5 w-5" />
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* Quick Actions Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold">Quick Actions</CardTitle>
          <CardDescription>Get started with the primary workspace setups</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-border/80 bg-muted/15 flex flex-col justify-between items-start gap-4">
            <div className="space-y-1">
              <div className="p-2 bg-primary/10 text-primary rounded-lg inline-block mb-1">
                <BookOpen className="h-4.5 w-4.5" />
              </div>
              <h4 className="font-semibold text-sm">Upload Knowledge Source</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Provide manuals or TXT/PDF files for RAG grounding answers.
              </p>
            </div>
            <Link to="/knowledge">
              <Button size="sm" variant="outline" className="text-xs flex items-center gap-1.5">
                Go to Uploads <ArrowRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>

          <div className="p-4 rounded-xl border border-border/80 bg-muted/15 flex flex-col justify-between items-start gap-4">
            <div className="space-y-1">
              <div className="p-2 bg-indigo-500/10 text-indigo-500 rounded-lg inline-block mb-1">
                <MessageSquare className="h-4.5 w-4.5" />
              </div>
              <h4 className="font-semibold text-sm">RAG Chat Playground</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Test generative model streaming responses and citations.
              </p>
            </div>
            <Link to="/chat">
              <Button size="sm" variant="outline" className="text-xs flex items-center gap-1.5">
                Start Chatting <ArrowRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>

          <div className="p-4 rounded-xl border border-border/80 bg-muted/15 flex flex-col justify-between items-start gap-4">
            <div className="space-y-1">
              <div className="p-2 bg-amber-500/10 text-amber-500 rounded-lg inline-block mb-1">
                <Sliders className="h-4.5 w-4.5" />
              </div>
              <h4 className="font-semibold text-sm">Widget Configurations</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Customize colors, bot details, allowed CORS origins and copy embed script.
              </p>
            </div>
            <Link to="/widget">
              <Button size="sm" variant="outline" className="text-xs flex items-center gap-1.5">
                Configure Widget <ArrowRight className="h-3 w-3" />
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
export default DashboardPage;
