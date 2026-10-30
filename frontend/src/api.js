const API_URL = import.meta.env.VITE_API_URL || "/api";

export async function getHealth() {
  const response = await fetch(`${API_URL}/health/`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export async function login(username, password, tenantId) {
  const response = await fetch(`${API_URL}/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    throw new Error("Login failed. Check your username and password.");
  }

  const data = await response.json();
  sessionStorage.setItem("apiToken", data.token);
  sessionStorage.setItem("tenantId", tenantId);
}

export async function apiRequest(path, options = {}) {
  const token = sessionStorage.getItem("apiToken");
  const tenantId = sessionStorage.getItem("tenantId");
  const isFormData = options.body instanceof FormData;

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body && !isFormData
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}
export async function createCheckoutSession() {
  return apiRequest("/billing/checkout/", {
    method: "POST",
  });
}
export async function getBillingStatus() {
  return apiRequest("/billing/status/");
}