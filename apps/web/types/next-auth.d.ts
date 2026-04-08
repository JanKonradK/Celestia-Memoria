import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  interface User {
    id: string;
    accessToken?: string;
    role?: string;
  }

  interface Session {
    user: {
      id: string;
      role: string;
    } & DefaultSession["user"];
    accessToken: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    accessToken: string;
    role: string;
  }
}
