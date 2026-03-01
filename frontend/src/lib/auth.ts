import axios from "axios";

const TOKEN_KEY = "ca_token";

export const API_BASE =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

const authApi = axios.create({
  baseURL: API_BASE,
});

// ---------------- Token helpers ----------------
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// ---------------- Auth APIs ----------------

export async function registerUser(email: string, password: string) {
  const { data } = await authApi.post("/auth/register", {
    email,
    password,
  });

  return data;
}

export async function loginUser(email: string, password: string) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const { data } = await authApi.post("/auth/login", form, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return data;
}

export async function me() {
  const token = getToken();
  if (!token) throw new Error("No token");

  const { data } = await authApi.get("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  return data;
}