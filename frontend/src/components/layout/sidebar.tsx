"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Bot, 
  Puzzle, 
  ShieldCheck, 
  FileText, 
  DollarSign, 
  Settings 
} from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Agents", href: "/agents", icon: Bot },
  { name: "Skills", href: "/skills", icon: Puzzle },
  { name: "Policies", href: "/policies", icon: ShieldCheck },
  { name: "Audit Log", href: "/audit", icon: FileText },
  { name: "Costs", href: "/costs", icon: DollarSign },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col h-screen sticky top-0">
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <ShieldCheck className="w-6 h-6 text-emerald-500 mr-2" />
        <span className="text-lg font-bold text-slate-100 tracking-tight">GovernAI</span>
      </div>
      
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-emerald-500/10 text-emerald-400"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <item.icon className={`w-5 h-5 ${isActive ? "text-emerald-400" : "text-slate-500"}`} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-800">
        <div className="bg-slate-900 rounded-xl p-4 text-xs">
          <p className="text-slate-300 font-semibold mb-1">Deloitte Capstone</p>
          <p className="text-slate-500">Team Fennec - MVP</p>
        </div>
      </div>
    </aside>
  );
}
