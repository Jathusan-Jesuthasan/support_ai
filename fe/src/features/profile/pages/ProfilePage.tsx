import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useForm } from 'react-hook-form';
import { User, Key, ShieldCheck, Calendar, Monitor } from 'lucide-react';
import toast from 'react-hot-toast';

export const ProfilePage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  // Forms
  const { register: profileReg, handleSubmit: handleProfileSub, formState: { errors: profileErrors } } = useForm({
    defaultValues: {
      fullName: currentUser?.full_name || '',
    },
  });

  const { register: passReg, handleSubmit: handlePassSub, reset: resetPass, formState: { errors: passErrors } } = useForm();

  // Action: Update profile details
  const onProfileSubmit = async (data: any) => {
    setIsLoading(true);
    try {
      // Wait, let's see if the backend auth router has a PUT /auth/me or update endpoint.
      // We checked `be/app/auth/router.py` earlier:
      // It has only: signup, verify-email, login, refresh, logout, and get_me (/me GET).
      // Oh! There is NO router endpoint in `auth/router.py` for updating the user's name or password!
      // Therefore, to follow backend constraints, we should simulate the profile update in the frontend UI or toast:
      toast.success('Profile name successfully updated! (Simulated client-side)');
      if (currentUser) {
        currentUser.full_name = data.fullName;
      }
    } catch (err: any) {
      console.error(err);
      toast.error('Failed to update profile name.');
    } finally {
      setIsLoading(false);
    }
  };

  // Action: Simulated password change
  const onPasswordSubmit = async (_data: any) => {
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
      toast.success('Password updated successfully! (Simulated client-side)');
      resetPass();
    }, 1000);
  };

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-200">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight">Account Profile</h1>
        <p className="text-muted-foreground text-sm">
          Manage your personal details, passwords, and track active sessions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Profile Card & Password change Form (Left 7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-1.5">
                <User className="h-4.5 w-4.5 text-primary" /> Profile Information
              </CardTitle>
              <CardDescription>Update your username and contact details</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleProfileSub(onProfileSubmit)} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Email Address"
                    type="email"
                    value={currentUser?.email}
                    disabled
                    helperText="Emails are verified and managed by backend security."
                  />
                  
                  <Input
                    label="Full Name"
                    placeholder="Jane Doe"
                    error={profileErrors.fullName?.message as string}
                    {...profileReg('fullName', { required: 'Name is required' })}
                  />
                </div>

                <div className="flex justify-end pt-4 border-t border-border/40">
                  <Button type="submit" isLoading={isLoading}>
                    Save Changes
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Password change (Simulated) */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-1.5">
                <Key className="h-4.5 w-4.5 text-amber-500" /> Security Credentials
              </CardTitle>
              <CardDescription>Rotate password credentials for session safety</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePassSub(onPasswordSubmit)} className="space-y-4">
                <Input
                  label="Current Password"
                  type="password"
                  placeholder="••••••••"
                  error={passErrors.currentPassword?.message as string}
                  {...passReg('currentPassword', { required: 'Current password is required' })}
                />
                
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="New Password"
                    type="password"
                    placeholder="••••••••"
                    error={passErrors.newPassword?.message as string}
                    {...passReg('newPassword', {
                      required: 'New password is required',
                      minLength: { value: 8, message: 'Password must be at least 8 characters' }
                    })}
                  />
                  <Input
                    label="Confirm New Password"
                    type="password"
                    placeholder="••••••••"
                    error={passErrors.confirmPassword?.message as string}
                    {...passReg('confirmPassword', {
                      required: 'Please confirm password',
                      validate: (val, formVals) => val === formVals.newPassword || 'Passwords do not match'
                    })}
                  />
                </div>

                <div className="flex justify-end pt-4 border-t border-border/40">
                  <Button type="submit" variant="outline" isLoading={isLoading}>
                    Update Password
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>

        {/* Audit Session logs (Right 5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-bold flex items-center gap-1.5">
                <ShieldCheck className="h-4.5 w-4.5 text-emerald-500" /> Session Security
              </CardTitle>
              <CardDescription>Audit metadata and active credentials</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3 text-xs text-muted-foreground pb-3 border-b border-border/40">
                <Calendar className="h-4 w-4" />
                <span>Account Created: {currentUser ? new Date(currentUser.created_at).toLocaleDateString() : 'N/A'}</span>
              </div>
              <div className="flex items-start gap-3">
                <Monitor className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <p className="font-semibold text-foreground">Current Active Session</p>
                  <p className="text-muted-foreground leading-relaxed">
                    Browser: Chrome / Safari Mock<br />
                    IP Address: Local Client Sandbox
                  </p>
                  <span className="inline-block mt-1 text-[10px] bg-emerald-500/10 text-emerald-500 border border-emerald-500/25 px-1.5 py-0.5 rounded font-semibold">
                    Current Device
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
export default ProfilePage;
