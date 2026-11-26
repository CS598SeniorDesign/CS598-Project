import "./globals.css";
import { ChatProvider } from "@/components/chat/ChatProvider";
import Navbar from "@/components/layout/Navbar";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "QuestLog",
  description: "Track and discover your favorite board games.",
};

const themeScript = `
  (function () {
    try {
      var theme = localStorage.getItem("questlog-theme");
      document.documentElement.dataset.theme =
        theme === "light" ? "light" : "dark";
    } catch {
      document.documentElement.dataset.theme = "dark";
    }
  })();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>

      <body className="min-h-screen bg-background text-foreground">
        <ThemeProvider>
          <ChatProvider>
            <Navbar />
            <main>{children}</main>
          </ChatProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
