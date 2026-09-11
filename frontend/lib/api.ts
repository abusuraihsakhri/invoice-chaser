import axios from "axios";

export const getApiBaseUrl = (): string => {
  if (typeof window !== "undefined") {
    const customUrl = localStorage.getItem("api_base_url");
    if (customUrl && customUrl.trim().length > 0) {
      return customUrl.trim().replace(/\/+$/, "");
    }
  }
  return (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
};

export const api = axios.create({
  baseURL: getApiBaseUrl(),
});

// Dynamically attach current API base URL & auth token
api.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl();
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      if (!window.location.pathname.includes("/login") && !window.location.pathname.includes("/register")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// Auth
export const authApi = {
  register: (data: {
    email: string;
    password: string;
    business_name?: string;
    tone_preference?: string;
    currency?: string;
  }) => api.post("/api/auth/register", data),
  login: (data: { email: string; password: string }) => api.post("/api/auth/login", data),
  getMe: () => api.get("/api/auth/me"),
};

// Clients
export const clientsApi = {
  list: () => api.get("/api/clients"),
  create: (data: { name: string; email: string; company?: string; phone?: string; notes?: string }) =>
    api.post("/api/clients", data),
  update: (id: number, data: any) => api.put(`/api/clients/${id}`, data),
  delete: (id: number) => api.delete(`/api/clients/${id}`),
  exportCsvUrl: () => `${getApiBaseUrl()}/api/clients/export/csv`,
};

// Invoices
export const invoicesApi = {
  list: (status?: string) => api.get("/api/invoices", { params: { status_filter: status } }),
  get: (id: number) => api.get(`/api/invoices/${id}`),
  create: (data: {
    client_id: number;
    amount: number;
    currency?: string;
    description?: string;
    payment_url?: string;
    issued_date: string;
    due_date: string;
  }) => api.post("/api/invoices", data),
  update: (id: number, data: any) => api.put(`/api/invoices/${id}`, data),
  markPaid: (id: number) => api.post(`/api/invoices/${id}/mark-paid`),
  generatePaymentLink: (id: number) => api.post(`/api/invoices/${id}/payment-link`),
  getPdfUrl: (id: number) => `${getApiBaseUrl()}/api/invoices/${id}/pdf`,
  downloadPdf: async (id: number, invoiceNumber: string) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : "";
    const res = await axios.get(`${getApiBaseUrl()}/api/invoices/${id}/pdf`, {
      responseType: "blob",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const blob = new Blob([res.data], { type: "application/pdf" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Invoice_${invoiceNumber}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
  exportCsvUrl: () => `${getApiBaseUrl()}/api/invoices/export/csv`,
};

// Reminders
export const remindersApi = {
  list: (invoiceId?: number) => api.get("/api/reminders", { params: { invoice_id: invoiceId } }),
  get: (id: number) => api.get(`/api/reminders/${id}`),
  edit: (id: number, data: { email_subject?: string; email_body?: string; scheduled_at?: string }) =>
    api.put(`/api/reminders/${id}`, data),
  sendNow: (id: number) => api.post(`/api/reminders/${id}/send`),
  cancel: (id: number) => api.delete(`/api/reminders/${id}`),
};

// Intelligence & AI
export const intelligenceApi = {
  getRisk: (invoiceId: number) => api.get(`/api/intelligence/invoices/${invoiceId}/risk`),
  escalateTone: (data: { invoice_id: number; target_tone: string; custom_instruction?: string }) =>
    api.post("/api/intelligence/escalate-tone", data),
  draftDisputeReply: (data: { invoice_id: number; client_excuse: string }) =>
    api.post("/api/intelligence/draft-dispute-reply", data),
  createPaymentPlan: (
    invoiceId: number,
    data: { installments_count: number; frequency_days: number; notes?: string }
  ) => api.post(`/api/intelligence/invoices/${invoiceId}/payment-plan`, data),
  getPaymentPlans: (invoiceId: number) =>
    api.get(`/api/intelligence/invoices/${invoiceId}/payment-plans`),
};

// Integrations
export const integrationsApi = {
  list: () => api.get("/api/integrations"),
  save: (data: { service_name: string; is_active: boolean; config_data: any }) =>
    api.post("/api/integrations", data),
  testWebhook: (data: { service: string; webhook_url: string }) =>
    api.post("/api/integrations/test-webhook", data),
};

// Dashboard & Health
export const dashboardApi = {
  getStats: () => api.get("/api/dashboard"),
  getHealth: async (baseUrl?: string) => {
    const target = (baseUrl || getApiBaseUrl()).replace(/\/+$/, "");
    const startTime = Date.now();
    const res = await axios.get(`${target}/health`, { timeout: 5000 });
    const latencyMs = Date.now() - startTime;
    return { ...res.data, latencyMs };
  },
};

