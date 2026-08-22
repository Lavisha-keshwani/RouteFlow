import axios from "axios";

const TOKEN_KEY = "routeflow_token";
const REFRESH_KEY = "routeflow_refresh";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access, refresh) => {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";

export const http = axios.create({ baseURL });

// Attach the bearer token to every request when present.
http.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Normalize backend error envelopes and auto-logout on 401.
http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && tokenStore.get()) {
      tokenStore.clear();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    const apiError = error.response?.data?.error ?? {
      code: "NETWORK_ERROR",
      message: error.message || "Unable to reach the server.",
    };
    return Promise.reject(apiError);
  }
);

export function getErrorMessage(err) {
  if (err && typeof err === "object" && "message" in err) {
    return String(err.message);
  }
  return "Something went wrong.";
}
