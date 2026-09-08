import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { AuthProvider } from "@/lib/auth-context";
import { createClient } from "@/lib/supabase/server";
import { cookies } from "next/headers";
import { UserRole } from "@/lib/types";

export default async function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let initialRole: UserRole = "admin";
  let user = null;

  try {
    const cookieStore = await cookies();
    const cookieRole = cookieStore.get("govern_ai_role")?.value;
    if (cookieRole && ["admin", "agent_builder", "user"].includes(cookieRole)) {
      initialRole = cookieRole as UserRole;
    } else {
      const supabase = await createClient();
      const { data } = await supabase.auth.getUser();
      if (data.user) {
        user = data.user;
        const rawRole = (user.app_metadata?.role || user.user_metadata?.role || "user") as string;
        if (rawRole === "admin" || rawRole === "agent_builder" || rawRole === "user") {
          initialRole = rawRole;
        } else {
          initialRole = "user";
        }
      }
    }
  } catch {
    // Keep defaults
  }

  return (
    <AuthProvider initialRole={initialRole} initialUser={user}>
      <div className="flex min-h-screen bg-white dark:bg-[#0a0a0a] text-slate-900 dark:text-slate-100 transition-colors duration-300">
        <Sidebar />
        <div className="flex-1 flex flex-col relative min-w-0">
          <Header />
          <main className="flex-1 p-8 overflow-auto bg-white dark:bg-[#0a0a0a]">
            {children}
          </main>
        </div>
      </div>
    </AuthProvider>
  );
}
