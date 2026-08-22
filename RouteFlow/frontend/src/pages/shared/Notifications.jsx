import { useQuery } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { notificationApi } from "@/lib/api";
import { EmptyState, LoadingBlock, PageHeader, StatusBadge, Table, Td, Th } from "@/components/ui";
import { formatRelative, humanize } from "@/lib/format";

export default function Notifications() {
  const { data, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationApi.list({ page: 1, page_size: 50 }),
  });

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle="Delivery updates sent to you at every status change."
      />
      {isLoading ? (
        <LoadingBlock />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          title="No notifications yet"
          description="You'll see delivery updates here."
          icon={<Bell size={40} />}
        />
      ) : (
        <Table>
          <thead className="bg-slate-50">
            <tr>
              <Th>Event</Th>
              <Th>Channel</Th>
              <Th>Message</Th>
              <Th>Status</Th>
              <Th>When</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.items.map((n) => (
              <tr key={n.id}>
                <Td className="font-medium text-slate-800">{humanize(n.event_type)}</Td>
                <Td>{n.channel}</Td>
                <Td className="max-w-md text-slate-500">{n.message}</Td>
                <Td>
                  <StatusBadge status={n.status} />
                </Td>
                <Td className="text-slate-400">{formatRelative(n.created_at)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
