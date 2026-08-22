import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Plus } from "lucide-react";
import { adminApi } from "@/lib/api";
import {
  Button,
  EmptyState,
  Field,
  LoadingBlock,
  Modal,
  PageHeader,
  SelectField,
  StatusBadge,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/client";

export default function Areas() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", zone_id: 0 });
  const [zoneFilter, setZoneFilter] = useState("");

  const { data: zones } = useQuery({ queryKey: ["admin", "zones"], queryFn: adminApi.zones });
  const { data: areas, isLoading } = useQuery({
    queryKey: ["admin", "areas", zoneFilter],
    queryFn: () => adminApi.areas(zoneFilter ? Number(zoneFilter) : undefined),
  });

  const zoneOptions = (zones ?? []).map((z) => ({
    value: String(z.id),
    label: `${z.code} — ${z.name}`,
  }));
  const zoneName = (id) => zones?.find((z) => z.id === id)?.code ?? `#${id}`;

  const createMut = useMutation({
    mutationFn: () => adminApi.createArea({ name: form.name, zone_id: form.zone_id }),
    onSuccess: () => {
      toast.success("Area created");
      setOpen(false);
      setForm({ name: "", zone_id: 0 });
      qc.invalidateQueries({ queryKey: ["admin", "areas"] });
      qc.invalidateQueries({ queryKey: ["admin", "zones"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const moveMut = useMutation({
    mutationFn: ({ id, zone_id }) => adminApi.updateArea(id, { zone_id }),
    onSuccess: () => {
      toast.success("Area moved");
      qc.invalidateQueries({ queryKey: ["admin", "areas"] });
      qc.invalidateQueries({ queryKey: ["admin", "zones"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Areas"
        subtitle="Map areas to zones. Address zone detection uses this mapping."
        action={
          <Button onClick={() => setOpen(true)} disabled={!zones?.length}>
            <Plus size={16} /> New area
          </Button>
        }
      />

      <div className="mb-4 w-64">
        <SelectField
          value={zoneFilter}
          onChange={(e) => setZoneFilter(e.target.value)}
          options={[{ value: "", label: "All zones" }, ...zoneOptions]}
        />
      </div>

      {isLoading ? (
        <LoadingBlock />
      ) : !areas || areas.length === 0 ? (
        <EmptyState title="No areas yet" description="Create an area and map it to a zone." />
      ) : (
        <Table>
          <thead className="bg-slate-50">
            <tr>
              <Th>Area</Th>
              <Th>Zone</Th>
              <Th>Status</Th>
              <Th>Move to zone</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {areas.map((a) => (
              <tr key={a.id}>
                <Td className="font-medium text-slate-900">{a.name}</Td>
                <Td>{zoneName(a.zone_id)}</Td>
                <Td>
                  <StatusBadge status={a.is_active ? "AVAILABLE" : "OFFLINE"} />
                </Td>
                <Td>
                  <select
                    className="input max-w-[200px]"
                    value={a.zone_id}
                    onChange={(e) => moveMut.mutate({ id: a.id, zone_id: Number(e.target.value) })}
                  >
                    {zoneOptions.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Create area"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              loading={createMut.isPending}
              disabled={!form.name || !form.zone_id}
              onClick={() => createMut.mutate()}
            >
              Create
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field
            label="Area name"
            placeholder="Mylapore"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <SelectField
            label="Zone"
            value={String(form.zone_id || "")}
            onChange={(e) => setForm({ ...form, zone_id: Number(e.target.value) })}
            options={[{ value: "", label: "Select a zone" }, ...zoneOptions]}
          />
        </div>
      </Modal>
    </div>
  );
}
