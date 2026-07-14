import React, { useState, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { useForm } from 'react-hook-form';
import { Building, Settings2, Trash2, Plus, Calendar, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import { cn } from '@/utils/cn';
import { COUNTRIES } from '@/constants/countries';

export const CompanyPage: React.FC = () => {
  const { companies, activeCompanyId, switchCompany, fetchUserAndCompanies } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  // Memoize country options for the dropdown
  const countryOptions = useMemo(() => 
    COUNTRIES.map(country => ({
      value: country.code,
      label: `${country.code} - ${country.name}`
    })),
    []
  );
  
  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);

  // Forms
  const { register: createReg, handleSubmit: handleCreateSub, reset: resetCreate, formState: { errors: createErrors } } = useForm();
  const { register: editReg, handleSubmit: handleEditSub, setValue: setEditValue, formState: { errors: editErrors } } = useForm();

  const onCreateSubmit = async (data: any) => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/companies', {
        name: data.name,
        slug: data.slug || undefined,
        description: data.description || '',
        website: data.website || '',
        industry: data.industry || '',
        timezone: data.timezone || 'UTC',
        country: data.country || '',
      });
      toast.success('Workspace created successfully!');
      await fetchUserAndCompanies();
      const newCompanyId = response.data.data.company_id;
      if (newCompanyId) {
        await switchCompany(newCompanyId);
      }
      setIsCreateOpen(false);
      resetCreate();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to create workspace.');
    } finally {
      setIsLoading(false);
    }
  };

  const openSettings = async (companyId: string) => {
    setSelectedCompanyId(companyId);
    setIsLoading(true);
    try {
      const response = await apiClient.get(`/companies/${companyId}`);
      const details = response.data.data;
      setEditValue('name', details.name);
      setEditValue('slug', details.slug);
      setEditValue('description', details.description || '');
      setEditValue('website', details.website || '');
      setEditValue('industry', details.industry || '');
      setEditValue('timezone', details.timezone || 'UTC');
      setEditValue('country', details.country || '');
      setIsSettingsOpen(true);
    } catch (err: any) {
      console.error(err);
      toast.error('Failed to retrieve workspace details.');
    } finally {
      setIsLoading(false);
    }
  };

  const onEditSubmit = async (data: any) => {
    if (!selectedCompanyId) return;
    setIsLoading(true);
    try {
      await apiClient.put(`/companies/${selectedCompanyId}`, {
        name: data.name,
        slug: data.slug || undefined,
        description: data.description || '',
        website: data.website || '',
        industry: data.industry || '',
        timezone: data.timezone || 'UTC',
        country: data.country || '',
      });
      toast.success('Workspace updated successfully!');
      await fetchUserAndCompanies();
      setIsSettingsOpen(false);
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to update workspace.');
    } finally {
      setIsLoading(false);
    }
  };

  const onDeleteCompany = async () => {
    if (!selectedCompanyId) return;
    if (!confirm('WARNING: Are you sure you want to delete this workspace? This will logically archive the company and revoke all active memberships.')) return;
    setIsLoading(true);
    try {
      await apiClient.delete(`/companies/${selectedCompanyId}`);
      toast.success('Workspace deleted successfully.');
      await fetchUserAndCompanies();
      setIsSettingsOpen(false);
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to delete workspace.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Workspaces</h1>
          <p className="text-muted-foreground text-sm">
            Configure, manage, and switch between your tenant company workspaces.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="flex items-center gap-1.5">
          <Plus className="h-4 w-4" /> Create Workspace
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {companies.map((co) => {
          const isActive = co.company_id === activeCompanyId;
          return (
            <Card key={co.company_id} className={cn("hover:border-primary/25 transition-all flex flex-col justify-between", {
              "border-primary shadow-sm shadow-primary/5 bg-primary/5 dark:bg-primary/5": isActive,
            })}>
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base flex items-center gap-1.5 font-bold">
                      <Building className="h-4.5 w-4.5 text-muted-foreground" /> {co.name}
                    </CardTitle>
                    <CardDescription className="font-mono text-xs text-muted-foreground/80">
                      /{co.slug}
                    </CardDescription>
                  </div>
                  {isActive && (
                    <span className="text-xs bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-full font-medium">
                      Active
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="pb-4 space-y-3">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Calendar className="h-3.5 w-3.5" />
                  <span>Created: {new Date(co.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Shield className="h-3.5 w-3.5" />
                  <span>Status: <span className="capitalize font-semibold text-foreground">{co.status}</span></span>
                </div>
              </CardContent>
              <CardFooter className="flex items-center gap-2">
                {!isActive ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 text-xs"
                    onClick={() => switchCompany(co.company_id)}
                  >
                    Switch Workspace
                  </Button>
                ) : (
                  <div className="flex-1 text-xs text-center text-primary font-medium bg-primary/10 py-2 rounded-lg border border-primary/20">
                    Selected Workspace
                  </div>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="shrink-0 border border-border bg-background"
                  onClick={() => openSettings(co.company_id)}
                >
                  <Settings2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              </CardFooter>
            </Card>
          );
        })}
      </div>

      {/* Modal: Create Company */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Create New Workspace">
        <form onSubmit={handleCreateSub(onCreateSubmit)} className="space-y-4">
          <Input
            label="Workspace Name"
            placeholder="Acme Corp"
            error={createErrors.name?.message as string}
            {...createReg('name', { required: 'Workspace name is required' })}
          />

          <Input
            label="Workspace URL Slug (Optional)"
            placeholder="acme-corp"
            helperText="Custom lowercase identifier for your widget dashboard links. Auto-generated on empty."
            error={createErrors.slug?.message as string}
            {...createReg('slug', {
              pattern: {
                value: /^[a-z0-9-]+$/,
                message: 'Slug can only contain lowercase letters, numbers, and dashes',
              },
            })}
          />

          <Input
            label="Website URL"
            placeholder="https://acme.com"
            error={createErrors.website?.message as string}
            {...createReg('website')}
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Industry"
              placeholder="SaaS / FinTech"
              {...createReg('industry')}
            />
            <Select
              label="Country"
              options={countryOptions}
              error={createErrors.country?.message as string}
              {...createReg('country', { required: 'Country is required' })}
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description
            </label>
            <textarea
              placeholder="Provide a brief summary of the workspace tenant..."
              className="flex min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              {...createReg('description')}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button variant="outline" type="button" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoading}>
              Create
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Company Settings */}
      <Modal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} title="Workspace Settings" size="lg">
        <form onSubmit={handleEditSub(onEditSubmit)} className="space-y-4">
          <Input
            label="Workspace Name"
            placeholder="Acme Corp"
            error={editErrors.name?.message as string}
            {...editReg('name', { required: 'Workspace name is required' })}
          />

          <Input
            label="Workspace URL Slug"
            placeholder="acme-corp"
            error={editErrors.slug?.message as string}
            {...editReg('slug', {
              required: 'Slug is required',
              pattern: {
                value: /^[a-z0-9-]+$/,
                message: 'Slug can only contain lowercase letters, numbers, and dashes',
              },
            })}
          />

          <Input
            label="Website URL"
            placeholder="https://acme.com"
            error={editErrors.website?.message as string}
            {...editReg('website')}
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Industry"
              placeholder="SaaS / FinTech"
              {...editReg('industry')}
            />
            <Select
              label="Country"
              options={countryOptions}
              error={editErrors.country?.message as string}
              {...editReg('country', { required: 'Country is required' })}
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description
            </label>
            <textarea
              placeholder="Provide a brief summary of the workspace tenant..."
              className="flex min-h-20 w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              {...editReg('description')}
            />
          </div>

          <div className="flex items-center justify-between pt-6 border-t border-border/40">
            <Button
              variant="destructive"
              type="button"
              className="flex items-center gap-1.5"
              onClick={onDeleteCompany}
              isLoading={isLoading}
            >
              <Trash2 className="h-4 w-4" /> Archive Workspace
            </Button>
            <div className="flex gap-3">
              <Button variant="outline" type="button" onClick={() => setIsSettingsOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" isLoading={isLoading}>
                Save Changes
              </Button>
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
};
export default CompanyPage;
