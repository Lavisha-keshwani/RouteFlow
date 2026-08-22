import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsApi } from "@/lib/api";
import { Card, EmptyState, LoadingBlock, PageHeader } from "@/components/ui";

export default function Analytics() {
  const { data, isLoading } = useQuery({ queryKey: ["analytics"], queryFn: analyticsApi.summary });
  if (isLoading || !data) return <LoadingBlock />;

  const zoneData = data.orders_by_zone.map((z) => ({ name: z.zone, count: z.count }));
  const dailyData = data.daily_volume.map((d) => ({ name: d.date.slice(5), count: d.count }));
  const failureData = Object.entries(data.failure_rate_by_zone).map(([zone, rate]) => ({
    name: zone,
    rate,
  }));

  return (
    <div>
      <PageHeader title="Analytics" subtitle="Delivery performance by zone and over time." />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <h3 className="mb-4 text-base font-semibold text-slate-900">Daily order volume</h3>
          {dailyData.length === 0 ? (
            <EmptyState title="No data yet" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={dailyData} margin={{ top: 8, right: 12, bottom: 8, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#4f46e5"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card>
          <h3 className="mb-4 text-base font-semibold text-slate-900">Orders by pickup zone</h3>
          {zoneData.length === 0 ? (
            <EmptyState title="No data yet" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={zoneData} margin={{ top: 8, right: 12, bottom: 8, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
                <Tooltip cursor={{ fill: "#f1f5f9" }} />
                <Bar dataKey="count" fill="#6366f1" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="mb-4 text-base font-semibold text-slate-900">Failure rate by zone (%)</h3>
          {failureData.length === 0 ? (
            <EmptyState title="No completed attempts yet" />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={failureData} margin={{ top: 8, right: 12, bottom: 8, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip cursor={{ fill: "#f1f5f9" }} />
                <Bar dataKey="rate" radius={[6, 6, 0, 0]}>
                  {failureData.map((entry) => (
                    <Cell key={entry.name} fill={entry.rate > 20 ? "#f43f5e" : "#10b981"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </div>
  );
}
