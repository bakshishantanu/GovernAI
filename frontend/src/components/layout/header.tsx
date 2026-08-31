"use client";

import { logout } from "@/app/auth/actions";
import { LogOut, User, Bell } from "lucide-react";

export function Header() {
  return (
    <header className="h-16 bg-slate-950/50 backdrop-blur-md border-b border-slate-800 flex items-center justify-between px-8 sticky top-0 z-10">
      <div className="flex items-center text-sm font-medium text-slate-400">
        <span className="bg-slate-900 px-2.5 py-1 rounded-md border border-slate-800">
          Organization: Default Org
        </span>
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 text-slate-400 hover:text-slate-200 transition-colors rounded-full hover:bg-slate-900">
          <Bell className="w-5 h-5" />
        </button>

        <div className="h-6 w-px bg-slate-800"></div>

        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end">
            <span className="text-sm font-semibold text-slate-200">Pranav Ladha</span>
            <span className="text-xs text-emerald-400">Admin</span>
          </div>
          <div className="w-9 h-9 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-500">
            <User className="w-5 h-5" />
          </div>
        </div>

        <form action={logout}>
          <button
            type="submit"
            className="p-2 text-slate-400 hover:text-red-400 transition-colors rounded-full hover:bg-red-500/10 ml-2"
            title="Log out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </form>
      </div>
    </header>
  );
}
