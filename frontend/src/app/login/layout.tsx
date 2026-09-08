import type { ReactNode } from "react";
import { kecal, interLanding, caveat } from "@/lib/landing-fonts";
import "../landing/landing.css";

export default function LoginLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`landing ${kecal.variable} ${interLanding.variable} ${caveat.variable}`}
    >
      {children}
    </div>
  );
}
