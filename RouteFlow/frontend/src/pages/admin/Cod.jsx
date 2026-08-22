import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Wallet } from "lucide-react";
import { adminApi } from "@/lib/api";
import { Button, Card, Field, LoadingBlock, PageHeader } from "@/components/ui";
import { getErrorMessage } from "@/lib/client";

const TYPES = ["B2C", "B2B"];

export default function Cod() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin", "cod"],
    queryFn: adminApi.codSurcharges,
  });
  const [amounts, setAmounts] = useState({});

  useEffect(() => {
    if (data) {
      const map = {};
      data.forEach((c) => (map[c.order_type] = c.amount));
      setAmounts((prev) => ({ ...map, ...prev }));
    }
  }, [data]);

  const upsertMut = useMutation({
    mutationFn: ({ order_type, amount }) => adminApi.upsertCod({ order_type, amount }),
    onSuccess: () => {
      toast.success("COD surcharge saved");
      qc.invalidateQueries({ queryKey: ["admin", "cod"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  if (isLoading) return <LoadingBlock />;

  return (
    <div>
      <PageHeader
        title="COD surcharges"
        subtitle="Extra charge applied to cash-on-delivery orders, per order type."
      />

      <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
        {TYPES.map((type) => (
          <Card key={type}>
            <div className="mb-4 flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <Wallet size={18} />
              </div>
              <div>
                <p className="font-semibold text-slate-900">{type}</p>
                <p className="text-xs text-slate-400">COD surcharge (₹)</p>
              </div>
            </div>
            <Field
              type="number"
              step="0.01"
              min="0"
              value={amounts[type] ?? ""}
              onChange={(e) => setAmounts({ ...amounts, [type]: e.target.value })}
            />
            <Button
              className="mt-3 w-full"
              loading={upsertMut.isPending && upsertMut.variables?.order_type === type}
              onClick={() => upsertMut.mutate({ order_type: type, amount: Number(amounts[type] || 0) })}
            >
              Save
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
