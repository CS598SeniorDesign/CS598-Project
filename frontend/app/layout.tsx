import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "QuestLog",
  description: "Track and discover your favorite board games.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background text-white">
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
