import React from 'react';
import { Bot } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title, subtitle }) => {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2 bg-background transition-colors duration-300">
      {/* Left Branding Side (Desktop Only) */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-gradient-to-br from-indigo-950 via-slate-900 to-violet-950 text-white relative overflow-hidden">
        {/* Glowing Decorative Orbs */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] rounded-full bg-primary/20 blur-3xl -mr-40 -mt-40 animate-pulse-slow" />
        <div className="absolute bottom-0 left-0 w-[350px] h-[350px] rounded-full bg-violet-600/10 blur-3xl -ml-20 -mb-20" />

        {/* Top Header */}
        <div className="flex items-center gap-3 relative z-10">
          <div className="bg-primary/20 p-2 rounded-xl border border-primary/30">
            <Bot className="h-6 w-6 text-primary" />
          </div>
          <span className="font-bold text-xl tracking-tight bg-gradient-to-r from-white via-indigo-200 to-primary-foreground bg-clip-text text-transparent">
            SupportAI
          </span>
        </div>

        {/* Middle Copy */}
        <div className="max-w-md relative z-10">
          <h1 className="text-4xl font-extrabold tracking-tight leading-tight mb-4">
            Enterprise RAG-Powered Customer Support
          </h1>
          <p className="text-slate-300 text-base leading-relaxed">
            Ingest company documents, sync product catalogs, customize brand widgets, and deploy autonomous grounding agents in minutes.
          </p>
        </div>

        {/* Bottom Metadata */}
        <div className="text-slate-400 text-xs relative z-10">
          &copy; {new Date().getFullYear()} SupportAI Platform. All rights reserved.
        </div>
      </div>

      {/* Right Form Side */}
      <div className="flex items-center justify-center p-6 md:p-12 relative">
        <div className="w-full max-w-md flex flex-col gap-6">
          <div className="flex flex-col gap-2 text-center lg:text-left">
            <h2 className="text-2xl font-bold tracking-tight">
              {title}
            </h2>
            <p className="text-sm text-muted-foreground">
              {subtitle}
            </p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
};
