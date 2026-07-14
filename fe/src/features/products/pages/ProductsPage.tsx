import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { apiClient } from '@/services/apiClient';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { EmptyState } from '@/components/ui/EmptyState';
import { TableSkeleton } from '@/components/ui/Skeleton';
import { useForm } from 'react-hook-form';
import { ShoppingBag, Search, Plus, Trash2, Edit3, DollarSign, Barcode, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

interface Product {
  product_id: string;
  company_id: string;
  sku: string;
  name: string;
  description: string;
  price: number;
  url?: string;
  is_available: boolean;
  created_at: string;
}

export const ProductsPage: React.FC = () => {
  const { activeCompanyId } = useAuth();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoadingAction, setIsLoadingAction] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  // 1. Fetch Catalog (combines list & search)
  const { data: products = [], isLoading: isProductsLoading, error: productsError, refetch: refetchProducts } = useQuery({
    queryKey: ['products', activeCompanyId, searchQuery],
    queryFn: async () => {
      if (!activeCompanyId) return [];
      
      // If search query is present, use search route
      if (searchQuery.trim().length > 0) {
        const response = await apiClient.get(`/companies/${activeCompanyId}/products/search?q=${searchQuery}`);
        return response.data.data || [];
      }
      
      // Else use default list route
      const response = await apiClient.get(`/companies/${activeCompanyId}/products`);
      return response.data.data || [];
    },
    enabled: !!activeCompanyId,
  });

  // 2. Action: Register Product
  const onAddSubmit = async (data: any) => {
    if (!activeCompanyId) return;
    setIsLoadingAction(true);
    try {
      await apiClient.post(`/companies/${activeCompanyId}/products`, {
        sku: data.sku,
        name: data.name,
        description: data.description,
        price: parseFloat(data.price),
        url: data.url || undefined,
        is_available: data.isAvailable === 'true' || data.isAvailable === true,
      });
      toast.success('Product successfully registered in catalog!');
      refetchProducts();
      setIsAddOpen(false);
      reset();
    } catch (err: any) {
      console.error(err);
      toast.error(err.response?.data?.error?.message || 'Failed to register product.');
    } finally {
      setIsLoadingAction(false);
    }
  };

  // 3. Action: Simulated Edit (toast warning)
  const handleSimulatedEdit = (productName: string) => {
    toast.error(
      `Edit product "${productName}" is not supported by the backend router. The action is simulated locally.`,
      { duration: 4000 }
    );
  };

  // 4. Action: Simulated Delete (toast warning)
  const handleSimulatedDelete = (productName: string) => {
    toast.error(
      `Delete product "${productName}" is not supported by the backend router. The action is simulated locally.`,
      { duration: 4000 }
    );
  };

  if (!activeCompanyId) {
    return (
      <EmptyState
        icon={ShoppingBag}
        title="No Company Selected"
        description="Select or create a company workspace to view and manage product catalogs."
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in-50 duration-200">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Product Catalog</h1>
          <p className="text-muted-foreground text-sm">
            Manage your inventory metadata which is matched during user query resolutions.
          </p>
        </div>
        <Button onClick={() => setIsAddOpen(true)} className="flex items-center gap-1.5 text-xs">
          <Plus className="h-4 w-4" /> Add Product
        </Button>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="relative max-w-md w-full">
        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search products by SKU, name, or description..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-card border border-border/80 rounded-lg pl-9 pr-4 py-2.5 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring transition-all"
        />
      </div>

      {/* Catalog Render */}
      {isProductsLoading ? (
        <TableSkeleton />
      ) : productsError ? (
        <div className="p-6 text-center text-destructive">
          Failed to load product catalog.
        </div>
      ) : products.length === 0 ? (
        <EmptyState
          icon={ShoppingBag}
          title="No Products Found"
          description={
            searchQuery
              ? `No products matched the search query "${searchQuery}".`
              : 'Your product catalog is empty. Register items to allow assistant referencing.'
          }
          actionText={searchQuery ? 'Clear Search' : 'Register Product'}
          onAction={searchQuery ? () => setSearchQuery('') : () => setIsAddOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((p: Product) => (
            <Card key={p.product_id} className="hover:border-primary/20 transition-all flex flex-col justify-between">
              <CardHeader className="pb-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <CardTitle className="text-base font-bold truncate max-w-[180px]">{p.name}</CardTitle>
                    <CardDescription className="font-mono text-xs flex items-center gap-1 text-muted-foreground/80">
                      <Barcode className="h-3 w-3" /> SKU: {p.sku}
                    </CardDescription>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                      p.is_available
                        ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                        : 'bg-destructive/10 text-destructive border-destructive/20'
                    }`}
                  >
                    {p.is_available ? 'Available' : 'Unavailable'}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-xs text-muted-foreground line-clamp-3 leading-relaxed min-h-[48px]">
                  {p.description}
                </p>
                <div className="flex items-center gap-1 text-base font-bold text-foreground">
                  <DollarSign className="h-4.5 w-4.5" />
                  <span>{p.price.toFixed(2)}</span>
                </div>
              </CardContent>
              <CardFooter className="flex justify-between items-center bg-muted/15 border-t border-border/40 p-4">
                {p.url ? (
                  <a
                    href={p.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-primary font-medium hover:underline flex items-center gap-1"
                  >
                    View Link <ExternalLink className="h-3 w-3" />
                  </a>
                ) : (
                  <span className="text-[10px] text-muted-foreground">No External Link</span>
                )}
                
                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 rounded-full border border-border/60 bg-background"
                    onClick={() => handleSimulatedEdit(p.name)}
                  >
                    <Edit3 className="h-3.5 w-3.5 text-muted-foreground" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 rounded-full border border-border/60 bg-background text-destructive hover:bg-destructive/5"
                    onClick={() => handleSimulatedDelete(p.name)}
                  >
                    <Trash2 className="h-3.5 w-3.5 text-destructive/80" />
                  </Button>
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Modal: Add Product */}
      <Modal isOpen={isAddOpen} onClose={() => setIsAddOpen(false)} title="Register Catalog Product">
        <form onSubmit={handleSubmit(onAddSubmit)} className="space-y-4">
          <Input
            label="Product Name"
            placeholder="SuperWidget Pro"
            error={errors.name?.message as string}
            {...register('name', { required: 'Name is required' })}
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="SKU Identifier"
              placeholder="WID-PRO-001"
              error={errors.sku?.message as string}
              {...register('sku', { required: 'SKU is required' })}
            />
            <Input
              label="Price (USD)"
              type="number"
              step="0.01"
              placeholder="99.99"
              error={errors.price?.message as string}
              {...register('price', { required: 'Price is required' })}
            />
          </div>

          <Input
            label="External URL (Optional)"
            placeholder="https://acme.com/products/pro"
            error={errors.url?.message as string}
            {...register('url')}
          />

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Availability Status
            </label>
            <select
              {...register('isAvailable')}
              className="flex w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm placeholder:text-muted-foreground/60 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 transition-all"
            >
              <option value="true">In Stock & Available</option>
              <option value="false">Out of Stock & Unavailable</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Description
            </label>
            <textarea
              placeholder="Provide specifications, use cases, troubleshooting limits..."
              className="flex min-h-[80px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              {...register('description', { required: 'Description is required' })}
            />
            {errors.description && (
              <p className="text-xs text-destructive mt-1">Description is required</p>
            )}
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-border/40">
            <Button variant="outline" type="button" onClick={() => setIsAddOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoadingAction}>
              Register Product
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
export default ProductsPage;
