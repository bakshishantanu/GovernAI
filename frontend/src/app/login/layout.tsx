import type { ReactNode } from "react";
import { archivoBlack, interLanding, caveat } from "@/lib/landing-fonts";
import "../landing/landing.css";

export default function LoginLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`landing ${archivoBlack.variable} ${interLanding.variable} ${caveat.variable}`}
    >
      {children}
    </div>
  );
}
