import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Package, PlusCircle } from "lucide-react";
import { orderApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  Button,
  EmptyState,
  LoadingBlock,
  PageHeader,
  StatCard,
  StatusBadge,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { formatCurrency, formatRelative } from "@/lib/format";

const ACTIVE = ["CONFIRMED", "ASSIGNED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "RESCHEDULED"];

export default function CustomerDashboard() {
  const { user } = useAuth();
  const { data, isLoading } = useQuery({
    queryKey: ["orders", "dashboard"],
    queryFn: () => orderApi.list({ page: 1, page_size: 100 }),
  });

  if (isLoading) return <LoadingBlock />;
  const orders = data?.items ?? [];
  const total = data?.total ?? 0;
  const active = orders.filter((o) => ACTIVE.includes(o.status)).length;
  const delivered = orders.filter((o) => o.status === "DELIVERED").length;
  const failed = orders.filter((o) => o.status === "FAILED").length;

  return (
    <div>
      <PageHeader
        title={`Hi ${user?.full_name.split(" ")[0]} 👋`}
        subtitle="Here's an overview of your deliveries."
        action={
          <Link to="/orders/new">
            <Button>
              <PlusCircle size={16} /> New order
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total orders" value={total} />
        <StatCard label="Active" value={active} accent="text-blue-600" />
        <StatCard label="Delivered" value={delivered} accent="text-emerald-600" />
        <StatCard label="Failed" value={failed} accent="text-rose-600" />
      </div>

      <div className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Recent orders</h2>
          <Link to="/orders" className="text-sm font-medium text-brand-600 hover:text-brand-700">
            View all
          </Link>
        </div>
        {orders.length === 0 ? (
          <EmptyState
            title="No orders yet"
            description="Create your first delivery order to see it here."
            icon={<Package size={40} />}
          />
        ) : (
          <Table>
            <thead className="bg-slate-50">
              <tr>
                <Th>Order</Th>
                <Th>Route</Th>
                <Th>Amount</Th>
                <Th>Status</Th>
                <Th>Created</Th>
                <Th></Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {orders.slice(0, 6).map((o) => (
                <tr key={o.id} className="hover:bg-slate-50">
                  <Td className="font-medium text-slate-900">{o.order_number}</Td>
                  <Td className="text-slate-500">
                    {o.zone_type === "INTRA_ZONE" ? "Intra-zone" : "Inter-zone"}
                  </Td>
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
                      Track
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>
    </div>
  );
}
