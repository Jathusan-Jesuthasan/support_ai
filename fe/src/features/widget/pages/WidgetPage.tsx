import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { useForm } from 'react-hook-form';
import { Sliders, Copy, Check, MessageSquare, Bot, Globe, Shield } from 'lucide-react';
import toast from 'react-hot-toast';

interface WidgetSettings {
  theme_color: string;
  welcome_message: string;
  bot_name: string;
  allowed_domains: string[];
  is_enabled: boolean;
}

export const WidgetPage: React.FC = () => {
  const { activeCompanyId } = useAuth();
  
  const [isLoadingAction, setIsLoadingAction] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm({
    defaultValues: {
      themeColor: '#4f46e5',
      botName: 'SupportBot',
      welcomeMessage: 'Hello! How can I help you today?',
      allowedDomains: '',
      isEnabled: true,
    },
  });

  // Watch values for real-time live preview panel
  const watchThemeColor = watch('themeColor');
  const watchBotName = watch('botName');
  const watchWelcomeMessage = watch('welcomeMessage');
  const watchIsEnabled = watch('isEnabled');

  // 1. Fetch Widget Settings
  const { isLoading: isSettingsLoading, refetch: refetchSettings } = useQuery({
    queryKey: ['widgetSettings', activeCompanyId],
    queryFn: async () => {
      if (!activeCompanyId) return null;
      const response = await apiClient.get(`/companies/${activeCompanyId}/widget/settings`);
      const data: WidgetSettings = response.data.data;
      
      // Populate form values
      setValue('themeColor', data.theme_color);
      setValue('botName', data.bot_name);
      setValue('welcomeMessage', data.welcome_message);
      setValue('allowedDomains', data.allowed_domains.join(', '));
      setValue('isEnabled', data.is_enabled);
      
      return data;
    },
    enabled: !!activeCompanyId,
  });

  // 2. Action: Save Widget Settings
  const onSubmit = async (data: any) => {
    if (!activeCompanyId) return;
    setIsLoadingAction(true);
    try {
      const domainsArray = data.allowedDomains
        .split(',')
        .map((d: string) => d.trim())
        .filter((d: string) => d.length > 0);

      await apiClient.put(`/companies/${activeCompanyId}/widget/settings`, {
        theme_color: data.themeColor,
        welcome_message: data.welcomeMessage,
        bot_name: data.botName,
        allowed_domains: domainsArray,
        is_enabled: data.isEnabled === 'true' || data.isEnabled === true,
      });
      toast.success('Widget settings updated successfully!');
      refetchSettings();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to update widget settings.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 3. Action: Copy Embed Script Loader
  const embedScript = `<script
  src="http://localhost:8001/api/v1/widget/loader.js"
  data-company-id="${activeCompanyId || '00000000-0000-0000-0000-000000000000'}"
  async
></script>`;

  const handleCopyScript = () => {
    navigator.clipboard.writeText(embedScript);
    setIsCopied(true);
    toast.success('Embed script copied to clipboard!');
    setTimeout(() => setIsCopied(false), 2000);
  };

  if (!activeCompanyId) {
    return (
      <EmptyState
        icon={Sliders}
        title="No Company Selected"
        description="Select or create a company workspace to configure your support widget."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Widget Settings</h1>
        <p className="text-muted-foreground text-sm">
          Customize styles, bots, allowed CORS domain origins, and embed scripts for your support chat.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Settings Form & Loader Script (Left 7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-bold">Branding & Configurations</CardTitle>
              <CardDescription>Update theme colors, default greetings, and domains</CardDescription>
            </CardHeader>
            <CardContent>
              {isSettingsLoading ? (
                <div className="space-y-4">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : (
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <Input
                      label="Chatbot Display Name"
                      placeholder="SupportBot"
                      error={errors.botName?.message as string}
                      {...register('botName', { required: 'Bot name is required' })}
                    />
                    
                    <div className="space-y-1">
                      <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                        Brand Theme Color
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="color"
                          className="h-10 w-12 rounded border border-border cursor-pointer p-0.5"
                          {...register('themeColor')}
                        />
                        <Input
                          placeholder="#4f46e5"
                          {...register('themeColor', {
                            required: 'Theme color is required',
                            pattern: {
                              value: /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/,
                              message: 'Invalid hex code format',
                            },
                          })}
                        />
                      </div>
                    </div>
                  </div>

                  <Input
                    label="Welcome / Greeting Message"
                    placeholder="Hello! How can I help you today?"
                    error={errors.welcomeMessage?.message as string}
                    {...register('welcomeMessage', { required: 'Welcome message is required' })}
                  />

                  <Input
                    label="Allowed Domains (CORS Whitelist)"
                    placeholder="https://mywebsite.com, http://localhost:3000"
                    helperText="Comma-separated URLs where the widget is allowed to load. If empty, CORS blocks anonymous widget loads."
                    {...register('allowedDomains')}
                  />

                  <div className="flex items-center gap-2 pt-2">
                    <input
                      type="checkbox"
                      id="isEnabled"
                      className="rounded border-border text-primary focus:ring-ring h-4 w-4"
                      {...register('isEnabled')}
                    />
                    <label htmlFor="isEnabled" className="text-sm font-semibold select-none cursor-pointer">
                      Enable support widget loads for this company workspace
                    </label>
                  </div>

                  <div className="flex justify-end pt-4 border-t border-border/40">
                    <Button type="submit" isLoading={isLoadingAction}>
                      Save Widget Settings
                    </Button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>

          {/* Embed Script Panel */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <Globe className="h-4.5 w-4.5 text-primary" /> Embed Script Code
              </CardTitle>
              <CardDescription>
                Copy and paste this HTML snippet before your site&apos;s closing &lt;/body&gt; tag to activate the bot.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative bg-muted/65 p-4 rounded-lg border border-border/40 font-mono text-xs overflow-x-auto text-foreground/85 leading-relaxed">
                <pre>{embedScript}</pre>
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-3 right-3 rounded-full border bg-background"
                  onClick={handleCopyScript}
                >
                  {isCopied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Live Preview Panel (Right 5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-3 sticky top-20">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground px-1">
            Live Interactive Preview
          </span>
          <div className="border border-border/80 rounded-xl overflow-hidden shadow-lg h-[480px] bg-background/90 flex flex-col relative">
            {/* Widget Header Mock */}
            <div
              className="px-4 py-3 flex items-center gap-2.5 text-white transition-all"
              style={{ backgroundColor: watchThemeColor }}
            >
              <div className="p-1 bg-white/20 rounded-lg">
                <Bot className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold leading-none mb-0.5">{watchBotName}</p>
                <p className="text-[10px] text-white/80 leading-none">Online</p>
              </div>
            </div>

            {/* Widget Body Mock */}
            <div className="flex-1 p-4 bg-muted/10 space-y-4 overflow-y-auto flex flex-col">
              {/* Check Enabled state */}
              {!watchIsEnabled && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
                  <Shield className="h-8 w-8 text-destructive/40 mb-2 animate-pulse-slow" />
                  <p className="text-xs font-semibold text-destructive">Widget Disabled</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Toggle configuration checkbox to enable.</p>
                </div>
              )}

              {watchIsEnabled && (
                <>
                  {/* Welcome bubble */}
                  <div className="flex gap-2 max-w-[85%] mr-auto items-start">
                    <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center font-bold text-xs text-primary uppercase shrink-0 border border-primary/20">
                      B
                    </div>
                    <div className="px-3 py-2 bg-muted/40 border border-border/40 rounded-lg text-xs leading-relaxed text-foreground rounded-tl-none">
                      {watchWelcomeMessage}
                    </div>
                  </div>

                  {/* Mock user question */}
                  <div className="flex max-w-[85%] ml-auto items-start bg-primary text-primary-foreground px-3 py-2 rounded-lg text-xs leading-relaxed rounded-tr-none shadow-sm">
                    How do I reset my product specifications settings?
                  </div>
                </>
              )}
            </div>

            {/* Widget Footer Input Mock */}
            <div className="p-3 border-t border-border/40 flex gap-2 bg-background">
              <input
                disabled
                placeholder="Ask a question..."
                className="flex-1 bg-muted/30 border border-border/60 rounded px-2.5 py-1.5 text-xs focus:outline-none"
              />
              <Button
                disabled
                size="icon"
                className="h-8 w-8 text-white shrink-0"
                style={{ backgroundColor: watchThemeColor }}
              >
                <MessageSquare className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
export default WidgetPage;
