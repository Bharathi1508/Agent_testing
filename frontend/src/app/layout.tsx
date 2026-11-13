
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HEAAP | Enterprise Agent Assurance",
  description:
    "Hybrid Enterprise Agent Assurance Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
