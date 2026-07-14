import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { DashboardLayout } from '@/layouts/DashboardLayout';
import { AuthLayout } from '@/layouts/AuthLayout';
import { Loader2 } from 'lucide-react';

// Lazy loading page imports (to optimize compilation speed and separate code blocks cleanly)
import LoginPage from '@/features/auth/pages/LoginPage';
import SignupPage from '@/features/auth/pages/SignupPage';
import VerifyEmailPage from '@/features/auth/pages/VerifyEmailPage';
import ForgotPasswordPage from '@/features/auth/pages/ForgotPasswordPage';
import DashboardPage from '@/features/dashboard/pages/DashboardPage';
import CompanyPage from '@/features/company/pages/CompanyPage';
import MembershipPage from '@/features/membership/pages/MembershipPage';
import KnowledgePage from '@/features/knowledge/pages/KnowledgePage';
import ChatPage from '@/features/chat/pages/ChatPage';
import ProductsPage from '@/features/products/pages/ProductsPage';
import WidgetPage from '@/features/widget/pages/WidgetPage';
import AnalyticsPage from '@/features/analytics/pages/AnalyticsPage';
import ProfilePage from '@/features/profile/pages/ProfilePage';
import NotFoundPage from '@/features/error/pages/NotFoundPage';

// Protected Dashboard Layout Wrapper
const ProtectedLayoutWrapper: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-10 w-10 text-primary animate-spin" />
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          Validating Security Session...
        </span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <DashboardLayout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/companies" element={<CompanyPage />} />
        <Route path="/members" element={<MembershipPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/widget" element={<WidgetPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </DashboardLayout>
  );
};

// Anonymous Auth Layout Wrapper
interface AnonymousWrapperProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

const AnonymousLayoutWrapper: React.FC<AnonymousWrapperProps> = ({ children, title, subtitle }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-10 w-10 text-primary animate-spin" />
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          Bootstrapping Workspace...
        </span>
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <AuthLayout title={title} subtitle={subtitle}>
      {children}
    </AuthLayout>
  );
};

export const AppRouter: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        {/* Auth Routes */}
        <Route
          path="/login"
          element={
            <AnonymousLayoutWrapper title="Welcome Back" subtitle="Log in to access your tenant widget workspace">
              <LoginPage />
            </AnonymousLayoutWrapper>
          }
        />
        <Route
          path="/signup"
          element={
            <AnonymousLayoutWrapper title="Get Started" subtitle="Create your account to bootstrap SupportAI">
              <SignupPage />
            </AnonymousLayoutWrapper>
          }
        />
        <Route
          path="/verify-email"
          element={
            <AuthLayout title="Email Activation" subtitle="Confirm your account credentials ownership">
              <VerifyEmailPage />
            </AuthLayout>
          }
        />
        <Route
          path="/forgot-password"
          element={
            <AnonymousLayoutWrapper title="Password Recovery" subtitle="Dispatched secure recovery link to email">
              <ForgotPasswordPage />
            </AnonymousLayoutWrapper>
          }
        />

        {/* Dashboard Routes */}
        <Route path="/*" element={<ProtectedLayoutWrapper />} />

        {/* Error Route */}
        <Route path="/404" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
};
