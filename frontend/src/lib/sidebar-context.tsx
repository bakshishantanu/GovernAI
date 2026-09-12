"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

/**
 * Whether the mobile nav drawer is open. Separate from the sidebar's own
 * desktop collapse-to-rail state (persisted in `sidebar.tsx` via
 * localStorage) — that one is a standing preference; this one is a
 * transient overlay that always starts closed and is never remembered
 * across visits, the same way every other app's mobile nav behaves.
 *
 * Lives in its own context because `Header` (which owns the hamburger
 * button) and `Sidebar` (which owns the drawer) are siblings under
 * `[role]/layout.tsx`, a server component that can't hold client state
 * itself.
 */
type SidebarContextValue = {
  mobileOpen: boolean;
  openMobile: () => void;
  closeMobile: () => void;
};

const SidebarContext = createContext<SidebarContextValue | null>(null);

export function SidebarProvider({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <SidebarContext.Provider
      value={{
        mobileOpen,
        openMobile: () => setMobileOpen(true),
        closeMobile: () => setMobileOpen(false),
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar(): SidebarContextValue {
  const ctx = useContext(SidebarContext);
  if (!ctx) throw new Error("useSidebar must be used within a SidebarProvider");
  return ctx;
}
