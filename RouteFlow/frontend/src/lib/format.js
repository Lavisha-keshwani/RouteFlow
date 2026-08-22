import { clsx } from "clsx";
import { format, formatDistanceToNow, parseISO } from "date-fns";

/** Join class names conditionally (clsx wrapper). */
export function cn(...inputs) {
  return clsx(inputs);
}

export function formatCurrency(value, currency = "INR") {
  const amount = typeof value === "string" ? parseFloat(value) : value;
  const symbol = currency === "INR" ? "₹" : "";
  return `${symbol}${(amount || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatWeight(value) {
  const amount = typeof value === "string" ? parseFloat(value) : value;
  return `${(amount || 0).toLocaleString("en-IN", { maximumFractionDigits: 3 })} kg`;
}

export function formatDate(iso) {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "dd MMM yyyy, h:mm a");
  } catch {
    return iso;
  }
}

export function formatRelative(iso) {
  if (!iso) return "—";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return "—";
  }
}

/** Turn SCREAMING_SNAKE_CASE enums into "Title Case" labels. */
export function humanize(value) {
  if (!value) return "—";
  return value
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
