import { http } from "./client";

// ---- Auth ----
export const authApi = {
  login: (email, password) =>
    http.post("/auth/login", { email, password }).then((r) => r.data),
  register: (payload) => http.post("/auth/register", payload).then((r) => r.data),
  me: () => http.get("/auth/me").then((r) => r.data),
};

// ---- Orders (customer / shared) ----
export const orderApi = {
  quote: (payload) => http.post("/orders/quote", payload).then((r) => r.data),
  create: (payload, idempotencyKey) =>
    http
      .post("/orders", payload, {
        headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      })
      .then((r) => r.data),
  list: (params) => http.get("/orders", { params }).then((r) => r.data),
  get: (id) => http.get(`/orders/${id}`).then((r) => r.data),
  confirm: (id) => http.post(`/orders/${id}/confirm`).then((r) => r.data),
  updateStatus: (id, status, reason) =>
    http.patch(`/orders/${id}/status`, { status, reason }).then((r) => r.data),
  fail: (id, failure_reason, notes) =>
    http.post(`/orders/${id}/fail`, { failure_reason, notes }).then((r) => r.data),
  reschedule: (id, payload) =>
    http.post(`/orders/${id}/reschedule`, payload).then((r) => r.data),
};

// ---- Tracking ----
export const trackingApi = {
  get: (id) => http.get(`/tracking/${id}`).then((r) => r.data),
  timeline: (id) => http.get(`/tracking/${id}/timeline`).then((r) => r.data),
};

// ---- Agent self-service ----
export const agentApi = {
  me: () => http.get("/agents/me").then((r) => r.data),
  setAvailability: (status) =>
    http.patch("/agents/me/availability", { status }).then((r) => r.data),
  updateLocation: (latitude, longitude) =>
    http.patch("/agents/me/location", { latitude, longitude }).then((r) => r.data),
};

// ---- Admin ----
export const adminApi = {
  zones: () => http.get("/admin/zones").then((r) => r.data),
  createZone: (payload) => http.post("/admin/zones", payload).then((r) => r.data),
  updateZone: (id, payload) => http.patch(`/admin/zones/${id}`, payload).then((r) => r.data),

  areas: (zoneId) =>
    http
      .get("/admin/areas", { params: zoneId ? { zone_id: zoneId } : {} })
      .then((r) => r.data),
  createArea: (payload) => http.post("/admin/areas", payload).then((r) => r.data),
  updateArea: (id, payload) => http.patch(`/admin/areas/${id}`, payload).then((r) => r.data),

  rates: (params) => http.get("/admin/rates", { params }).then((r) => r.data),
  createRate: (payload) => http.post("/admin/rates", payload).then((r) => r.data),
  updateRate: (id, payload) => http.patch(`/admin/rates/${id}`, payload).then((r) => r.data),
  deleteRate: (id) => http.delete(`/admin/rates/${id}`).then((r) => r.data),

  codSurcharges: () => http.get("/admin/cod-surcharges").then((r) => r.data),
  upsertCod: (payload) => http.put("/admin/cod-surcharges", payload).then((r) => r.data),

  agents: () => http.get("/admin/agents").then((r) => r.data),
  createAgent: (payload) => http.post("/admin/agents", payload).then((r) => r.data),
  updateAgent: (id, payload) => http.patch(`/admin/agents/${id}`, payload).then((r) => r.data),

  orders: (params) => http.get("/admin/orders", { params }).then((r) => r.data),
  assign: (orderId, agentId, reason) =>
    http
      .post(`/admin/orders/${orderId}/assign`, { agent_id: agentId, reason })
      .then((r) => r.data),
  autoAssign: (orderId) =>
    http.post(`/admin/orders/${orderId}/auto-assign`).then((r) => r.data),
  override: (orderId, status, reason) =>
    http.post(`/admin/orders/${orderId}/override`, { status, reason }).then((r) => r.data),
};

// ---- Analytics ----
export const analyticsApi = {
  summary: () => http.get("/analytics/summary").then((r) => r.data),
};

// ---- Notifications ----
export const notificationApi = {
  list: (params) => http.get("/notifications", { params }).then((r) => r.data),
};
