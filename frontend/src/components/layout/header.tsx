"use client";

import { logout } from "@/app/auth/actions";
import { LogOut, User, Bell, ShieldCheck } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth-context";
import { UserRole } from "@/lib/types";

export function Header() {
  const { role, userName, switchRole } = useAuth();

  const getRoleBadge = (r: UserRole) => {
    switch (r) {
      case "admin":
        return "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20";
      case "agent_builder":
        return "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20";
      case "user":
        return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
    }
  };

  const getRoleLabel = (r: UserRole) => {
    switch (r) {
      case "admin":
        return "Admin";
      case "agent_builder":
        return "Agent Builder";
      case "user":
        return "User";
    }
  };

  return (
    <header className="h-14 bg-white dark:bg-[#0a0a0a] border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6 sticky top-0 z-10 transition-colors duration-300">
      <div className="flex items-center gap-3">
        <div className="flex items-center text-sm font-medium text-slate-600 dark:text-slate-400">
          <span className="bg-slate-100 dark:bg-slate-900 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-800 text-xs">
            Org: Default Org
          </span>
        </div>

        {/* Role Simulator / Quick Switcher */}
        <div className="hidden sm:flex items-center bg-slate-100 dark:bg-slate-900/80 rounded-lg p-0.5 border border-slate-200 dark:border-slate-800 text-xs">
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 px-2 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-slate-400" />
            Role:
          </span>
          {(["admin", "agent_builder", "user"] as UserRole[]).map((r) => {
            const isActive = role === r;
            return (
              <button
                key={r}
                type="button"
                onClick={() => switchRole(r)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                  isActive
                    ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-sm font-semibold"
                    : "text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
                }`}
              >
                {getRoleLabel(r)}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        
        <button className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors rounded-md hover:bg-slate-100 dark:hover:bg-slate-800">
          <Bell className="w-4 h-4" />
        </button>

        <div className="h-4 w-px bg-slate-200 dark:border-slate-800 mx-2"></div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium text-slate-900 dark:text-slate-200">{userName}</span>
            <span className={`text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 border rounded ${getRoleBadge(role)}`}>
              {getRoleLabel(role)}
            </span>
          </div>
          <div className="w-8 h-8 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-600 dark:text-slate-400">
            <User className="w-4 h-4" />
          </div>
        </div>

        <form action={logout}>
          <button
            type="submit"
            className="p-2 text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors rounded-md hover:bg-red-50 dark:hover:bg-red-500/10 ml-2"
            title="Log out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </form>
      </div>
    </header>
  );
}
