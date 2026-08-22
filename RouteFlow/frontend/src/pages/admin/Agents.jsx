import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Plus } from "lucide-react";
import { adminApi } from "@/lib/api";
import {
  Button,
  Field,
  LoadingBlock,
  Modal,
  PageHeader,
  Pill,
  SelectField,
  StatusBadge,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/client";
import { formatRelative } from "@/lib/format";

export default function Agents() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "",
    current_zone_id: "",
    max_active_orders: "5",
  });

  const { data: agents, isLoading } = useQuery({
    queryKey: ["admin", "agents"],
    queryFn: adminApi.agents,
  });
  const { data: zones } = useQuery({ queryKey: ["admin", "zones"], queryFn: adminApi.zones });
  const zoneOptions = (zones ?? []).map((z) => ({
    value: String(z.id),
    label: `${z.code} — ${z.name}`,
  }));

  const createMut = useMutation({
    mutationFn: () =>
      adminApi.createAgent({
        full_name: form.full_name,
        email: form.email,
        phone: form.phone || undefined,
        password: form.password,
        current_zone_id: form.current_zone_id ? Number(form.current_zone_id) : undefined,
        max_active_orders: Number(form.max_active_orders),
      }),
    onSuccess: () => {
      toast.success("Agent created");
      setOpen(false);
      setForm({
        full_name: "",
        email: "",
        phone: "",
        password: "",
        current_zone_id: "",
        max_active_orders: "5",
      });
      qc.invalidateQueries({ queryKey: ["admin", "agents"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }) => adminApi.updateAgent(id, { is_active }),
    onSuccess: () => {
      toast.success("Agent updated");
      qc.invalidateQueries({ queryKey: ["admin", "agents"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Delivery agents"
        subtitle="Manage your fleet, capacity and availability."
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New agent
          </Button>
        }
      />

      {isLoading ? (
        <LoadingBlock />
      ) : (
        <Table>
          <thead className="bg-slate-50">
            <tr>
              <Th>Agent</Th>
              <Th>Status</Th>
              <Th>Capacity</Th>
              <Th>Location</Th>
              <Th>Active</Th>
              <Th></Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(agents ?? []).map((a) => (
              <tr key={a.id}>
                <Td>
                  <p className="font-medium text-slate-900">{a.full_name}</p>
                  <p className="text-xs text-slate-400">{a.email}</p>
                </Td>
                <Td>
                  <StatusBadge status={a.status} />
                </Td>
                <Td>
                  <Pill tone="brand">
                    {a.active_orders}/{a.max_active_orders}
                  </Pill>
                </Td>
                <Td className="text-xs text-slate-500">
                  {a.current_latitude
                    ? `${a.current_latitude.toFixed(3)}, ${a.current_longitude?.toFixed(3)}`
                    : "—"}
                  <span className="block text-slate-400">
                    {formatRelative(a.last_location_update)}
                  </span>
                </Td>
                <Td>{a.is_active ? "Yes" : "No"}</Td>
                <Td>
                  <button
                    onClick={() => toggleMut.mutate({ id: a.id, is_active: !a.is_active })}
                    className="text-xs font-medium text-brand-600 hover:text-brand-700"
                  >
                    {a.is_active ? "Deactivate" : "Activate"}
                  </button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Create delivery agent"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={createMut.isPending}
              disabled={!form.full_name || !form.email || form.password.length < 8}
              onClick={() => createMut.mutate()}
            >
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field
            label="Full name"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
          <Field
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-4">
            <Field
              label="Phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
            <Field
              label="Password"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label="Home zone"
              value={form.current_zone_id}
              onChange={(e) => setForm({ ...form, current_zone_id: e.target.value })}
              options={[{ value: "", label: "None" }, ...zoneOptions]}
            />
            <Field
              label="Max active orders"
              type="number"
              min="1"
              value={form.max_active_orders}
              onChange={(e) => setForm({ ...form, max_active_orders: e.target.value })}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}
