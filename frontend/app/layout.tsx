import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Autonomous Software Team // Control Center",
  description:
    "Autonomous Multi-Agent Software Team Orchestration Platform with Two-Tier Dynamic Routing, Deterministic Quality Gate, and Real-Time Reactive DAG Dashboard.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full flex flex-col bg-[#070b14] text-slate-100" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
