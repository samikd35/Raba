export type TenantSize = 'startup' | 'small' | 'medium' | 'enterprise' | string;

export interface TenantSettings {
  [key: string]: any;
}

export interface TenantCreateRequest {
  name: string;
  tenant_type: 'individual' | 'company' | string;
  description?: string;
  website?: string;
  industry?: string;
  size?: TenantSize;
  country?: string;
  settings?: TenantSettings;
}

export interface Tenant {
  id: string;
  name: string;
  tenant_type: string;
  description?: string;
  website?: string;
  industry?: string;
  size?: TenantSize;
  country?: string;
  settings?: TenantSettings;
  created_at?: string;
  updated_at?: string;
}

export interface TenantListResponse {
  tenants: Tenant[];
  total?: number;
}
