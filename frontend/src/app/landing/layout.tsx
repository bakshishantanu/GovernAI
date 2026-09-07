import type { ReactNode } from "react";
import { fredoka, interLanding, caveat } from "@/lib/landing-fonts";

export default function LandingLayout({ children }: { children: ReactNode }) {
  return (
    <div className={`${fredoka.variable} ${interLanding.variable} ${caveat.variable}`}>
      {children}
    </div>
  );
}
