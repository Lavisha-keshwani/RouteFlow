import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Map, Plus } from "lucide-react";
import { adminApi } from "@/lib/api";
import {
  Button,
  Card,
  Field,
  LoadingBlock,
  Modal,
  PageHeader,
  Pill,
  StatusBadge,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/client";

export default function Zones() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", city: "" });

  const { data: zones, isLoading } = useQuery({
    queryKey: ["admin", "zones"],
    queryFn: adminApi.zones,
  });

  const createMut = useMutation({
    mutationFn: () => adminApi.createZone(form),
    onSuccess: () => {
      toast.success("Zone created");
      setOpen(false);
      setForm({ code: "", name: "", city: "" });
      qc.invalidateQueries({ queryKey: ["admin", "zones"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }) => adminApi.updateZone(id, { is_active }),
    onSuccess: () => {
      toast.success("Zone updated");
      qc.invalidateQueries({ queryKey: ["admin", "zones"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Zones"
        subtitle="Serviceable zones used for pricing and assignment."
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New zone
          </Button>
        }
      />

      {isLoading ? (
        <LoadingBlock />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(zones ?? []).map((z) => (
            <Card key={z.id}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                    <Map size={18} />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900">{z.code}</p>
                    <p className="text-xs text-slate-400">{z.name}</p>
                  </div>
                </div>
                <StatusBadge status={z.is_active ? "AVAILABLE" : "OFFLINE"} />
              </div>
              <p className="mt-3 text-sm text-slate-500">{z.city}</p>
              <div className="mt-3 flex flex-wrap gap-1">
                {(z.areas ?? []).slice(0, 6).map((a) => (
                  <Pill key={a.id}>{a.name}</Pill>
                ))}
                {(z.areas?.length ?? 0) > 6 && (
                  <Pill tone="brand">+{(z.areas?.length ?? 0) - 6}</Pill>
                )}
              </div>
              <button
                onClick={() => toggleMut.mutate({ id: z.id, is_active: !z.is_active })}
                className="mt-4 text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                {z.is_active ? "Deactivate" : "Activate"}
              </button>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Create zone"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={createMut.isPending}
              disabled={!form.code || !form.name || !form.city}
              onClick={() => createMut.mutate()}
            >
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field
            label="Code"
            placeholder="CHN-05"
            value={form.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
          />
          <Field
            label="Name"
            placeholder="Chennai West"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Field
            label="City"
            placeholder="Chennai"
            value={form.city}
            onChange={(e) => setForm({ ...form, city: e.target.value })}
          />
        </div>
      </Modal>
    </div>
  );
}
