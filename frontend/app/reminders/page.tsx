"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { remindersApi, intelligenceApi } from "@/lib/api";

interface Reminder {
  id: number;
  invoice_id: number;
  reminder_type: string;
  tone: string;
  status: string;
  scheduled_at: string;
  sent_at: string | null;
  email_subject: string;
  email_body: string;
  invoice?: {
    invoice_number: string;
    client: { name: string; email: string };
  };
}

export default function RemindersPage() {
  const router = useRouter();
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<Reminder | null>(null);

  // AI Escalation Modal state
  const [escalatingReminder, setEscalatingReminder] = useState<Reminder | null>(null);
  const [targetTone, setTargetTone] = useState("urgent");
  const [customInstruction, setCustomInstruction] = useState("");
  const [escalating, setEscalating] = useState(false);
  const [generatedPreview, setGeneratedPreview] = useState<{ subject: string; body: string; rate: number } | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }
    loadReminders();
  }, []);

  const loadReminders = async () => {
    try {
      const res = await remindersApi.list();
      setReminders(res.data);
    } catch (err) {
      console.error("Failed to load reminders:", err);
    } finally {
      setLoading(false);
    }
  };

  const sendNow = async (id: number) => {
    try {
      await remindersApi.sendNow(id);
      loadReminders();
      setPreview(null);
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to send reminder");
    }
  };

  const cancelReminder = async (id: number) => {
    if (!confirm("Cancel this scheduled reminder?")) return;
    try {
      await remindersApi.cancel(id);
      loadReminders();
    } catch (err: any) {
      alert("Failed to cancel reminder");
    }
  };

  const handleGenerateEscalation = async () => {
    if (!escalatingReminder) return;
    setEscalating(true);
    try {
      const res = await intelligenceApi.escalateTone({
        invoice_id: escalatingReminder.invoice_id,
        target_tone: targetTone,
        custom_instruction: customInstruction || undefined,
      });
      setGeneratedPreview({
        subject: res.data.subject,
        body: res.data.body,
        rate: res.data.projected_response_rate_pct,
      });
    } catch (err: any) {
      alert("Failed to generate AI tone escalation");
    } finally {
      setEscalating(false);
    }
  };

  const handleApplyEscalation = async () => {
    if (!escalatingReminder || !generatedPreview) return;
    try {
      await remindersApi.edit(escalatingReminder.id, {
        email_subject: generatedPreview.subject,
        email_body: generatedPreview.body,
      });
      setEscalatingReminder(null);
      setGeneratedPreview(null);
      loadReminders();
    } catch (err) {
      alert("Failed to update reminder");
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading reminders...</div>;
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8">
      <Navbar />

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8 px-4">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Payment Reminders</h1>
          <p className="text-xs text-gray-500">Automated AI-powered reminder queue with tone auto-escalation.</p>
        </div>

        {/* AI Tone Escalation Modal */}
        {escalatingReminder && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full p-6 border border-gray-100 max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-xl">✨</span>
                  <h2 className="text-lg font-bold text-gray-900">AI Tone Escalator & Drafter</h2>
                </div>
                <button
                  onClick={() => {
                    setEscalatingReminder(null);
                    setGeneratedPreview(null);
                  }}
                  className="text-gray-400 hover:text-gray-600 text-xl"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-4 text-sm">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Target Tone</label>
                  <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                    {["friendly", "professional", "firm", "urgent", "final", "legal"].map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setTargetTone(t)}
                        className={`py-2 px-2 text-xs font-medium rounded-lg border capitalize transition ${
                          targetTone === t
                            ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                            : "bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100"
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">
                    Custom Prompt or Specific Instruction (Optional)
                  </label>
                  <input
                    type="text"
                    value={customInstruction}
                    onChange={(e) => setCustomInstruction(e.target.value)}
                    placeholder="e.g. Mention our client phone call on Monday, offer 3% prompt discount..."
                    className="w-full rounded-lg border border-gray-300 px-3.5 py-2 text-sm"
                  />
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={handleGenerateEscalation}
                    disabled={escalating}
                    className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition shadow-sm"
                  >
                    {escalating ? "AI Drafting..." : "Generate AI Copy"}
                  </button>
                </div>

                {generatedPreview && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200 space-y-3">
                    <div className="flex justify-between items-center text-xs text-gray-500">
                      <span>Subject: <strong>{generatedPreview.subject}</strong></span>
                      <span className="text-green-700 font-semibold bg-green-50 px-2 py-0.5 rounded">
                        ~{generatedPreview.rate}% Response Rate
                      </span>
                    </div>
                    <div className="p-3 bg-white rounded-lg border border-gray-200 text-xs text-gray-800 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                      {generatedPreview.body}
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <button
                        type="button"
                        onClick={handleApplyEscalation}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
                      >
                        Apply to Reminder
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Preview Modal */}
        {preview && (
          <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full p-6 border border-gray-100">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold text-gray-900">Email Preview</h2>
                <button onClick={() => setPreview(null)} className="text-gray-400 hover:text-gray-600 text-xl">
                  &times;
                </button>
              </div>
              <div className="mb-4 text-xs text-gray-600 space-y-1 bg-gray-50 p-3 rounded-lg border border-gray-100">
                <p><strong>To:</strong> {preview.invoice?.client.email}</p>
                <p><strong>Subject:</strong> {preview.email_subject}</p>
                <p><strong>Escalation Tone:</strong> <span className="capitalize">{preview.tone}</span></p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-gray-200 whitespace-pre-wrap text-xs text-gray-800 leading-relaxed mb-6 max-h-60 overflow-y-auto font-sans">
                {preview.email_body}
              </div>
              <div className="flex justify-between items-center">
                <div className="text-xs text-gray-400">
                  {preview.status === "sent" ? "Sent" : "Scheduled"}
                </div>
                <div className="flex gap-2">
                  {preview.status !== "sent" && preview.status !== "cancelled" && (
                    <button
                      onClick={() => sendNow(preview.id)}
                      className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-xs font-medium hover:bg-indigo-700 shadow-sm transition"
                    >
                      Send Immediately
                    </button>
                  )}
                  <button
                    onClick={() => setPreview(null)}
                    className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg text-xs font-medium hover:bg-gray-200 transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Reminders List */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="divide-y divide-gray-200">
            {reminders.length === 0 ? (
              <p className="p-8 text-gray-500 text-center text-sm">
                No reminders yet. Create an invoice to auto-schedule your first set of reminders!
              </p>
            ) : (
              reminders.map((reminder) => (
                <div key={reminder.id} className="p-5 flex flex-col sm:flex-row justify-between sm:items-center gap-4 hover:bg-gray-50/75 transition">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <p className="font-semibold text-gray-900 text-sm">{reminder.email_subject}</p>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${
                          reminder.tone === "legal" || reminder.tone === "final"
                            ? "bg-red-100 text-red-700"
                            : reminder.tone === "urgent" || reminder.tone === "firm"
                            ? "bg-orange-100 text-orange-700"
                            : "bg-blue-100 text-blue-700"
                        }`}
                      >
                        {reminder.tone} Tone
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      Invoice: {reminder.invoice?.invoice_number || `#${reminder.invoice_id}`} &bull; Client: {reminder.invoice?.client.name || "Client"}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Scheduled: {new Date(reminder.scheduled_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    {reminder.status === "sent" ? (
                      <span className="text-green-700 bg-green-50 px-2.5 py-1 rounded-md text-xs font-semibold">
                        ✓ Sent {reminder.sent_at ? new Date(reminder.sent_at).toLocaleDateString() : ""}
                      </span>
                    ) : reminder.status === "cancelled" ? (
                      <span className="text-gray-400 bg-gray-100 px-2.5 py-1 rounded-md text-xs">
                        Cancelled (Paid)
                      </span>
                    ) : (
                      <>
                        <button
                          onClick={() => {
                            setEscalatingReminder(reminder);
                            setTargetTone(reminder.tone || "firm");
                          }}
                          className="px-2.5 py-1 text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-md transition"
                        >
                          ✨ AI Escalator
                        </button>
                        <button
                          onClick={() => setPreview(reminder)}
                          className="px-2.5 py-1 text-xs font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md transition"
                        >
                          Preview
                        </button>
                        <button
                          onClick={() => sendNow(reminder.id)}
                          className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md text-xs font-medium shadow-sm transition"
                        >
                          Send Now
                        </button>
                        <button
                          onClick={() => cancelReminder(reminder.id)}
                          className="px-2 py-1 text-xs text-red-500 hover:text-red-700"
                          title="Cancel reminder"
                        >
                          &times;
                        </button>
                      </>
                    )}
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
