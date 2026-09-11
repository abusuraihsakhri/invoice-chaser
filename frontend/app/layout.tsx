import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Invoice Chaser",
  description: "Get paid faster with AI-powered payment reminders",
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
