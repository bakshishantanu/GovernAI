import { Inter, Caveat, Fredoka } from "next/font/google";

// The reference site's real display face is a licensed font called
// "Champ" (bold, rounded, friendly) — not available to us. Fredoka is
// the closest freely-available match: rounded terminals, chunky but
// not razor-geometric like Archivo Black was.
export const fredoka = Fredoka({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
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
