import { Archivo_Black, Inter, Caveat, Fredoka } from "next/font/google";

export const archivoBlack = Archivo_Black({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-display",
});

// A rounder, friendlier display face reserved for one-off playful
// moments (the sliding marquee statement) — distinct from Archivo
// Black's blocky geometric weight used for section headlines.
export const fredoka = Fredoka({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-marquee",
});

export const interLanding = Inter({
  subsets: ["latin"],
  variable: "--font-landing-body",
});

export const caveat = Caveat({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-hand",
});
