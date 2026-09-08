"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { UserRole } from "./types";
import { createClient } from "./supabase/client";

interface AuthContextType {
  role: UserRole;
  user: any | null;
  userEmail: string | null;
  userName: string | null;
  switchRole: (newRole: UserRole) => void;
  isAdmin: boolean;
  isBuilder: boolean;
  isUser: boolean;
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
  const [role, setRoleState] = useState<UserRole>(() => {
    if (typeof window !== "undefined") {
      const savedRole = localStorage.getItem("govern_ai_role") as UserRole | null;
      if (savedRole && ["admin", "agent_builder", "user"].includes(savedRole)) {
        return savedRole;
      }
    }
    return initialRole;
  });
  const [user, setUser] = useState<any | null>(initialUser);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const supabase = createClient();
    supabase.auth.getUser().then(({ data: { user: supaUser } }) => {
      if (supaUser) {
        setUser(supaUser);
        const savedRole = localStorage.getItem("govern_ai_role") as UserRole | null;
        if (!savedRole) {
          const rawRole = (supaUser.app_metadata?.role || supaUser.user_metadata?.role || "user") as string;
          if (rawRole === "admin" || rawRole === "agent_builder" || rawRole === "user") {
            setRoleState(rawRole);
          } else {
            setRoleState("user");
          }
        }
      }
      setIsLoaded(true);
    }).catch(() => {
      setIsLoaded(true);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser(session.user);
        const currentSaved = localStorage.getItem("govern_ai_role") as UserRole | null;
        if (!currentSaved) {
          const rawRole = (session.user.app_metadata?.role || session.user.user_metadata?.role || "user") as string;
          if (rawRole === "admin" || rawRole === "agent_builder" || rawRole === "user") {
            setRoleState(rawRole);
          } else {
            setRoleState("user");
          }
        }
      } else {
        setUser(null);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const switchRole = (newRole: UserRole) => {
    setRoleState(newRole);
    localStorage.setItem("govern_ai_role", newRole);
    document.cookie = `govern_ai_role=${newRole}; path=/; max-age=31536000; SameSite=Lax`;
    window.dispatchEvent(new CustomEvent("govern-ai-role-change", { detail: newRole }));
  };

  const userEmail = user?.email || (role === "admin" ? "admin@govern.ai" : role === "agent_builder" ? "builder@govern.ai" : "user@govern.ai");
  const userName = user?.user_metadata?.full_name || (role === "admin" ? "Admin Operator" : role === "agent_builder" ? "Lead Builder" : "Standard User");

  const value: AuthContextType = {
    role,
    user,
    userEmail,
    userName,
    switchRole,
    isAdmin: role === "admin",
    isBuilder: role === "agent_builder" || role === "admin",
    isUser: role === "user",
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
