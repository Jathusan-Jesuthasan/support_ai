import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { apiClient } from '@/services/apiClient';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, XCircle, Loader2, Mail, RefreshCw, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';

const OTP_LENGTH = 6;
const RESEND_COOLDOWN_S = 60;

export const VerifyEmailPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const email: string = (location.state as any)?.email ?? '';

  const [digits, setDigits] = useState<string[]>(Array(OTP_LENGTH).fill(''));
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMsg, setErrorMsg] = useState('');
  const [countdown, setCountdown] = useState(RESEND_COOLDOWN_S);
  const [resendCooldown, setResendCooldown] = useState(true);
  const [resending, setResending] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const redirectTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start the resend cooldown on mount
  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          setResendCooldown(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Auto-redirect after success
  useEffect(() => {
    if (status !== 'success') return;
    let secs = 5;
    redirectTimer.current = setInterval(() => {
      secs -= 1;
      if (secs <= 0) {
        clearInterval(redirectTimer.current!);
        navigate('/login');
      }
    }, 1000);
    return () => clearInterval(redirectTimer.current!);
  }, [status, navigate]);

  const focusAt = (index: number) => {
    inputRefs.current[index]?.focus();
  };

  const handleChange = (index: number, value: string) => {
    // Allow paste of full OTP
    if (value.length > 1) {
      const pasted = value.replace(/\D/g, '').slice(0, OTP_LENGTH);
      if (pasted.length === OTP_LENGTH) {
        const newDigits = pasted.split('');
        setDigits(newDigits);
        focusAt(OTP_LENGTH - 1);
        return;
      }
    }

    const char = value.replace(/\D/g, '').slice(-1);
    const newDigits = [...digits];
    newDigits[index] = char;
    setDigits(newDigits);
    if (char && index < OTP_LENGTH - 1) focusAt(index + 1);
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (digits[index]) {
        const newDigits = [...digits];
        newDigits[index] = '';
        setDigits(newDigits);
      } else if (index > 0) {
        focusAt(index - 1);
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      focusAt(index - 1);
    } else if (e.key === 'ArrowRight' && index < OTP_LENGTH - 1) {
      focusAt(index + 1);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (!pasted) return;
    const newDigits = Array(OTP_LENGTH).fill('');
    pasted.split('').forEach((ch, i) => { newDigits[i] = ch; });
    setDigits(newDigits);
    focusAt(Math.min(pasted.length, OTP_LENGTH - 1));
  };

  const handleVerify = useCallback(async () => {
    const otp = digits.join('');
    if (otp.length < OTP_LENGTH) return;

    setStatus('loading');
    setErrorMsg('');
    try {
      await apiClient.post('/auth/verify-email-otp', { email, otp });
      setStatus('success');
      toast.success('Email verified! Redirecting to login…');
    } catch (err: any) {
      setStatus('error');
      const msg = err.response?.data?.error?.message ?? 'Invalid or expired code. Please try again.';
      setErrorMsg(msg);
    }
  }, [digits, email]);

  // Auto-submit when all digits are filled
  useEffect(() => {
    if (digits.every((d) => d !== '') && status === 'idle') {
      handleVerify();
    }
  }, [digits, status, handleVerify]);

  const handleResend = async () => {
    if (resendCooldown || resending) return;
    setResending(true);
    setStatus('idle');
    setErrorMsg('');
    setDigits(Array(OTP_LENGTH).fill(''));
    focusAt(0);
    try {
      await apiClient.post('/auth/resend-verification-otp', { email });
      toast.success('A new verification code has been sent!');
      setCountdown(RESEND_COOLDOWN_S);
      setResendCooldown(true);
      const interval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            setResendCooldown(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch {
      toast.error('Failed to resend code. Please try again.');
    } finally {
      setResending(false);
    }
  };

  const otp = digits.join('');
  const isComplete = otp.length === OTP_LENGTH;

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-card border border-border rounded-2xl text-center shadow-lg min-h-[380px] w-full max-w-md">

      {/* ── Success ── */}
      {status === 'success' ? (
        <div className="space-y-4 w-full">
          <CheckCircle2 className="h-14 w-14 text-emerald-500 mx-auto" />
          <h3 className="text-xl font-semibold text-emerald-500">Email Verified!</h3>
          <p className="text-sm text-muted-foreground">
            Your account is now active. Redirecting you to login…
          </p>
          <Link to="/login" className="block mt-2">
            <Button className="w-full">Proceed to Sign In</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-6 w-full">

          {/* Header */}
          <div className="space-y-2">
            <div className="flex items-center justify-center w-14 h-14 rounded-full bg-primary/10 mx-auto">
              <ShieldCheck className="h-7 w-7 text-primary" />
            </div>
            <h3 className="text-xl font-semibold">Check your email</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              We sent a 6-digit verification code to{' '}
              {email ? (
                <span className="font-medium text-foreground">{email}</span>
              ) : (
                'your email address'
              )}
              . It expires in <span className="font-medium">10 minutes</span>.
            </p>
          </div>

          {/* OTP digit boxes */}
          <div className="flex justify-center gap-2.5">
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                id={`otp-digit-${i}`}
                type="text"
                inputMode="numeric"
                maxLength={OTP_LENGTH}
                value={digit}
                autoFocus={i === 0}
                onChange={(e) => handleChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                onPaste={handlePaste}
                disabled={status === 'loading'}
                className={[
                  'w-11 h-13 text-center text-xl font-bold rounded-lg border-2 transition-all duration-150',
                  'bg-background outline-none',
                  'focus:border-primary focus:ring-2 focus:ring-primary/20',
                  status === 'error'
                    ? 'border-destructive text-destructive'
                    : digit
                      ? 'border-primary text-foreground'
                      : 'border-border text-foreground',
                  status === 'loading' ? 'opacity-50 cursor-not-allowed' : '',
                ].join(' ')}
                style={{ width: '2.75rem', height: '3.25rem', fontSize: '1.375rem' }}
              />
            ))}
          </div>

          {/* Error message */}
          {status === 'error' && errorMsg && (
            <div className="flex items-center justify-center gap-2 text-destructive text-sm">
              <XCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Verify button */}
          <Button
            id="verify-otp-btn"
            className="w-full"
            disabled={!isComplete || status === 'loading'}
            onClick={() => {
              setStatus('idle');
              setTimeout(handleVerify, 0);
            }}
          >
            {status === 'loading' ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Verifying…
              </span>
            ) : (
              'Verify Email'
            )}
          </Button>

          {/* Resend + back to login */}
          <div className="space-y-2 pt-1">
            <button
              id="resend-otp-btn"
              type="button"
              onClick={handleResend}
              disabled={resendCooldown || resending}
              className={[
                'flex items-center justify-center gap-1.5 w-full text-sm transition-colors',
                resendCooldown || resending
                  ? 'text-muted-foreground cursor-not-allowed'
                  : 'text-primary hover:underline cursor-pointer',
              ].join(' ')}
            >
              {resending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" />
              )}
              {resendCooldown
                ? `Resend code in ${countdown}s`
                : resending
                  ? 'Sending…'
                  : 'Resend verification code'}
            </button>

            <Link to="/login" className="block">
              <Button variant="outline" className="w-full text-sm" size="sm">
                Back to Login
              </Button>
            </Link>
          </div>

        </div>
      )}
    </div>
  );
};

export default VerifyEmailPage;
