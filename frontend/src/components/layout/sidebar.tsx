"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Bot, 
  Puzzle, 
  Shield, 
  FileText, 
  DollarSign, 
  Settings 
} from "lucide-react";

const navItems = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Agents", href: "/agents", icon: Bot },
  { name: "Skills", href: "/skills", icon: Puzzle },
  { name: "Policies", href: "/policies", icon: Shield },
  { name: "Audit Log", href: "/audit", icon: FileText },
  { name: "Costs", href: "/costs", icon: DollarSign },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 bg-slate-50 dark:bg-[#0a0a0a] border-r border-slate-200 dark:border-slate-800 flex flex-col h-screen sticky top-0 transition-colors duration-300">
      <div className="h-14 flex items-center px-5 border-b border-slate-200 dark:border-slate-800">
        <Shield className="w-5 h-5 text-slate-900 dark:text-white mr-2" />
        <span className="text-md font-semibold text-slate-900 dark:text-slate-100 tracking-tight">GovernAI</span>
      </div>
      
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive
                  ? "bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-white"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-900"
              }`}
            >
              <item.icon className={`w-4 h-4 ${isActive ? "text-slate-900 dark:text-white" : "text-slate-500"}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-200 dark:border-slate-800">
        <div className="bg-white dark:bg-[#111] border border-slate-200 dark:border-slate-800 rounded-md p-3 text-xs">
          <p className="text-slate-700 dark:text-slate-300 font-semibold mb-0.5">Deloitte Capstone</p>
          <p className="text-slate-500 dark:text-slate-500">Team Fennec - MVP</p>
        </div>
      </div>
    </aside>
  );
}
