"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { dashboardApi, invoicesApi } from "@/lib/api";


interface DashboardStats {
  total_outstanding: number;
  total_overdue: number;
  overdue_count: number;
  invoices_sent: number;
  invoices_paid: number;
  reminders_sent: number;
  avg_days_to_payment: number | null;
}

interface Invoice {
  id: number;
  invoice_number: string;
  amount: number;
  status: string;
  due_date: string;
  client: { name: string; email: string };
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentInvoices, setRecentInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [statsRes, invoicesRes] = await Promise.all([
        dashboardApi.getStats(),
        invoicesApi.list(),
      ]);
      setStats(statsRes.data);
      setRecentInvoices((invoicesRes.data as Invoice[]).slice(0, 5));
    } catch (err) {
      console.error("Failed to load dashboard:", err);
    } finally {
      setLoading(false);
    }
  };

  const markPaid = async (id: number) => {
    try {
      await invoicesApi.markPaid(id);
      loadDashboard();
    } catch (err) {
      console.error("Failed to mark paid:", err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8">
      <Navbar />


      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Outstanding</p>
              <p className="text-2xl font-bold text-gray-900">
                ${stats.total_outstanding.toFixed(2)}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Overdue</p>
              <p className="text-2xl font-bold text-red-600">
                ${stats.total_overdue.toFixed(2)}
              </p>
              <p className="text-xs text-gray-400">{stats.overdue_count} invoices</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Reminders Sent</p>
              <p className="text-2xl font-bold text-gray-900">{stats.reminders_sent}</p>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <p className="text-sm text-gray-500">Avg Days to Pay</p>
              <p className="text-2xl font-bold text-gray-900">
                {stats.avg_days_to_payment ?? "N/A"}
              </p>
            </div>
          </div>
        )}

        {/* Recent Invoices */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b flex justify-between items-center">
            <h2 className="text-lg font-medium">Recent Invoices</h2>
            <a href="/invoices" className="text-indigo-600 text-sm hover:text-indigo-500">
              View all
            </a>
          </div>
          <div className="divide-y">
            {recentInvoices.length === 0 ? (
              <p className="p-6 text-gray-500 text-center">No invoices yet</p>
            ) : (
              recentInvoices.map((invoice) => (
                <div key={invoice.id} className="px-6 py-4 flex justify-between items-center">
                  <div>
                    <p className="font-medium">{invoice.invoice_number}</p>
                    <p className="text-sm text-gray-500">{invoice.client.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">${invoice.amount.toFixed(2)}</p>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        invoice.status === "paid"
                          ? "bg-green-100 text-green-700"
                          : invoice.status === "overdue"
                          ? "bg-red-100 text-red-700"
                          : "bg-blue-100 text-blue-700"
                      }`}
                    >
                      {invoice.status}
                    </span>
                  </div>
                  {invoice.status !== "paid" && (
                    <button
                      onClick={() => markPaid(invoice.id)}
                      className="ml-4 text-sm text-green-600 hover:text-green-700"
                    >
                      Mark Paid
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
