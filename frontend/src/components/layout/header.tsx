"use client";

import { logout } from "@/app/auth/actions";
import { LogOut, User, Bell } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

export function Header() {
  return (
    <header className="h-14 bg-white dark:bg-[#0a0a0a] border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6 sticky top-0 z-10 transition-colors duration-300">
      <div className="flex items-center text-sm font-medium text-slate-600 dark:text-slate-400">
        <span className="bg-slate-100 dark:bg-slate-900 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-800">
          Organization: Default Org
        </span>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        
        <button className="p-2 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors rounded-md hover:bg-slate-100 dark:hover:bg-slate-800">
          <Bell className="w-4 h-4" />
        </button>

        <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 mx-2"></div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-sm font-medium text-slate-900 dark:text-slate-200">Pranav Ladha</span>
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 dark:text-slate-500">Admin</span>
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
