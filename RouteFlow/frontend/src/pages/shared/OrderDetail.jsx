import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  MapPin,
  Package as PackageIcon,
  UserCheck,
  Sparkles,
} from "lucide-react";
import { adminApi, orderApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  Button,
  Card,
  Field,
  LoadingBlock,
  Modal,
  PageHeader,
  Pill,
  SelectField,
  StatusBadge,
  Td,
  Table,
  Th,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/client";
import { cn, formatCurrency, formatDate, formatWeight, humanize } from "@/lib/format";

const NEXT_STATUS = {
  ASSIGNED: "PICKED_UP",
  PICKED_UP: "IN_TRANSIT",
  IN_TRANSIT: "OUT_FOR_DELIVERY",
  OUT_FOR_DELIVERY: "DELIVERED",
};

const ALL_STATUSES = [
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

const FAILURE_REASONS = [
  "CUSTOMER_UNAVAILABLE",
  "WRONG_ADDRESS",
  "CUSTOMER_REFUSED",
  "DAMAGED_PACKAGE",
  "OTHER",
];

export default function OrderDetail() {
  const { id } = useParams();
  const orderId = Number(id);
  const { user } = useAuth();
  const qc = useQueryClient();
  const [modal, setModal] = useState(null);

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => orderApi.get(orderId),
  });

  function refresh() {
    qc.invalidateQueries({ queryKey: ["order", orderId] });
    qc.invalidateQueries({ queryKey: ["orders"] });
  }

  const confirmMut = useMutation({
    mutationFn: () => orderApi.confirm(orderId),
    onSuccess: () => {
      toast.success("Order confirmed");
      refresh();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const statusMut = useMutation({
    mutationFn: (status) => orderApi.updateStatus(orderId, status),
    onSuccess: () => {
      toast.success("Status updated");
      refresh();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  if (isLoading || !order) return <LoadingBlock />;

  const role = user?.role;
  const isAdmin = role === "ADMIN";
  const isCustomer = role === "CUSTOMER";
  const isAgent = role === "DELIVERY_AGENT";
  const next = NEXT_STATUS[order.status];
  const canAdvance = (isAgent || isAdmin) && next;
  const canConfirm = (isCustomer || isAdmin) && order.status === "PENDING_CONFIRMATION";
  const canAssign = isAdmin && (order.status === "CONFIRMED" || order.status === "RESCHEDULED");
  const canReschedule = (isCustomer || isAdmin) && order.status === "FAILED";
  const canFail = (isAgent || isAdmin) && order.status === "OUT_FOR_DELIVERY";

  return (
    <div>
      <PageHeader
        title={order.order_number}
        subtitle={`Created ${formatDate(order.created_at)}`}
        action={<StatusBadge status={order.status} />}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: details */}
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <h3 className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-900">
              <MapPin size={18} className="text-brand-600" /> Route & package
            </h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <Info label="Pickup" value={order.pickup_address} />
              <Info label="Drop" value={order.drop_address} />
              <Info label="Zone type" value={humanize(order.zone_type)} />
              <Info
                label="Order / payment"
                value={`${order.order_type} · ${humanize(order.payment_type)}`}
              />
              {order.package && (
                <>
                  <Info
                    label="Dimensions"
                    value={`${order.package.length_cm} × ${order.package.width_cm} × ${order.package.height_cm} cm`}
                  />
                  <Info
                    label="Chargeable weight"
                    value={formatWeight(order.package.chargeable_weight_kg)}
                  />
                </>
              )}
            </div>
          </Card>

          <Card>
            <h3 className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-900">
              <PackageIcon size={18} className="text-brand-600" /> Pricing snapshot
            </h3>
            <div className="space-y-2 text-sm">
              <Row label="Base charge" value={formatCurrency(order.base_charge, order.currency)} />
              <Row
                label="COD surcharge"
                value={
                  order.payment_type === "COD"
                    ? formatCurrency(order.cod_surcharge, order.currency)
                    : "—"
                }
              />
              <div className="flex items-center justify-between border-t border-dashed border-slate-200 pt-2">
                <span className="font-semibold text-slate-900">Total</span>
                <span className="text-lg font-bold text-brand-700">
                  {formatCurrency(order.total_charge, order.currency)}
                </span>
              </div>
              <p className="pt-1 text-xs text-slate-400">
                Frozen at confirmation — rate-card changes never alter this order.
              </p>
            </div>
          </Card>

          {order.attempts.length > 0 && (
            <Card>
              <h3 className="mb-4 text-base font-semibold text-slate-900">Delivery attempts</h3>
              <Table>
                <thead className="bg-slate-50">
                  <tr>
                    <Th>#</Th>
                    <Th>Status</Th>
                    <Th>Agent</Th>
                    <Th>Scheduled</Th>
                    <Th>Reason</Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {order.attempts.map((a) => (
                    <tr key={a.id}>
                      <Td>{a.attempt_number}</Td>
                      <Td>
                        <StatusBadge status={a.status} />
                      </Td>
                      <Td>{a.agent_id ? `#${a.agent_id}` : "—"}</Td>
                      <Td>{a.scheduled_date ?? "—"}</Td>
                      <Td className="text-slate-500">
                        {a.failure_reason ? humanize(a.failure_reason) : "—"}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Card>
          )}
        </div>

        {/* Right: timeline + actions */}
        <div className="space-y-6">
          <Card>
            <h3 className="mb-4 text-base font-semibold text-slate-900">Actions</h3>
            <div className="space-y-2">
              {canConfirm && (
                <Button
                  className="w-full"
                  loading={confirmMut.isPending}
                  onClick={() => confirmMut.mutate()}
                >
                  Confirm order
                </Button>
              )}
              {canAssign && (
                <Button className="w-full" onClick={() => setModal("assign")}>
                  <UserCheck size={16} /> Assign agent
                </Button>
              )}
              {canAdvance && next && (
                <Button
                  className="w-full"
                  loading={statusMut.isPending}
                  onClick={() => statusMut.mutate(next)}
                >
                  Mark {humanize(next)}
                </Button>
              )}
              {canFail && (
                <Button variant="danger" className="w-full" onClick={() => setModal("fail")}>
                  Report failed delivery
                </Button>
              )}
              {canReschedule && (
                <Button className="w-full" onClick={() => setModal("reschedule")}>
                  Reschedule delivery
                </Button>
              )}
              {isAdmin && (
                <Button
                  variant="secondary"
                  className="w-full"
                  onClick={() => setModal("override")}
                >
                  Override status
                </Button>
              )}
              {!canConfirm &&
                !canAssign &&
                !canAdvance &&
                !canFail &&
                !canReschedule &&
                !isAdmin && (
                  <p className="text-sm text-slate-400">
                    No actions available for this order right now.
                  </p>
                )}
            </div>
          </Card>

          <Card>
            <h3 className="mb-4 text-base font-semibold text-slate-900">Tracking timeline</h3>
            <Timeline history={order.status_history} />
          </Card>
        </div>
      </div>

      {modal === "assign" && (
        <AssignModal orderId={orderId} onClose={() => setModal(null)} onDone={refresh} />
      )}
      {modal === "reschedule" && (
        <RescheduleModal orderId={orderId} onClose={() => setModal(null)} onDone={refresh} />
      )}
      {modal === "fail" && (
        <FailModal orderId={orderId} onClose={() => setModal(null)} onDone={refresh} />
      )}
      {modal === "override" && (
        <OverrideModal orderId={orderId} onClose={() => setModal(null)} onDone={refresh} />
      )}
    </div>
  );
}

function Info({ label, value }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm text-slate-800">{value}</p>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-800">{value}</span>
    </div>
  );
}

function Timeline({ history }) {
  if (history.length === 0) return <p className="text-sm text-slate-400">No events yet.</p>;
  return (
    <ol className="relative space-y-5">
      {history.map((h, idx) => {
        const isLast = idx === history.length - 1;
        const failed = h.new_status === "FAILED";
        return (
          <li key={h.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              {failed ? (
                <AlertTriangle size={18} className="text-rose-500" />
              ) : isLast ? (
                <Circle size={18} className="fill-brand-100 text-brand-600" />
              ) : (
                <CheckCircle2 size={18} className="text-emerald-500" />
              )}
              {idx !== history.length - 1 && (
                <span className="mt-1 h-full w-px flex-1 bg-slate-200" />
              )}
            </div>
            <div className="pb-1">
              <p
                className={cn(
                  "text-sm font-semibold",
                  failed ? "text-rose-700" : "text-slate-800"
                )}
              >
                {humanize(h.new_status)}
              </p>
              <p className="text-xs text-slate-400">{formatDate(h.created_at)}</p>
              {h.reason && <p className="mt-0.5 text-xs text-slate-500">{h.reason}</p>}
              {h.actor_role && (
                <span className="mt-1 inline-block">
                  <Pill>{humanize(h.actor_role)}</Pill>
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// ---- Modals ----
function AssignModal({ orderId, onClose, onDone }) {
  const { data: agents, isLoading } = useQuery({
    queryKey: ["admin", "agents"],
    queryFn: adminApi.agents,
  });
  const auto = useMutation({
    mutationFn: () => adminApi.autoAssign(orderId),
    onSuccess: (res) => {
      toast.success(`Auto-assigned: ${res.decision.explanation}`);
      onDone();
      onClose();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });
  const manual = useMutation({
    mutationFn: (agentId) => adminApi.assign(orderId, agentId),
    onSuccess: () => {
      toast.success("Agent assigned");
      onDone();
      onClose();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const available = (agents ?? []).filter((a) => a.is_active);

  return (
    <Modal open onClose={onClose} title="Assign delivery agent">
      <Button className="mb-4 w-full" loading={auto.isPending} onClick={() => auto.mutate()}>
        <Sparkles size={16} /> Auto-assign best agent
      </Button>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-400">
        Or choose manually
      </p>
      {isLoading ? (
        <LoadingBlock />
      ) : (
        <div className="max-h-64 space-y-2 overflow-y-auto">
          {available.map((a) => {
            const full = a.active_orders >= a.max_active_orders;
            const disabled = full || a.status === "OFFLINE";
            return (
              <div
                key={a.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-slate-800">{a.full_name}</p>
                  <p className="text-xs text-slate-400">
                    {humanize(a.status)} · {a.active_orders}/{a.max_active_orders} active
                  </p>
                </div>
                <Button
                  variant="secondary"
                  disabled={disabled || manual.isPending}
                  onClick={() => manual.mutate(a.id)}
                >
                  Assign
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </Modal>
  );
}

function RescheduleModal({ orderId, onClose, onDone }) {
  const [date, setDate] = useState("");
  const [reason, setReason] = useState("");
  const mut = useMutation({
    mutationFn: () => orderApi.reschedule(orderId, { new_date: date, reason }),
    onSuccess: () => {
      toast.success("Delivery rescheduled");
      onDone();
      onClose();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });
  const today = new Date().toISOString().slice(0, 10);
  return (
    <Modal
      open
      onClose={onClose}
      title="Reschedule delivery"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={mut.isPending} disabled={!date} onClick={() => mut.mutate()}>
            Reschedule
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field
          label="New delivery date"
          type="date"
          min={today}
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <Field
          label="Reason (optional)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <p className="text-xs text-slate-400">
          A new delivery attempt is created and a fresh agent auto-assigned.
        </p>
      </div>
    </Modal>
  );
}

function FailModal({ orderId, onClose, onDone }) {
  const [reason, setReason] = useState(FAILURE_REASONS[0]);
  const [notes, setNotes] = useState("");
  const mut = useMutation({
    mutationFn: () => orderApi.fail(orderId, reason, notes),
    onSuccess: () => {
      toast.success("Delivery marked as failed");
      onDone();
      onClose();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });
  return (
    <Modal
      open
      onClose={onClose}
      title="Report failed delivery"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="danger" loading={mut.isPending} onClick={() => mut.mutate()}>
            Mark failed
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <SelectField
          label="Failure reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          options={FAILURE_REASONS.map((r) => ({ value: r, label: humanize(r) }))}
        />
        <Field label="Notes (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
    </Modal>
  );
}

function OverrideModal({ orderId, onClose, onDone }) {
  const [status, setStatus] = useState("CONFIRMED");
  const [reason, setReason] = useState("");
  const mut = useMutation({
    mutationFn: () => adminApi.override(orderId, status, reason),
    onSuccess: () => {
      toast.success("Status overridden");
      onDone();
      onClose();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });
  return (
    <Modal
      open
      onClose={onClose}
      title="Override order status"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={mut.isPending} disabled={!reason} onClick={() => mut.mutate()}>
            Override
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <SelectField
          label="New status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          options={ALL_STATUSES.map((s) => ({ value: s, label: humanize(s) }))}
        />
        <Field
          label="Reason (required, audited)"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <p className="text-xs text-slate-400">
          Overrides are recorded in the tracking timeline and audit log.
        </p>
      </div>
    </Modal>
  );
}
