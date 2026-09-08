import type { ReactNode } from "react";
import { kecal, interLanding, caveat } from "@/lib/landing-fonts";

export default function LandingLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`${kecal.variable} ${interLanding.variable} ${caveat.variable}`}
    >
      {children}
    </div>
  );
}
