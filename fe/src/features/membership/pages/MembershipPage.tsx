import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { EmptyState } from '@/components/ui/EmptyState';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { useForm } from 'react-hook-form';
import { Users, UserPlus, LogOut, ArrowRightLeft, UserX } from 'lucide-react';
import toast from 'react-hot-toast';
import { cn } from '@/utils/cn';

export const MembershipPage: React.FC = () => {
  const { activeCompanyId, user: currentUser, fetchUserAndCompanies } = useAuth();
  const [isLoadingAction, setIsLoadingAction] = useState(false);
  
  // Modals state
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [isTransferOpen, setIsTransferOpen] = useState(false);

  const { register: inviteReg, handleSubmit: handleInviteSub, reset: resetInvite, formState: { errors: inviteErrors } } = useForm();
  const { register: transferReg, handleSubmit: handleTransferSub, reset: resetTransfer } = useForm();

  // 1. Fetch Workspace Members
  const { data: members = [], isLoading: isMembersLoading, error: membersError, refetch: refetchMembers } = useQuery({
    queryKey: ['members', activeCompanyId],
    queryFn: async () => {
      if (!activeCompanyId) return [];
      const response = await apiClient.get('/membership', {
        headers: {
          'X-Company-ID': activeCompanyId, // PermissionChecker fetches company_id from headers
        },
      });
      return response.data.data || [];
    },
    enabled: !!activeCompanyId,
  });

  // Find caller membership role
  const callerMember = members.find((m: any) => m.user_id === currentUser?.user_id);
  const callerRole = callerMember?.role || 'MEMBER';
  const isOwner = callerRole === 'OWNER';
  const isAdminOrOwner = callerRole === 'OWNER' || callerRole === 'ADMIN';

  // 2. Action: Invite User
  const onInviteSubmit = async (data: any) => {
    setIsLoadingAction(true);
    try {
      await apiClient.post(
        '/membership/invite',
        {
          email: data.email,
          role: data.role,
        },
        {
          headers: {
            'X-Company-ID': activeCompanyId,
          },
        }
      );
      toast.success(`Invitation successfully sent to ${data.email}!`);
      refetchMembers();
      setIsInviteOpen(false);
      resetInvite();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to send invitation.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 3. Action: Update Role
  const onRoleChange = async (memberId: string, newRole: string) => {
    setIsLoadingAction(true);
    try {
      await apiClient.patch(
        `/membership/${memberId}/role`,
        {
          role: newRole,
        },
        {
          headers: {
            'X-Company-ID': activeCompanyId,
          },
        }
      );
      toast.success('Member role updated successfully!');
      refetchMembers();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to change role.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 4. Action: Remove Member
  const onRemoveMember = async (memberId: string) => {
    if (!confirm('Are you sure you want to remove this member from the workspace?')) return;
    setIsLoadingAction(true);
    try {
      await apiClient.delete(`/membership/${memberId}`, {
        headers: {
          'X-Company-ID': activeCompanyId,
        },
      });
      toast.success('Member removed from workspace.');
      refetchMembers();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to remove member.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 5. Action: Transfer Ownership
  const onTransferSubmit = async (data: any) => {
    setIsLoadingAction(true);
    try {
      await apiClient.post(
        '/membership/transfer-owner',
        {
          target_user_id: data.targetUserId,
        },
        {
          headers: {
            'X-Company-ID': activeCompanyId,
          },
        }
      );
      toast.success('Ownership transferred successfully!');
      refetchMembers();
      setIsTransferOpen(false);
      resetTransfer();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to transfer ownership.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 6. Action: Leave Workspace
  const onLeaveWorkspace = async () => {
    if (!confirm('Are you sure you want to leave this company workspace?')) return;
    setIsLoadingAction(true);
    try {
      await apiClient.post(
        '/membership/leave',
        {},
        {
          headers: {
            'X-Company-ID': activeCompanyId,
          },
        }
      );
      toast.success('Successfully left the company workspace.');
      await fetchUserAndCompanies();
      window.location.href = '/dashboard';
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to leave workspace.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  if (!activeCompanyId) {
    return (
      <EmptyState
        icon={Users}
        title="No Company Selected"
        description="Select or create a company workspace to manage team members."
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-200">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Team Members</h1>
          <p className="text-muted-foreground text-sm">
            Invite colleagues, configure roles, transfer ownerships, or leave the active workspace.
          </p>
        </div>
        <div className="flex gap-2">
          {isOwner && (
            <Button
              variant="outline"
              onClick={() => setIsTransferOpen(true)}
              className="flex items-center gap-1.5 text-xs"
            >
              <ArrowRightLeft className="h-4 w-4" /> Transfer Ownership
            </Button>
          )}
          <Button
            variant="outline"
            className="flex items-center gap-1.5 text-xs text-destructive hover:bg-destructive/10 border-destructive/20"
            onClick={onLeaveWorkspace}
            isLoading={isLoadingAction}
          >
            <LogOut className="h-4 w-4" /> Leave Workspace
          </Button>
          {isAdminOrOwner && (
            <Button
              onClick={() => setIsInviteOpen(true)}
              className="flex items-center gap-1.5 text-xs"
            >
              <UserPlus className="h-4 w-4" /> Invite Member
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold">Workspace Members</CardTitle>
          <CardDescription>All collaborators and pending invitations</CardDescription>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          {isMembersLoading ? (
            <div className="p-6">
              <TableSkeleton />
            </div>
          ) : membersError ? (
            <div className="p-6 text-center text-destructive text-sm">
              Failed to load team members.
            </div>
          ) : members.length === 0 ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              No team members found in this workspace.
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border/40 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/20">
                  <th className="px-6 py-3.5">User Info</th>
                  <th className="px-6 py-3.5">Role</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-y-border/20">
                {members.map((member: any) => {
                  const isCurrent = member.user_id === currentUser?.user_id;
                  const isTargetOwner = member.role === 'OWNER';
                  const isTargetAdmin = member.role === 'ADMIN';

                  // Determine if current user can edit role
                  let canEdit = false;
                  if (isOwner && !isCurrent) canEdit = true;
                  if (isAdminOrOwner && !isTargetOwner && !isTargetAdmin && !isCurrent) canEdit = true;

                  // Determine if current user can remove member
                  let canRemove = false;
                  if (isOwner && !isCurrent) canRemove = true;
                  if (isAdminOrOwner && !isTargetOwner && !isTargetAdmin && !isCurrent) canRemove = true;

                  return (
                    <tr key={member.membership_id} className="hover:bg-muted/10 text-sm">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center font-bold text-sm text-primary uppercase">
                            {member.email?.charAt(0) || 'U'}
                          </div>
                          <div>
                            <p className="font-semibold flex items-center gap-1.5">
                              {member.email || 'Workspace User'}
                              {isCurrent && (
                                <span className="text-[10px] bg-muted text-muted-foreground border px-1.5 py-0.5 rounded font-normal">
                                  You
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-muted-foreground">ID: {member.user_id}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {canEdit ? (
                          <select
                            value={member.role}
                            onChange={(e) => onRoleChange(member.membership_id, e.target.value)}
                            disabled={isLoadingAction}
                            className="text-xs rounded border border-border bg-background px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-ring font-medium"
                          >
                            <option value="OWNER">Owner</option>
                            <option value="ADMIN">Admin</option>
                            <option value="MEMBER">Member</option>
                            <option value="VIEWER">Viewer</option>
                          </select>
                        ) : (
                          <span className="text-xs font-semibold uppercase tracking-wider bg-secondary text-secondary-foreground border px-2.5 py-1 rounded-md">
                            {member.role}
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full border",
                            {
                              "bg-emerald-500/10 text-emerald-500 border-emerald-500/25": member.status === 'active',
                              "bg-amber-500/10 text-amber-500 border-amber-500/25 animate-pulse-slow": member.status === 'invited',
                              "bg-destructive/10 text-destructive border-destructive/25": member.status === 'removed',
                            }
                          )}
                        >
                          {member.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {canRemove && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive border border-transparent rounded-full"
                            onClick={() => onRemoveMember(member.membership_id)}
                            disabled={isLoadingAction}
                          >
                            <UserX className="h-4 w-4" />
                          </Button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Modal: Invite Member */}
      <Modal isOpen={isInviteOpen} onClose={() => setIsInviteOpen(false)} title="Invite Team Member">
        <form onSubmit={handleInviteSub(onInviteSubmit)} className="space-y-4">
          <Input
            label="Email Address"
            placeholder="colleague@company.com"
            error={inviteErrors.email?.message as string}
            {...inviteReg('email', {
              required: 'Email is required',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Invalid email address',
              },
            })}
          />

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Role Authority
            </label>
            <select
              {...inviteReg('role', { required: true })}
              className="flex w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 transition-all"
            >
              <option value="MEMBER">Member (Read, write, edit, upload sources)</option>
              <option value="VIEWER">Viewer (Read logs and reports only)</option>
              <option value="ADMIN">Admin (Configure system, manage team)</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button variant="outline" type="button" onClick={() => setIsInviteOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoadingAction}>
              Send Invitation
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Transfer Ownership */}
      <Modal isOpen={isTransferOpen} onClose={() => setIsTransferOpen(false)} title="Transfer Workspace Ownership">
        <form onSubmit={handleTransferSub(onTransferSubmit)} className="space-y-4">
          <p className="text-xs text-muted-foreground leading-relaxed">
            Specify the user ID of an active workspace member to transfer the OWNER role to them. Your role will be demoted to ADMIN.
          </p>

          <Input
            label="Target User ID (UUID)"
            placeholder="00000000-0000-0000-0000-000000000000"
            {...transferReg('targetUserId', { required: true })}
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button variant="outline" type="button" onClick={() => setIsTransferOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" isLoading={isLoadingAction}>
              Confirm Transfer
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
export default MembershipPage;
