import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { RouteTransition } from "@/components/route-transition";

const inter = Inter({ subsets: ["latin"] });

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
      <body className={inter.className}>
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
