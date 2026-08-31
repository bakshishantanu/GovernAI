import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";

export default function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-white dark:bg-[#0a0a0a] text-slate-900 dark:text-slate-100 transition-colors duration-300">
      <Sidebar />
      <div className="flex-1 flex flex-col relative">
        <Header />
        <main className="flex-1 p-8 overflow-auto bg-white dark:bg-[#0a0a0a]">
          {children}
        </main>
      </div>
    </div>
  );
}
