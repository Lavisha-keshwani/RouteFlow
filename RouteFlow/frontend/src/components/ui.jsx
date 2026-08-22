import { X } from "lucide-react";
import { forwardRef } from "react";
import { cn, humanize } from "@/lib/format";

// ---- Spinner ----
export function Spinner({ className }) {
  return (
    <div
      className={cn(
        "h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600",
        className
      )}
    />
  );
}

export function LoadingBlock({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
      <Spinner /> <span className="text-sm">{label}</span>
    </div>
  );
}

// ---- Button ----
export function Button({ variant = "primary", loading, children, className, disabled, ...rest }) {
  const cls = {
    primary: "btn-primary",
    secondary: "btn-secondary",
    danger: "btn-danger",
    ghost: "btn-ghost",
  }[variant];
  return (
    <button className={cn(cls, className)} disabled={disabled || loading} {...rest}>
      {loading && <Spinner className="h-4 w-4 border-white/40 border-t-white" />}
      {children}
    </button>
  );
}

// ---- Card ----
export function Card({ children, className }) {
  return <div className={cn("card p-5", className)}>{children}</div>;
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatCard({ label, value, hint, accent }) {
  return (
    <div className="card p-5">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className={cn("mt-2 text-3xl font-bold tracking-tight", accent ?? "text-slate-900")}>
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
    </div>
  );
}

// ---- Badges ----
const STATUS_STYLES = {
  PENDING_CONFIRMATION: "bg-amber-50 text-amber-700 ring-amber-600/20",
  CONFIRMED: "bg-sky-50 text-sky-700 ring-sky-600/20",
  ASSIGNED: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
  PICKED_UP: "bg-violet-50 text-violet-700 ring-violet-600/20",
  IN_TRANSIT: "bg-blue-50 text-blue-700 ring-blue-600/20",
  OUT_FOR_DELIVERY: "bg-cyan-50 text-cyan-700 ring-cyan-600/20",
  DELIVERED: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  FAILED: "bg-rose-50 text-rose-700 ring-rose-600/20",
  RESCHEDULED: "bg-orange-50 text-orange-700 ring-orange-600/20",
  CANCELLED: "bg-slate-100 text-slate-600 ring-slate-500/20",
  AVAILABLE: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  BUSY: "bg-amber-50 text-amber-700 ring-amber-600/20",
  OFFLINE: "bg-slate-100 text-slate-600 ring-slate-500/20",
  SENT: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  PENDING: "bg-amber-50 text-amber-700 ring-amber-600/20",
};

export function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600 ring-slate-500/20";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset",
        style
      )}
    >
      {humanize(status)}
    </span>
  );
}

export function Pill({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-600",
    brand: "bg-brand-50 text-brand-700",
    green: "bg-emerald-50 text-emerald-700",
  };
  return (
    <span className={cn("rounded-md px-2 py-0.5 text-xs font-medium", tones[tone])}>
      {children}
    </span>
  );
}

// ---- Form fields ----
export const Field = forwardRef(function Field({ label, error, className, ...rest }, ref) {
  return (
    <div>
      {label && <label className="label">{label}</label>}
      <input
        ref={ref}
        className={cn("input", error && "border-rose-400 focus:ring-rose-200", className)}
        {...rest}
      />
      {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
    </div>
  );
});

export const SelectField = forwardRef(function SelectField(
  { label, error, options, className, ...rest },
  ref
) {
  return (
    <div>
      {label && <label className="label">{label}</label>}
      <select ref={ref} className={cn("input", className)} {...rest}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
    </div>
  );
});

// ---- Empty state ----
export function EmptyState({ title, description, icon }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white/60 py-16 text-center">
      {icon && <div className="mb-3 text-slate-300">{icon}</div>}
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-slate-400">{description}</p>}
    </div>
  );
}

// ---- Modal ----
export function Modal({ open, onClose, title, children, footer }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose} />
      <div className="card relative z-10 w-full max-w-lg p-0">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-slate-100 px-5 py-4">{footer}</div>
        )}
      </div>
    </div>
  );
}

// ---- Table primitives ----
export function Table({ children }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">{children}</table>
    </div>
  );
}
export function Th({ children, className }) {
  return (
    <th
      className={cn(
        "px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500",
        className
      )}
    >
      {children}
    </th>
  );
}
export function Td({ children, className }) {
  return <td className={cn("px-4 py-3 text-slate-700", className)}>{children}</td>;
}
