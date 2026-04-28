export interface AuthUser {
  id: number;
  email: string;
  username: string;
  is_verified: boolean;
  tutorial_seen: boolean;
  is_admin: boolean;
  is_active: boolean;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}
