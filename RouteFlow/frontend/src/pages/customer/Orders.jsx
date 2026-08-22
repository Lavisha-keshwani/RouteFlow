import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Package } from "lucide-react";
import { orderApi } from "@/lib/api";
import {
  Button,
  EmptyState,
  LoadingBlock,
  PageHeader,
  SelectField,
  StatusBadge,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { formatCurrency, formatRelative, humanize } from "@/lib/format";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  ...[
    "PENDING_CONFIRMATION",
    "CONFIRMED",
    "ASSIGNED",
    "PICKED_UP",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "FAILED",
    "RESCHEDULED",
  ].map((s) => ({ value: s, label: humanize(s) })),
];

export default function Orders() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["orders", { status, page }],
    queryFn: () => orderApi.list({ page, page_size: 10, ...(status ? { status } : {}) }),
  });

  return (
    <div>
      <PageHeader
        title="My orders"
        subtitle="Track and manage all your delivery orders."
        action={
          <Link to="/orders/new">
            <Button>New order</Button>
          </Link>
        }
      />

      <div className="mb-4 w-56">
        <SelectField
          options={STATUS_OPTIONS}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {isLoading ? (
        <LoadingBlock />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No orders found"
          description="Try a different filter or create a new order."
          icon={<Package size={40} />}
        />
      ) : (
        <>
          <Table>
            <thead className="bg-slate-50">
              <tr>
                <Th>Order</Th>
                <Th>Type</Th>
                <Th>Payment</Th>
                <Th>Amount</Th>
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
                  <Td>{formatCurrency(o.total_charge, o.currency)}</Td>
                  <Td>
                    <StatusBadge status={o.status} />
                  </Td>
                  <Td className="text-slate-400">{formatRelative(o.created_at)}</Td>
                  <Td>
                    <Link
                      to={`/orders/${o.id}`}
                      className="text-sm font-medium text-brand-600 hover:text-brand-700"
                    >
                      View
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

export function Pagination({ page, pages, total, onChange }) {
  if (total === 0) return null;
  return (
    <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
      <span>
        Page {page} of {pages || 1} · {total} total
      </span>
      <div className="flex gap-2">
        <Button variant="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          Previous
        </Button>
        <Button variant="secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Next
        </Button>
      </div>
    </div>
  );
}
