import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import toast from 'react-hot-toast';

export const ForgotPasswordPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [isSent, setIsSent] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      email: '',
    },
  });

  const onSubmit = async (_data: any) => {
    setIsLoading(true);
    // Simulate API request timeout
    setTimeout(() => {
      setIsLoading(false);
      setIsSent(true);
      toast.success('If this email is registered, we have sent a password reset link.');
    }, 1000);
  };

  return (
    <div className="space-y-4">
      {!isSent ? (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <p className="text-sm text-muted-foreground mb-2">
            Enter your email address and we will send you a secure link to reset your password.
          </p>
          <Input
            label="Email Address"
            type="email"
            placeholder="name@company.com"
            error={errors.email?.message}
            {...register('email', {
              required: 'Email is required',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Invalid email address',
              },
            })}
          />
          <Button type="submit" className="w-full" isLoading={isLoading}>
            Send Reset Link
          </Button>
        </form>
      ) : (
        <div className="space-y-4 text-center">
          <p className="text-sm text-muted-foreground leading-relaxed">
            A password reset email has been dispatched. Please check your inbox and follow the instructions.
          </p>
          <Link to="/login" className="block">
            <Button variant="outline" className="w-full">Back to Login</Button>
          </Link>
        </div>
      )}

      {!isSent && (
        <p className="text-center text-sm text-muted-foreground mt-4">
          Remember your credentials?{' '}
          <Link to="/login" className="text-primary hover:underline font-medium">
            Sign In
          </Link>
        </p>
      )}
    </div>
  );
};
export default ForgotPasswordPage;
