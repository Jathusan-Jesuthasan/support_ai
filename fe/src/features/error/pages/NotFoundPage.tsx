import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { HelpCircle } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center text-foreground transition-colors duration-300">
      <div className="max-w-md space-y-6">
        <div className="p-4 bg-primary/10 border border-primary/20 rounded-full text-primary w-fit mx-auto">
          <HelpCircle className="h-12 w-12 animate-bounce" />
        </div>
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight">404 - Page Not Found</h1>
          <p className="text-muted-foreground text-sm leading-relaxed max-w-xs mx-auto">
            The page you are trying to access does not exist or has been shifted permanently.
          </p>
        </div>
        <Link to="/dashboard" className="block">
          <Button className="w-full">Return to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
};
export default NotFoundPage;
