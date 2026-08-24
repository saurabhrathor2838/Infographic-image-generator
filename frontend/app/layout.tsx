/* ==========================================================================
   AI Visual Generator — Root Layout
   ========================================================================== */

import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Visual Generator",
  description:
    "Generate infographic images and complex technical visuals using an agentic AI workflow.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
