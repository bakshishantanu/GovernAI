import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { RouteTransition } from "@/components/route-transition";
import { archivoBlack, interLanding, caveat } from "@/lib/landing-fonts";

export const metadata: Metadata = {
  title: "GovernAI Enterprise",
  description: "Enterprise agent governance platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      {/*
        Fonts load here (root), not per-section, so the app shell and every
        screen share the same Archivo Black / Inter / Caveat vocabulary as
        the landing pages (D-038) without re-declaring them. The landing
        route group still applies these classes itself too; harmless —
        next/font dedupes by variable name, not by call site.
      */}
      <body className={`${archivoBlack.variable} ${interLanding.variable} ${caveat.variable}`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <RouteTransition />
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
