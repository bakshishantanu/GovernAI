import type { ReactNode } from "react";
import { archivoBlack, interLanding, caveat, fredoka } from "@/lib/landing-fonts";

export default function LandingLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`${archivoBlack.variable} ${interLanding.variable} ${caveat.variable} ${fredoka.variable}`}
    >
      {children}
    </div>
  );
}
