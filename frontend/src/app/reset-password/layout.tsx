import type { ReactNode } from "react";
import { kecal, interLanding, caveat } from "@/lib/landing-fonts";
import "../landing/landing.css";

/**
 * Same shell as `/login` (locked to light mode, same fonts) — this page is
 * reached straight from a password-reset email, before the user has any
 * reason to have set a theme preference, and it should look like the same
 * product as the sign-in screen it returns to.
 */
export default function ResetPasswordLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`landing landing-locked-light ${kecal.variable} ${interLanding.variable} ${caveat.variable}`}
    >
      {children}
    </div>
  );
}
