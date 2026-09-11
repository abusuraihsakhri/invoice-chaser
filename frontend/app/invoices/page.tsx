"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { invoicesApi, clientsApi, intelligenceApi } from "@/lib/api";

interface Invoice {
  id: number;
  invoice_number: string;
  amount: number;
  currency: string;
  status: string;
  description: string;
  payment_url: string | null;
  risk_score: number;
  due_date: string;
  client: { id: number; name: string; email: string };
}

interface Client {
  id: number;
  name: string;
  email: string;
}

interface RiskData {
  invoice_id: number;
  risk_score: number;
  risk_tier: string;
  default_probability_pct: number;
  expected_delay_days: number;
  key_factors: string[];
  recommended_action: string;
  discount_incentive_suggested?: string;
}

export default function InvoicesPage() {
  const router = useRouter();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<string>("");

  // AI Risk modal
  const [selectedRisk, setSelectedRisk] = useState<RiskData | null>(null);
  const [loadingRisk, setLoadingRisk] = useState(false);

  // Form state
  const [clientId, setClientId] = useState<number | "">("");
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    loadData();
  }, [filter]);

  const loadData = async () => {
    try {
      const [invoicesRes, clientsRes] = await Promise.all([
        invoicesApi.list(filter || undefined),
        clientsApi.list(),
      ]);
      setInvoices(invoicesRes.data);
      setClients(clientsRes.data);
    } catch (err) {
      console.error("Failed to load:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await invoicesApi.create({
        client_id: clientId as number,
        amount: parseFloat(amount),
        currency,
        description: description || undefined,
        issued_date: new Date().toISOString().split("T")[0],
        due_date: dueDate,
      });
      setShowForm(false);
      setClientId("");
      setAmount("");
      setDescription("");
      setDueDate("");
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to create invoice");
    }
  };

  const markPaid = async (id: number) => {
    try {
      await invoicesApi.markPaid(id);
      loadData();
    } catch (err) {
      console.error("Failed to mark paid:", err);
    }
  };

  const handleDownloadPdf = async (invoice: Invoice) => {
    try {
      await invoicesApi.downloadPdf(invoice.id, invoice.invoice_number);
    } catch (err: any) {
      alert("Failed to download PDF: " + (err.message || "Unknown error"));
    }
  };

  const handleViewRisk = async (invoiceId: number) => {
    setLoadingRisk(true);
    try {
      const res = await intelligenceApi.getRisk(invoiceId);
      setSelectedRisk(res.data);
    } catch (err) {
      alert("Failed to load risk prediction");
    } finally {
      setLoadingRisk(false);
    }
  };

  const handleCopyPaymentLink = (url: string | null) => {
    if (!url) {
      alert("No payment URL available for this invoice");
      return;
    }
    navigator.clipboard.writeText(url);
    alert("Payment link copied to clipboard!");
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading invoices...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8">
      <Navbar />

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 px-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
            <p className="text-xs text-gray-500">Manage billing, automated reminders, and payment tracking.</p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <a
              href={invoicesApi.exportCsvUrl()}
              download
              className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 font-medium shadow-sm transition"
            >
              📥 Export CSV
            </a>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white shadow-sm"
            >
              <option value="">All Statuses</option>
              <option value="sent">Sent</option>
              <option value="overdue">Overdue</option>
              <option value="paid">Paid</option>
            </select>
            <button
              onClick={() => setShowForm(!showForm)}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 shadow-sm transition"
            >
              {showForm ? "Cancel" : "+ New Invoice"}
            </button>
          </div>
        </div>

        {/* AI Risk Modal */}
        {selectedRisk && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full p-6 border border-gray-100">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-xl">🧠</span>
                  <h2 className="text-lg font-bold text-gray-900">AI Default Risk Analysis</h2>
                </div>
                <button onClick={() => setSelectedRisk(null)} className="text-gray-400 hover:text-gray-600 text-xl">
                  &times;
                </button>
              </div>

              <div className="space-y-4 text-sm">
                <div className="flex justify-between items-center bg-gray-50 p-4 rounded-lg">
                  <div>
                    <p className="text-xs text-gray-500 uppercase tracking-wider">Default Risk Score</p>
                    <p className="text-2xl font-black text-gray-900">{selectedRisk.risk_score} / 100</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
                      selectedRisk.risk_tier === "severe"
                        ? "bg-red-100 text-red-700"
                        : selectedRisk.risk_tier === "high"
                        ? "bg-orange-100 text-orange-700"
                        : selectedRisk.risk_tier === "medium"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-green-100 text-green-700"
                    }`}
                  >
                    {selectedRisk.risk_tier} Risk
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500">Default Probability</p>
                    <p className="text-base font-bold text-gray-800">{selectedRisk.default_probability_pct}%</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-xs text-gray-500">Projected Delay</p>
                    <p className="text-base font-bold text-gray-800">+{selectedRisk.expected_delay_days} days</p>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-gray-700 mb-1">Key Factors Identified:</p>
                  <ul className="list-disc pl-5 text-xs text-gray-600 space-y-1">
                    {selectedRisk.key_factors.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-3.5 bg-indigo-50 text-indigo-900 rounded-lg border border-indigo-100">
                  <p className="text-xs font-semibold uppercase text-indigo-700 mb-1">Recommended Action</p>
                  <p className="text-xs leading-relaxed">{selectedRisk.recommended_action}</p>
                  {selectedRisk.discount_incentive_suggested && (
                    <p className="text-xs font-medium text-indigo-800 mt-2">
                      💡 {selectedRisk.discount_incentive_suggested}
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setSelectedRisk(null)}
                  className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Create Form */}
        {showForm && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Create & Schedule Invoice</h2>
            {clients.length === 0 ? (
              <p className="text-gray-500 text-sm">
                You need to <a href="/clients" className="text-indigo-600 underline">add a client</a> first.
              </p>
            ) : (
              <form onSubmit={handleCreate} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Client</label>
                  <select
                    required
                    value={clientId}
                    onChange={(e) => setClientId(Number(e.target.value))}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
                  >
                    <option value="">Select client...</option>
                    {clients.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name} ({c.email})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="col-span-2">
                    <label className="block text-xs font-medium text-gray-700">Amount</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="1500.00"
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Currency</label>
                    <select
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-2 py-2 text-sm bg-white"
                    >
                      <option value="USD">USD ($)</option>
                      <option value="EUR">EUR (€)</option>
                      <option value="GBP">GBP (£)</option>
                      <option value="CAD">CAD ($)</option>
                      <option value="AUD">AUD ($)</option>
                    </select>
                  </div>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-gray-700">Description</label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                    placeholder="e.g. Software engineering & mobile design services"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Due Date</label>
                  <input
                    type="date"
                    required
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div className="sm:col-span-2 pt-2">
                  <button
                    type="submit"
                    className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 shadow-sm transition"
                  >
                    Create Invoice & Auto-Schedule Reminders
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Invoices List / Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase">Invoice</th>
                  <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase">Client</th>
                  <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase">Amount</th>
                  <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase">Due Date</th>
                  <th className="px-6 py-3.5 text-left text-xs font-semibold text-gray-500 uppercase">Status & Risk</th>
                  <th className="px-6 py-3.5 text-right text-xs font-semibold text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {invoices.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500 text-sm">
                      No invoices found. Create your first invoice!
                    </td>
                  </tr>
                ) : (
                  invoices.map((invoice) => (
                    <tr key={invoice.id} className="hover:bg-gray-50/75 transition">
                      <td className="px-6 py-4 font-semibold text-gray-900 text-sm">{invoice.invoice_number}</td>
                      <td className="px-6 py-4 text-gray-600 text-sm">{invoice.client?.name}</td>
                      <td className="px-6 py-4 font-bold text-gray-900 text-sm">
                        ${Number(invoice.amount).toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-gray-600 text-sm">{invoice.due_date}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${
                              invoice.status === "paid"
                                ? "bg-green-100 text-green-700"
                                : invoice.status === "overdue"
                                ? "bg-red-100 text-red-700"
                                : "bg-blue-100 text-blue-700"
                            }`}
                          >
                            {invoice.status}
                          </span>
                          <button
                            onClick={() => handleViewRisk(invoice.id)}
                            className="text-xs text-indigo-600 hover:text-indigo-800 bg-indigo-50 px-2 py-0.5 rounded font-medium"
                            title="View AI Risk Score"
                          >
                            Risk: {invoice.risk_score ? `${Math.round(invoice.risk_score)}%` : "AI"}
                          </button>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right space-x-2 whitespace-nowrap">
                        <button
                          onClick={() => handleDownloadPdf(invoice)}
                          className="text-xs px-2.5 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded font-medium transition"
                          title="Download PDF"
                        >
                          📄 PDF
                        </button>
                        {invoice.payment_url && (
                          <button
                            onClick={() => handleCopyPaymentLink(invoice.payment_url)}
                            className="text-xs px-2.5 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded font-medium transition"
                            title="Copy Payment Link"
                          >
                            🔗 Pay Link
                          </button>
                        )}
                        {invoice.status !== "paid" && (
                          <button
                            onClick={() => markPaid(invoice.id)}
                            className="text-xs px-2.5 py-1 bg-green-50 hover:bg-green-100 text-green-700 rounded font-medium transition"
                          >
                            Mark Paid
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
