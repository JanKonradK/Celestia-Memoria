export type UserRole = "controller" | "admin";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

export interface Session {
  user: User;
  access_token: string;
  expires_at: string;
}

export interface JwtPayload {
  sub: string;
  email: string;
  app_metadata: {
    role: UserRole;
  };
  iat: number;
  exp: number;
}
