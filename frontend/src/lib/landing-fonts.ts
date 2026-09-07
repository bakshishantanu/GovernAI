import { Archivo_Black, Inter, Caveat } from "next/font/google";

export const archivoBlack = Archivo_Black({
  subsets: ["latin"],
  weight: "400",
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
