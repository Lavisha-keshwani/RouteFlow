import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Plus, Trash2 } from "lucide-react";
import { adminApi } from "@/lib/api";
import {
  Button,
  Card,
  Field,
  LoadingBlock,
  Modal,
  PageHeader,
  SelectField,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/client";
import { formatCurrency, formatWeight, humanize } from "@/lib/format";

const COMBOS = [
  { order_type: "B2C", zone_type: "INTRA_ZONE" },
  { order_type: "B2C", zone_type: "INTER_ZONE" },
  { order_type: "B2B", zone_type: "INTRA_ZONE" },
  { order_type: "B2B", zone_type: "INTER_ZONE" },
];

export default function Rates() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    order_type: "B2C",
    zone_type: "INTRA_ZONE",
    min_weight_kg: "0",
    max_weight_kg: "5",
    base_charge: "60",
  });

  const { data: rates, isLoading } = useQuery({
    queryKey: ["admin", "rates"],
    queryFn: () => adminApi.rates(),
  });

  const createMut = useMutation({
    mutationFn: () =>
      adminApi.createRate({
        order_type: form.order_type,
        zone_type: form.zone_type,
        min_weight_kg: form.min_weight_kg,
        max_weight_kg: form.max_weight_kg,
        base_charge: form.base_charge,
      }),
    onSuccess: () => {
      toast.success("Rate card created");
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["admin", "rates"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const deleteMut = useMutation({
    mutationFn: (id) => adminApi.deleteRate(id),
    onSuccess: () => {
      toast.success("Rate card deleted");
      qc.invalidateQueries({ queryKey: ["admin", "rates"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const grouped = (combo) =>
    (rates ?? [])
      .filter((r) => r.order_type === combo.order_type && r.zone_type === combo.zone_type)
      .sort((a, b) => Number(a.min_weight_kg) - Number(b.min_weight_kg));

  return (
    <div>
      <PageHeader
        title="Rate cards"
        subtitle="Configure pricing by order type, zone type and weight bracket. No redeploy needed."
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} /> New rate
          </Button>
        }
      />

      {isLoading ? (
        <LoadingBlock />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {COMBOS.map((combo) => (
            <Card key={`${combo.order_type}-${combo.zone_type}`}>
              <h3 className="mb-3 text-sm font-semibold text-slate-900">
                {combo.order_type} · {humanize(combo.zone_type)}
              </h3>
              <Table>
                <thead className="bg-slate-50">
                  <tr>
                    <Th>Weight bracket</Th>
                    <Th>Base charge</Th>
                    <Th></Th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {grouped(combo).map((r) => (
                    <tr key={r.id}>
                      <Td>
                        {formatWeight(r.min_weight_kg)} – {formatWeight(r.max_weight_kg)}
                      </Td>
                      <Td className="font-medium">{formatCurrency(r.base_charge, r.currency)}</Td>
                      <Td>
                        <button
                          onClick={() => deleteMut.mutate(r.id)}
                          className="text-slate-400 hover:text-rose-600"
                          title="Delete"
                        >
                          <Trash2 size={16} />
                        </button>
                      </Td>
                    </tr>
                  ))}
                  {grouped(combo).length === 0 && (
                    <tr>
                      <Td className="text-slate-400">No brackets configured</Td>
                      <Td></Td>
                      <Td></Td>
                    </tr>
                  )}
                </tbody>
              </Table>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Create rate card"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button loading={createMut.isPending} onClick={() => createMut.mutate()}>
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label="Order type"
              value={form.order_type}
              onChange={(e) => setForm({ ...form, order_type: e.target.value })}
              options={[
                { value: "B2C", label: "B2C" },
                { value: "B2B", label: "B2B" },
              ]}
            />
            <SelectField
              label="Zone type"
              value={form.zone_type}
              onChange={(e) => setForm({ ...form, zone_type: e.target.value })}
              options={[
                { value: "INTRA_ZONE", label: "Intra-zone" },
                { value: "INTER_ZONE", label: "Inter-zone" },
              ]}
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <Field
              label="Min kg"
              type="number"
              step="0.001"
              value={form.min_weight_kg}
              onChange={(e) => setForm({ ...form, min_weight_kg: e.target.value })}
            />
            <Field
              label="Max kg"
              type="number"
              step="0.001"
              value={form.max_weight_kg}
              onChange={(e) => setForm({ ...form, max_weight_kg: e.target.value })}
            />
            <Field
              label="Base ₹"
              type="number"
              step="0.01"
              value={form.base_charge}
              onChange={(e) => setForm({ ...form, base_charge: e.target.value })}
            />
          </div>
          <p className="text-xs text-slate-400">
            Brackets are half-open (min, max]. Overlapping brackets are rejected.
          </p>
        </div>
      </Modal>
    </div>
  );
}
