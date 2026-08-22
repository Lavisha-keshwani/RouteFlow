import { useQuery } from "@tanstack/react-query";
import { IndianRupee, Package, TrendingUp, Users } from "lucide-react";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { analyticsApi } from "@/lib/api";
import { Card, LoadingBlock, PageHeader, StatCard } from "@/components/ui";
import { formatCurrency, humanize } from "@/lib/format";

const STATUS_COLORS = {
  PENDING_CONFIRMATION: "#f59e0b",
  CONFIRMED: "#0ea5e9",
  ASSIGNED: "#6366f1",
  PICKED_UP: "#8b5cf6",
  IN_TRANSIT: "#3b82f6",
  OUT_FOR_DELIVERY: "#06b6d4",
  DELIVERED: "#10b981",
  FAILED: "#f43f5e",
  RESCHEDULED: "#f97316",
  CANCELLED: "#94a3b8",
};

export default function AdminDashboard() {
  const { data, isLoading } = useQuery({ queryKey: ["analytics"], queryFn: analyticsApi.summary });
  if (isLoading || !data) return <LoadingBlock />;

  const statusData = data.orders_by_status.map((s) => ({
    name: humanize(s.status),
    key: s.status,
    count: s.count,
  }));

  return (
    <div>
      <PageHeader title="Operations dashboard" subtitle="Live overview of delivery performance." />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Total orders"
          value={data.total_orders}
          hint={`${data.active_orders} active`}
        />
        <StatCard
          label="Realized revenue"
          value={formatCurrency(data.revenue)}
          accent="text-emerald-600"
          hint={`Avg ${formatCurrency(data.average_order_value)}`}
        />
        <StatCard
          label="Success rate"
          value={`${data.delivery_success_rate}%`}
          accent="text-brand-600"
          hint={`${data.failed_delivery_rate}% failed`}
        />
        <StatCard
          label="Agent utilization"
          value={`${data.agent_utilization}%`}
          accent="text-indigo-600"
          hint={`${data.cod_percentage}% COD orders`}
        />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h3 className="mb-4 text-base font-semibold text-slate-900">Orders by status</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={statusData} margin={{ top: 8, right: 8, bottom: 8, left: -18 }}>
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={60}
              />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
              <Tooltip cursor={{ fill: "#f1f5f9" }} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {statusData.map((entry) => (
                  <Cell key={entry.key} fill={STATUS_COLORS[entry.key] ?? "#6366f1"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <div className="space-y-4">
          <MiniStat icon={<Package size={18} />} label="Pending confirmation" value={data.pending} />
          <MiniStat icon={<TrendingUp size={18} />} label="Delivered" value={data.delivered} />
          <MiniStat icon={<Users size={18} />} label="COD orders" value={data.cod_orders} />
          <MiniStat icon={<IndianRupee size={18} />} label="Failed" value={data.failed} />
        </div>
      </div>
    </div>
  );
}

function MiniStat({ icon, label, value }) {
  return (
    <div className="card flex items-center gap-3 p-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
        {icon}
      </div>
      <div>
        <p className="text-sm text-slate-500">{label}</p>
        <p className="text-xl font-bold text-slate-900">{value}</p>
      </div>
    </div>
  );
}
