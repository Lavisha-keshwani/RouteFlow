import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { MapPin, Navigation, Truck } from "lucide-react";
import { agentApi, orderApi } from "@/lib/api";
import {
  Button,
  Card,
  EmptyState,
  LoadingBlock,
  PageHeader,
  Pill,
  StatCard,
  StatusBadge,
  Table,
  Td,
  Th,
} from "@/components/ui";
import { getErrorMessage } from "@/lib/client";
import { formatRelative, humanize } from "@/lib/format";

const NEXT_STATUS = {
  ASSIGNED: "PICKED_UP",
  PICKED_UP: "IN_TRANSIT",
  IN_TRANSIT: "OUT_FOR_DELIVERY",
  OUT_FOR_DELIVERY: "DELIVERED",
};

const STATUS_OPTIONS = ["AVAILABLE", "BUSY", "OFFLINE"];

export default function AgentDashboard() {
  const qc = useQueryClient();
  const { data: profile, isLoading: loadingProfile } = useQuery({
    queryKey: ["agent", "me"],
    queryFn: agentApi.me,
  });
  const { data: orders, isLoading: loadingOrders } = useQuery({
    queryKey: ["agent", "orders"],
    queryFn: () => orderApi.list({ page: 1, page_size: 50 }),
  });

  const availabilityMut = useMutation({
    mutationFn: (status) => agentApi.setAvailability(status),
    onSuccess: () => {
      toast.success("Availability updated");
      qc.invalidateQueries({ queryKey: ["agent", "me"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const locationMut = useMutation({
    mutationFn: ({ lat, lon }) => agentApi.updateLocation(lat, lon),
    onSuccess: () => {
      toast.success("Location updated");
      qc.invalidateQueries({ queryKey: ["agent", "me"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const statusMut = useMutation({
    mutationFn: ({ id, status }) => orderApi.updateStatus(id, status),
    onSuccess: () => {
      toast.success("Order updated");
      qc.invalidateQueries({ queryKey: ["agent", "orders"] });
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  function shareLocation() {
    if (!navigator.geolocation) {
      toast.error("Geolocation is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => locationMut.mutate({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
      () => toast.error("Could not get your location.")
    );
  }

  if (loadingProfile || !profile) return <LoadingBlock />;

  const activeOrders = (orders?.items ?? []).filter(
    (o) => !["DELIVERED", "CANCELLED"].includes(o.status)
  );

  return (
    <div>
      <PageHeader
        title="My deliveries"
        subtitle="Manage your availability and active assignments."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <h3 className="mb-4 flex items-center gap-2 text-base font-semibold text-slate-900">
            <Truck size={18} className="text-brand-600" /> Status
          </h3>
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm text-slate-500">Current</span>
            <StatusBadge status={profile.status} />
          </div>
          <div className="mb-4 grid grid-cols-3 gap-2">
            {STATUS_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => availabilityMut.mutate(s)}
                disabled={availabilityMut.isPending}
                className={`rounded-lg border px-2 py-2 text-xs font-medium transition ${
                  profile.status === s
                    ? "border-brand-300 bg-brand-50 text-brand-700"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
              >
                {humanize(s)}
              </button>
            ))}
          </div>
          <div className="mb-4 flex items-center justify-between text-sm">
            <span className="text-slate-500">Capacity</span>
            <Pill tone="brand">
              {profile.active_orders}/{profile.max_active_orders}
            </Pill>
          </div>
          <div className="mb-2 flex items-center gap-2 text-sm text-slate-500">
            <MapPin size={14} />
            {profile.current_latitude
              ? `${profile.current_latitude.toFixed(4)}, ${profile.current_longitude?.toFixed(4)}`
              : "No location yet"}
          </div>
          <p className="mb-3 text-xs text-slate-400">
            Updated {formatRelative(profile.last_location_update)}
          </p>
          <Button
            variant="secondary"
            className="w-full"
            loading={locationMut.isPending}
            onClick={shareLocation}
          >
            <Navigation size={16} /> Share my location
          </Button>
        </Card>

        <div className="lg:col-span-2">
          <div className="mb-4 grid grid-cols-2 gap-4">
            <StatCard label="Active deliveries" value={activeOrders.length} accent="text-blue-600" />
            <StatCard
              label="Delivered"
              value={(orders?.items ?? []).filter((o) => o.status === "DELIVERED").length}
              accent="text-emerald-600"
            />
          </div>

          {loadingOrders ? (
            <LoadingBlock />
          ) : activeOrders.length === 0 ? (
            <EmptyState
              title="No active deliveries"
              description="New assignments will appear here."
              icon={<Truck size={40} />}
            />
          ) : (
            <Table>
              <thead className="bg-slate-50">
                <tr>
                  <Th>Order</Th>
                  <Th>Drop</Th>
                  <Th>Status</Th>
                  <Th>Action</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {activeOrders.map((o) => {
                  const next = NEXT_STATUS[o.status];
                  return (
                    <tr key={o.id}>
                      <Td className="font-medium text-slate-900">{o.order_number}</Td>
                      <Td className="max-w-xs truncate text-slate-500">{o.drop_address}</Td>
                      <Td>
                        <StatusBadge status={o.status} />
                      </Td>
                      <Td>
                        {next ? (
                          <Button
                            variant="secondary"
                            loading={statusMut.isPending}
                            onClick={() => statusMut.mutate({ id: o.id, status: next })}
                          >
                            Mark {humanize(next)}
                          </Button>
                        ) : (
                          "—"
                        )}
                      </Td>
                      <Td>
                        <Link
                          to={`/agent/orders/${o.id}`}
                          className="text-sm font-medium text-brand-600 hover:text-brand-700"
                        >
                          Details
                        </Link>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
        </div>
      </div>
    </div>
  );
}
