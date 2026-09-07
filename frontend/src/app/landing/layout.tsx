import type { ReactNode } from "react";
import { archivoBlack, interLanding, caveat } from "@/lib/landing-fonts";

export default function LandingLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`${archivoBlack.variable} ${interLanding.variable} ${caveat.variable}`}
    >
      {children}
    </div>
  );
}
