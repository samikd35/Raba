// types/auth.ts
export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  timezone: string;
  preferences: Record<string, any>;
  bio: string;
  website: string;
  location: string;
  roles: string[];
  tenant_id: string;
  tenant_type: string;
  can_skip_module: boolean | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  refreshToken?: string;
  user: User;
}

export interface RegisterCredentials {
  email: string;
  password: string;
  full_name: string;
  confirm_password: string;
}

export interface SessionResponse {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  token_type: string;
}

export interface LoginResponse {
  status: 'success';
  message: string;
  user: {
    id: string;
    email: string;
    email_verified: boolean;
    created_at: string;
    user_metadata?: {
      full_name?: string;
    };
  };
  session: SessionResponse;
}

export interface OrganizationLoginResponse {
  access_token: string;
  tenant_id: string;
  tenant_type: string;
  user_id: string;
  email: string;
  roles: string[];
}
