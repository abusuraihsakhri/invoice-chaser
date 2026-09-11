"use client";

import { useEffect, useState } from "react";
import Navbar from "@/components/Navbar";
import { getApiBaseUrl, dashboardApi, integrationsApi } from "@/lib/api";

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState("");
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency?: number } | null>(null);
  const [testing, setTesting] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Webhook test
  const [webhookService, setWebhookService] = useState("slack");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [webhookStatus, setWebhookStatus] = useState<string | null>(null);

  useEffect(() => {
    setApiUrl(getApiBaseUrl());
  }, []);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const data = await dashboardApi.getHealth(apiUrl);
      if (data && data.status === "healthy") {
        setTestResult({
          success: true,
          message: `Connected! Database: ${data.database} | AI: ${data.ai_provider} | Email: ${data.email_configured ? "Ready" : "Demo Mode"}`,
          latency: data.latencyMs,
        });
      } else {
        setTestResult({ success: false, message: "Server responded, but health status is unhealthy." });
      }
    } catch (err: any) {
      setTestResult({
        success: false,
        message: err.message || "Failed to connect to API server. Ensure backend is running.",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveApiUrl = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUrl = apiUrl.trim().replace(/\/+$/, "");
    localStorage.setItem("api_base_url", cleanUrl);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleResetDefaultUrl = () => {
    localStorage.removeItem("api_base_url");
    setApiUrl("http://localhost:8000");
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  const handleTestWebhook = async () => {
    if (!webhookUrl) return;
    setTestingWebhook(true);
    setWebhookStatus(null);
    try {
      await integrationsApi.testWebhook({
        service: webhookService,
        webhook_url: webhookUrl,
      });
      setWebhookStatus("Test alert successfully dispatched!");
    } catch (err: any) {
      setWebhookStatus(`Failed to send test: ${err.message}`);
    } finally {
      setTestingWebhook(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8">
      <Navbar />

      <main className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Settings & Integrations</h1>
          <p className="text-sm text-gray-500 mt-1">
            Configure cross-platform networking, intelligence engine, payment gateways, and webhooks.
          </p>
        </div>

        {/* API Server Configuration (Essential for Desktop and Android mobile phones) */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">API Server Endpoint</h2>
              <p className="text-xs text-gray-500">
                Connect your Android phone or Desktop client to local Wi-Fi or Cloud API backend.
              </p>
            </div>
            <span className="text-xs bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-md font-medium">
              Multi-Device Sync
            </span>
          </div>

          <form onSubmit={handleSaveApiUrl} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Backend URL
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  required
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  placeholder="e.g. http://localhost:8000 or http://192.168.1.50:8000"
                  className="flex-1 rounded-lg border border-gray-300 px-3.5 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testing}
                  className="px-4 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg disabled:opacity-50 transition"
                >
                  {testing ? "Pinging..." : "Test Ping"}
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
                >
                  Save URL
                </button>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Tip: On Android physical devices, use your computer&apos;s local IP (e.g. <code>http://192.168.x.x:8000</code>) instead of localhost.
              </p>
            </div>

            {savedSuccess && (
              <div className="p-3 bg-green-50 text-green-700 text-sm rounded-lg border border-green-200">
                ✓ API endpoint saved successfully!
              </div>
            )}

            {testResult && (
              <div
                className={`p-4 rounded-lg text-sm border ${
                  testResult.success
                    ? "bg-green-50 text-green-800 border-green-200"
                    : "bg-red-50 text-red-800 border-red-200"
                }`}
              >
                <p className="font-semibold flex items-center justify-between">
                  <span>{testResult.success ? "✓ API Connected Successfully" : "✗ Connection Failed"}</span>
                  {testResult.latency && <span className="text-xs font-mono">{testResult.latency} ms</span>}
                </p>
                <p className="mt-1 text-xs opacity-90">{testResult.message}</p>
              </div>
            )}

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleResetDefaultUrl}
                className="text-xs text-gray-500 hover:text-gray-700 underline"
              >
                Reset to default (http://localhost:8000)
              </button>
            </div>
          </form>
        </div>

        {/* Intelligence Engine & AI Configuration */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Intelligence & Tone Escalation</h2>
          <p className="text-xs text-gray-500 mb-4">
            AI handles payment prediction, dispute replies, and tone escalation.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
              <span className="font-medium text-gray-900">Supported AI Engines</span>
              <p className="text-xs text-gray-500 mt-1">
                Hermes 3, OpenAI GPT-4o, Google Gemini, Anthropic Claude, or Zero-Config Offline Heuristics.
              </p>
            </div>
            <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
              <span className="font-medium text-gray-900">Prompt Injection Guard</span>
              <p className="text-xs text-gray-500 mt-1">
                Active boundary filtering and XML containment prevents debtor prompt manipulation.
              </p>
            </div>
          </div>
        </div>

        {/* Webhook Dispatcher (Slack / Discord) */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">Team Webhook Notifications</h2>
          <p className="text-xs text-gray-500 mb-4">
            Receive real-time alerts when invoices become overdue or payments are collected.
          </p>

          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <select
                value={webhookService}
                onChange={(e) => setWebhookService(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white"
              >
                <option value="slack">Slack Webhook</option>
                <option value="discord">Discord Webhook</option>
                <option value="generic">Generic HTTPS Webhook</option>
              </select>
              <input
                type="url"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/services/..."
                className="sm:col-span-2 rounded-lg border border-gray-300 px-3.5 py-2 text-sm"
              />
            </div>

            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-400">Events: invoice.created, invoice.overdue, invoice.paid, reminder.sent</span>
              <button
                type="button"
                onClick={handleTestWebhook}
                disabled={testingWebhook || !webhookUrl}
                className="px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-sm font-medium rounded-lg disabled:opacity-50 transition"
              >
                {testingWebhook ? "Sending..." : "Test Webhook"}
              </button>
            </div>

            {webhookStatus && (
              <p className="text-xs text-gray-600 bg-gray-50 p-2.5 rounded border border-gray-200">
                {webhookStatus}
              </p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
