"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserRole } from "./types";
import { createClient } from "./supabase/client";

interface AuthContextType {
  role: UserRole;
  user: any | null;
  userEmail: string | null;
  userName: string | null;
  isAdmin: boolean;
  isAgentBuilder: boolean;
  isLoaded: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({
  children,
  initialRole = "admin",
  initialUser = null,
}: {
  children: React.ReactNode;
  initialRole?: UserRole;
  initialUser?: any | null;
}) {
  // The role is decided server-side (see `[role]/layout.tsx`), purely from
  // the signed-in account's own email — there is no manual switch anymore.
  // Registering/signing in with an email on the admin list lands on the
  // admin console; every other email lands on the user console.
  const [role] = useState<UserRole>(initialRole);
  const [user, setUser] = useState<any | null>(initialUser);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user: supaUser } }) => {
      if (supaUser) setUser(supaUser);
      setIsLoaded(true);
    }).catch(() => {
      setIsLoaded(true);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const userEmail = user?.email || (role === "admin" ? "admin@govern.ai" : "user@govern.ai");
  const userName = user?.user_metadata?.full_name || (role === "admin" ? "Admin Operator" : "Standard User");

  const value: AuthContextType = {
    role,
    user,
    userEmail,
    userName,
    isAdmin: role === "admin",
    isAgentBuilder: role === "agent_builder",
    isLoaded,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
