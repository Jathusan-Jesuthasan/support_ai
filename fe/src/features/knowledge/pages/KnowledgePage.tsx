import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { EmptyState } from '@/components/ui/EmptyState';
import { useForm } from 'react-hook-form';
import {
  BookOpen,
  FileText,
  UploadCloud,
  Trash2,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Plus
} from 'lucide-react';
import toast from 'react-hot-toast';

interface KnowledgeSource {
  knowledge_id: string;
  company_id: string;
  name: string;
  description?: string;
  source_type: string;
  file_name?: string;
  file_size?: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  error_message?: string;
  created_at: string;
}

export const KnowledgePage: React.FC = () => {
  const { activeCompanyId } = useAuth();
  const [isLoadingAction, setIsLoadingAction] = useState(false);
  
  // Create / Upload states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedSourceForUpload, setSelectedSourceForUpload] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  // 1. Fetch Knowledge Sources
  const { data: sources = [], isLoading: isSourcesLoading, error: sourcesError, refetch: refetchSources } = useQuery({
    queryKey: ['knowledge', activeCompanyId],
    queryFn: async () => {
      if (!activeCompanyId) return [];
      const response = await apiClient.get(`/companies/${activeCompanyId}/knowledge`);
      return response.data.data || [];
    },
    enabled: !!activeCompanyId,
  });

  // Polling logic for pending or processing files
  useEffect(() => {
    const hasActiveJobs = sources.some(
      (s: KnowledgeSource) => s.status === 'PENDING' || s.status === 'PROCESSING'
    );

    if (hasActiveJobs) {
      const interval = setInterval(() => {
        refetchSources();
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [sources, refetchSources]);

  // 2. Action: Register Source Reference
  const onCreateSubmit = async (data: any) => {
    if (!activeCompanyId) return;
    setIsLoadingAction(true);
    try {
      const response = await apiClient.post(`/companies/${activeCompanyId}/knowledge`, {
        name: data.name,
        description: data.description || '',
        source_type: 'FILE_UPLOAD', // Static value matching router expectation
      });
      toast.success('Knowledge source registered. Proceed to upload.');
      refetchSources();
      
      // Auto open upload overlay
      const registeredId = response.data.data.knowledge_id;
      setSelectedSourceForUpload(registeredId);
      
      setIsCreateOpen(false);
      reset();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to register source.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 3. Action: Upload File
  const handleUploadFile = async () => {
    if (!activeCompanyId || !selectedSourceForUpload || !selectedFile) {
      toast.error('Please choose a file first.');
      return;
    }

    setIsLoadingAction(true);
    setUploadProgress(10); // Start progress bar

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      setUploadProgress(40);
      await apiClient.post(
        `/companies/${activeCompanyId}/knowledge/${selectedSourceForUpload}/upload`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      setUploadProgress(100);
      toast.success('File uploaded successfully! Background indexing has started.');
      refetchSources();
      setTimeout(() => {
        setSelectedSourceForUpload(null);
        setSelectedFile(null);
        setUploadProgress(0);
      }, 500);
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'File upload failed. Ensure file size and types match rules.');
      setUploadProgress(0);
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 4. Action: Delete Knowledge Source
  const onDeleteSource = async (knowledgeId: string) => {
    if (!activeCompanyId) return;
    if (!confirm('Are you sure you want to delete this source? This will wipe the source record and all its vectorized embeddings.')) return;
    
    setIsLoadingAction(true);
    try {
      await apiClient.delete(`/companies/${activeCompanyId}/knowledge/${knowledgeId}`);
      toast.success('Source deleted successfully.');
      refetchSources();
    } catch (err: any) {
      console.error(err);
      toast.error('Failed to delete source.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  if (!activeCompanyId) {
    return (
      <EmptyState
        icon={BookOpen}
        title="No Company Selected"
        description="Select or create a company workspace to manage the knowledge base."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Knowledge Base</h1>
          <p className="text-muted-foreground text-sm">
            Ingest unstructured documents (PDF, DOCX, TXT) to ground RAG completions.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="flex items-center gap-1.5 text-xs">
          <Plus className="h-4 w-4" /> Add Source Reference
        </Button>
      </div>

      {isSourcesLoading ? (
        <TableSkeleton />
      ) : sourcesError ? (
        <div className="p-6 text-center text-destructive">
          Failed to load knowledge sources.
        </div>
      ) : sources.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No Knowledge Sources"
          description="Ground your generative answers by uploading manual text documents, product specifications, or FAQ sheets."
          actionText="Add Source Reference"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-in fade-in-50 duration-200">
          {sources.map((s: KnowledgeSource) => {
            const hasFile = !!s.file_name;
            return (
              <Card key={s.knowledge_id} className="hover:border-primary/20 transition-all flex flex-col justify-between">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-base font-bold flex items-center gap-2">
                        <FileText className="h-4.5 w-4.5 text-muted-foreground" /> {s.name}
                      </CardTitle>
                      {s.description && (
                        <CardDescription className="text-xs">{s.description}</CardDescription>
                      )}
                    </div>

                    {/* Status Pill */}
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                        s.status === 'COMPLETED'
                          ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                          : s.status === 'FAILED'
                          ? 'bg-destructive/10 text-destructive border-destructive/20'
                          : 'bg-amber-500/10 text-amber-500 border-amber-500/20 animate-pulse-slow'
                      }`}
                    >
                      {s.status === 'PROCESSING' && (
                        <RefreshCw className="h-3 w-3 animate-spin" />
                      )}
                      {s.status === 'COMPLETED' && <CheckCircle className="h-3 w-3" />}
                      {s.status === 'FAILED' && <AlertTriangle className="h-3 w-3" />}
                      {s.status}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {hasFile ? (
                    <div className="p-3.5 bg-muted/20 border border-border/40 rounded-lg flex items-center justify-between">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-foreground truncate">
                          {s.file_name}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          {s.file_size ? `${(s.file_size / 1024).toFixed(1)} KB` : 'Unknown size'}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 border border-dashed border-border/80 rounded-lg text-center bg-muted/10">
                      <p className="text-xs text-muted-foreground mb-3">No document file uploaded yet.</p>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-xs"
                        onClick={() => setSelectedSourceForUpload(s.knowledge_id)}
                      >
                        Upload Document
                      </Button>
                    </div>
                  )}

                  {s.error_message && (
                    <p className="text-xs text-destructive bg-destructive/5 p-2 rounded border border-destructive/15">
                      <strong>Parsing Error:</strong> {s.error_message}
                    </p>
                  )}
                </CardContent>
                <CardFooter className="flex justify-between items-center bg-muted/15 border-t border-border/40 p-4">
                  <span className="text-[10px] text-muted-foreground">
                    Added: {new Date(s.created_at).toLocaleDateString()}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive border border-transparent rounded-full h-8 w-8"
                    onClick={() => onDeleteSource(s.knowledge_id)}
                    disabled={isLoadingAction}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Modal: Create Knowledge Source */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Register Knowledge Source">
        <form onSubmit={handleSubmit(onCreateSubmit)} className="space-y-4">
          <Input
            label="Source Name"
            placeholder="User Policy Manual v1.2"
            error={errors.name?.message as string}
            {...register('name', { required: 'Name is required' })}
          />

          <div className="space-y-1">
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description
            </label>
            <textarea
              placeholder="What facts or guidelines does this document provide?"
              className="flex min-h-[80px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              {...register('description')}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button variant="outline" type="button" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoadingAction}>
              Register & Continue
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal: Upload File Trigger */}
      <Modal
        isOpen={!!selectedSourceForUpload}
        onClose={() => setSelectedSourceForUpload(null)}
        title="Upload Document File"
      >
        <div className="space-y-6">
          <div className="border-2 border-dashed border-border/80 hover:border-primary/50 transition-colors p-8 rounded-xl text-center bg-muted/10 relative">
            <input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center gap-3">
              <UploadCloud className="h-10 w-10 text-muted-foreground" />
              <div>
                <p className="text-sm font-semibold">
                  {selectedFile ? selectedFile.name : 'Click or Drag file to upload'}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Supported formats: PDF, DOCX, TXT, MD (Max 10MB)
                </p>
              </div>
            </div>
          </div>

          {uploadProgress > 0 && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-medium">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2.5">
                <div
                  className="bg-primary h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button
              variant="outline"
              type="button"
              onClick={() => setSelectedSourceForUpload(null)}
              disabled={isLoadingAction}
            >
              Cancel
            </Button>
            <Button
              onClick={handleUploadFile}
              isLoading={isLoadingAction}
              disabled={!selectedFile}
            >
              Submit Upload
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
export default KnowledgePage;
