import type { ReactNode } from "react";
import { Archivo_Black, Inter, Caveat } from "next/font/google";

const archivoBlack = Archivo_Black({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

const interLanding = Inter({
  subsets: ["latin"],
  variable: "--font-landing-body",
});

const caveat = Caveat({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-hand",
});

export default function LandingLayout({ children }: { children: ReactNode }) {
  return (
    <div
      className={`${archivoBlack.variable} ${interLanding.variable} ${caveat.variable}`}
    >
      {children}
    </div>
  );
}
