import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Package } from "lucide-react";
import { adminApi } from "@/lib/api";
import {
  EmptyState,
  LoadingBlock,
  PageHeader,
  SelectField,
  StatusBadge,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { Pagination } from "@/pages/customer/Orders";
import { formatCurrency, formatRelative, humanize } from "@/lib/format";

const STATUSES = [
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

export default function AdminOrders() {
  const [filters, setFilters] = useState({ status: "", order_type: "", payment_type: "" });
  const [page, setPage] = useState(1);

  const params = { page, page_size: 12 };
  if (filters.status) params.status = filters.status;
  if (filters.order_type) params.order_type = filters.order_type;
  if (filters.payment_type) params.payment_type = filters.payment_type;

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "orders", { ...filters, page }],
    queryFn: () => adminApi.orders(params),
  });

  function update(key, value) {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  }

  return (
    <div>
      <PageHeader title="All orders" subtitle="Filter, inspect and manage every delivery order." />

      <div className="mb-4 grid gap-3 sm:grid-cols-3 lg:w-2/3">
        <SelectField
          value={filters.status}
          onChange={(e) => update("status", e.target.value)}
          options={[
            { value: "", label: "All statuses" },
            ...STATUSES.map((s) => ({ value: s, label: humanize(s) })),
          ]}
        />
        <SelectField
          value={filters.order_type}
          onChange={(e) => update("order_type", e.target.value)}
          options={[
            { value: "", label: "All types" },
            { value: "B2C", label: "B2C" },
            { value: "B2B", label: "B2B" },
          ]}
        />
        <SelectField
          value={filters.payment_type}
          onChange={(e) => update("payment_type", e.target.value)}
          options={[
            { value: "", label: "All payments" },
            { value: "PREPAID", label: "Prepaid" },
            { value: "COD", label: "COD" },
          ]}
        />
      </div>

      {isLoading ? (
        <LoadingBlock />
      ) : !data || data.items.length === 0 ? (
        <EmptyState title="No orders match your filters" icon={<Package size={40} />} />
      ) : (
        <>
          <Table>
            <thead className="bg-slate-50">
              <tr>
                <Th>Order</Th>
                <Th>Type</Th>
                <Th>Payment</Th>
                <Th>Zone</Th>
                <Th>Amount</Th>
                <Th>Agent</Th>
                <Th>Status</Th>
                <Th>Created</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((o) => (
                <tr key={o.id} className="hover:bg-slate-50">
                  <Td className="font-medium text-slate-900">{o.order_number}</Td>
                  <Td>{o.order_type}</Td>
                  <Td>{humanize(o.payment_type)}</Td>
                  <Td>{humanize(o.zone_type)}</Td>
                  <Td>{formatCurrency(o.total_charge, o.currency)}</Td>
                  <Td>{o.assigned_agent_id ? `#${o.assigned_agent_id}` : "—"}</Td>
                  <Td>
                    <StatusBadge status={o.status} />
                  </Td>
                  <Td className="text-slate-400">{formatRelative(o.created_at)}</Td>
                  <Td>
                    <Link
                      to={`/admin/orders/${o.id}`}
                      className="text-sm font-medium text-brand-600 hover:text-brand-700"
                    >
                      Manage
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />
        </>
      )}
    </div>
  );
}
