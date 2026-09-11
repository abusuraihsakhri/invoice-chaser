"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { dashboardApi } from "@/lib/api";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [online, setOnline] = useState<boolean | null>(null);
  const [latency, setLatency] = useState<number | null>(null);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const data = await dashboardApi.getHealth();
      if (data && data.status === "healthy") {
        setOnline(true);
        setLatency(data.latencyMs || 25);
      } else {
        setOnline(false);
      }
    } catch {
      setOnline(false);
      setLatency(null);
    }
  };

  const navItems = [
    { label: "Dashboard", href: "/" },
    { label: "Invoices", href: "/invoices" },
    { label: "Clients", href: "/clients" },
    { label: "Reminders", href: "/reminders" },
    { label: "Settings", href: "/settings" },
  ];

  return (
    <>
      {/* Desktop Top Navbar */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
                ⚡
              </div>
              <Link href="/" className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent">
                Invoice Chaser
              </Link>
              {online !== null && (
                <span
                  title={online ? `API Online (${latency}ms)` : "API Offline - check Settings"}
                  className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    online ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${online ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
                  {online ? `${latency}ms` : "Offline"}
                </span>
              )}
            </div>

            {/* Desktop Navigation Links */}
            <div className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
              <div className="h-6 w-px bg-gray-200 mx-2" />
              <button
                onClick={() => {
                  localStorage.removeItem("token");
                  router.push("/login");
                }}
                className="text-gray-500 hover:text-gray-900 px-3 py-2 text-sm font-medium rounded-md hover:bg-gray-50"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Mobile Bottom Navigation Bar (Optimized for Android phones & touch screens) */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 safe-area-bottom pb-safe">
        <div className="grid grid-cols-5 h-16 items-center">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center justify-center py-1 text-xs font-medium ${
                  isActive ? "text-indigo-600 font-semibold" : "text-gray-500 hover:text-gray-900"
                }`}
              >
                <span className="text-lg mb-0.5">
                  {item.label === "Dashboard" && "📊"}
                  {item.label === "Invoices" && "📄"}
                  {item.label === "Clients" && "👥"}
                  {item.label === "Reminders" && "🔔"}
                  {item.label === "Settings" && "⚙️"}
                </span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </>
  );
}
