// Shared enum values and option lists mirroring the backend domain enums.

export const ROLES = {
  CUSTOMER: "CUSTOMER",
  DELIVERY_AGENT: "DELIVERY_AGENT",
  ADMIN: "ADMIN",
};

export const ORDER_TYPES = ["B2B", "B2C"];
export const PAYMENT_TYPES = ["PREPAID", "COD"];
export const ZONE_TYPES = ["INTRA_ZONE", "INTER_ZONE"];
export const AGENT_STATUSES = ["AVAILABLE", "BUSY", "OFFLINE"];

export const ORDER_STATUSES = [
  "PENDING_CONFIRMATION",
  "CONFIRMED",
  "ASSIGNED",
  "PICKED_UP",
  "IN_TRANSIT",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
  "FAILED",
  "RESCHEDULED",
  "CANCELLED",
];

// Status an assigned agent can advance an order to (mirrors the state machine).
export const AGENT_NEXT_STATUS = {
  ASSIGNED: ["PICKED_UP"],
  PICKED_UP: ["IN_TRANSIT"],
  IN_TRANSIT: ["OUT_FOR_DELIVERY"],
  OUT_FOR_DELIVERY: ["DELIVERED", "FAILED"],
};

export const FAILURE_REASONS = [
  "CUSTOMER_UNAVAILABLE",
  "WRONG_ADDRESS",
  "CUSTOMER_REFUSED",
  "DAMAGED_PACKAGE",
  "OTHER",
];

export const toOptions = (values) => values.map((v) => ({ value: v, label: v }));
