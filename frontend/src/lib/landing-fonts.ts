import { Inter, Caveat } from "next/font/google";
import localFont from "next/font/local";

/**
 * Kecal (FungiType, SIL OFL 1.1) — https://github.com/FungiType/Kecal.
 * A variable font (weight axis 200-800); `.landing-display` in landing.css
 * sets an explicit font-weight since nothing here pins one, unlike the
 * single-weight Archivo Black this replaced.
 */
export const kecal = localFont({
  src: "../fonts/Kecal-variable-web.woff2",
  weight: "200 800",
  display: "swap",
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
