"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { clientsApi } from "@/lib/api";

interface Client {
  id: number;
  name: string;
  email: string;
  company: string | null;
  phone: string | null;
  notes: string | null;
  risk_score: number;
  risk_tier: string;
}

export default function ClientsPage() {
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    loadClients();
  }, []);

  const loadClients = async () => {
    try {
      const res = await clientsApi.list();
      setClients(res.data);
    } catch (err) {
      console.error("Failed to load clients:", err);
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setName("");
    setEmail("");
    setCompany("");
    setPhone("");
    setNotes("");
    setEditing(null);
    setShowForm(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editing) {
        await clientsApi.update(editing.id, {
          name,
          email,
          company: company || undefined,
          phone: phone || undefined,
          notes: notes || undefined,
        });
      } else {
        await clientsApi.create({
          name,
          email,
          company: company || undefined,
          phone: phone || undefined,
          notes: notes || undefined,
        });
      }
      resetForm();
      loadClients();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to save client");
    }
  };

  const handleEdit = (client: Client) => {
    setEditing(client);
    setName(client.name);
    setEmail(client.email);
    setCompany(client.company || "");
    setPhone(client.phone || "");
    setNotes(client.notes || "");
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this client? This will also delete all their invoices.")) return;
    try {
      await clientsApi.delete(id);
      loadClients();
    } catch (err) {
      console.error("Failed to delete:", err);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading clients...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8">
      <Navbar />

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 px-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
            <p className="text-xs text-gray-500">Manage client contacts, payment risk profiles, and communication notes.</p>
          </div>
          <div className="flex items-center gap-3">
            <a
              href={clientsApi.exportCsvUrl()}
              download
              className="px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm text-gray-700 hover:bg-gray-50 font-medium shadow-sm transition"
            >
              📥 Export CSV
            </a>
            <button
              onClick={() => {
                resetForm();
                setShowForm(!showForm);
              }}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 shadow-sm transition"
            >
              {showForm ? "Cancel" : "+ New Client"}
            </button>
          </div>
        </div>

        {/* Create/Edit Form */}
        {showForm && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">{editing ? "Edit Client" : "Add Client"}</h2>
            <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700">Full Name *</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Morgan"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Email Address *</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="alex@company.com"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Company Name</label>
                <input
                  type="text"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  placeholder="Acme Innovations"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Phone Number</label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+1 (555) 019-2834"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-700">Personalized Notes (Influences AI Tone)</label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  placeholder="Prefers casual tone, always pays late, accounts payable contact is Sarah..."
                />
              </div>
              <div className="sm:col-span-2 pt-2">
                <button
                  type="submit"
                  className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 shadow-sm transition"
                >
                  {editing ? "Update Client Profile" : "Save Client"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Clients List */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="divide-y divide-gray-200">
            {clients.length === 0 ? (
              <p className="p-8 text-gray-500 text-center text-sm">No clients yet. Add your first client to start sending invoices!</p>
            ) : (
              clients.map((client) => (
                <div key={client.id} className="p-5 flex flex-col sm:flex-row justify-between sm:items-center gap-4 hover:bg-gray-50/75 transition">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-gray-900 text-base">{client.name}</p>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-semibold capitalize ${
                          client.risk_tier === "severe"
                            ? "bg-red-100 text-red-700"
                            : client.risk_tier === "high"
                            ? "bg-orange-100 text-orange-700"
                            : client.risk_tier === "medium"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-green-100 text-green-700"
                        }`}
                      >
                        {client.risk_tier || "Low"} Risk
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5">{client.email} {client.phone && `• ${client.phone}`}</p>
                    {client.company && <p className="text-xs text-gray-400 mt-0.5">{client.company}</p>}
                    {client.notes && <p className="text-xs text-indigo-600 italic mt-1 bg-indigo-50/50 px-2 py-0.5 rounded inline-block">Note: {client.notes}</p>}
                  </div>
                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <button
                      onClick={() => handleEdit(client)}
                      className="px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(client.id)}
                      className="px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 rounded-lg transition"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
