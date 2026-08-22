import {
  BarChart3,
  Bell,
  Boxes,
  LayoutDashboard,
  LogOut,
  Map,
  MapPin,
  Package,
  PlusCircle,
  Receipt,
  Truck,
  Users,
  Wallet,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { cn, humanize } from "@/lib/format";

const NAV = {
  CUSTOMER: [
    { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/orders/new", label: "Create Order", icon: PlusCircle },
    { to: "/orders", label: "My Orders", icon: Package, end: true },
    { to: "/notifications", label: "Notifications", icon: Bell },
  ],
  ADMIN: [
    { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/admin/orders", label: "Orders", icon: Package },
    { to: "/admin/zones", label: "Zones", icon: Map },
    { to: "/admin/areas", label: "Areas", icon: MapPin },
    { to: "/admin/rates", label: "Rate Cards", icon: Receipt },
    { to: "/admin/cod", label: "COD Surcharges", icon: Wallet },
    { to: "/admin/agents", label: "Agents", icon: Users },
    { to: "/admin/analytics", label: "Analytics", icon: BarChart3 },
  ],
  DELIVERY_AGENT: [{ to: "/agent", label: "My Deliveries", icon: Truck, end: true }],
};

export function Layout() {
  const { user, logout } = useAuth();
  if (!user) return null;
  const items = NAV[user.role] ?? [];

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-slate-200 bg-white lg:flex">
        <div className="flex items-center gap-2 px-6 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white">
            <Boxes size={20} />
          </div>
          <div>
            <p className="text-base font-bold leading-tight text-slate-900">RouteFlow</p>
            <p className="text-xs text-slate-400">Delivery Platform</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-2">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition",
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                )
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-slate-100 p-3">
          <div className="mb-2 px-3">
            <p className="truncate text-sm font-semibold text-slate-800">{user.full_name}</p>
            <p className="truncate text-xs text-slate-400">{humanize(user.role)}</p>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-rose-50 hover:text-rose-600"
          >
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-slate-200 bg-white/80 px-6 py-3 backdrop-blur lg:hidden">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white">
              <Boxes size={18} />
            </div>
            <span className="font-bold text-slate-900">RouteFlow</span>
          </div>
          <button onClick={logout} className="text-slate-500">
            <LogOut size={18} />
          </button>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
