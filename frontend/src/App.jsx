import { Navigate, Route, Routes } from "react-router-dom";
import { LoadingBlock } from "@/components/ui";
import { Layout } from "@/components/Layout";
import { useAuth } from "@/context/AuthContext";

import Login from "@/pages/auth/Login";
import Register from "@/pages/auth/Register";
import CustomerDashboard from "@/pages/customer/Dashboard";
import CreateOrder from "@/pages/customer/CreateOrder";
import Orders from "@/pages/customer/Orders";
import OrderDetail from "@/pages/shared/OrderDetail";
import Notifications from "@/pages/shared/Notifications";
import AdminDashboard from "@/pages/admin/Dashboard";
import AdminOrders from "@/pages/admin/Orders";
import Zones from "@/pages/admin/Zones";
import Areas from "@/pages/admin/Areas";
import Rates from "@/pages/admin/Rates";
import Cod from "@/pages/admin/Cod";
import Agents from "@/pages/admin/Agents";
import Analytics from "@/pages/admin/Analytics";
import AgentDashboard from "@/pages/agent/Dashboard";

function homePath(role) {
  if (role === "ADMIN") return "/admin";
  if (role === "DELIVERY_AGENT") return "/agent";
  return "/";
}

function RequireRole({ roles, children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingBlock />;
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to={homePath(user.role)} replace />;
  return children;
}

export default function App() {
  const { user, loading } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to={homePath(user.role)} replace /> : <Login />}
      />
      <Route
        path="/register"
        element={user ? <Navigate to={homePath(user.role)} replace /> : <Register />}
      />

      {/* Customer */}
      <Route
        element={
          <RequireRole roles={["CUSTOMER"]}>
            <Layout />
          </RequireRole>
        }
      >
        <Route path="/" element={<CustomerDashboard />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/new" element={<CreateOrder />} />
        <Route path="/orders/:id" element={<OrderDetail />} />
        <Route path="/notifications" element={<Notifications />} />
      </Route>

      {/* Admin */}
      <Route
        element={
          <RequireRole roles={["ADMIN"]}>
            <Layout />
          </RequireRole>
        }
      >
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/orders" element={<AdminOrders />} />
        <Route path="/admin/orders/:id" element={<OrderDetail />} />
        <Route path="/admin/zones" element={<Zones />} />
        <Route path="/admin/areas" element={<Areas />} />
        <Route path="/admin/rates" element={<Rates />} />
        <Route path="/admin/cod" element={<Cod />} />
        <Route path="/admin/agents" element={<Agents />} />
        <Route path="/admin/analytics" element={<Analytics />} />
      </Route>

      {/* Agent */}
      <Route
        element={
          <RequireRole roles={["DELIVERY_AGENT"]}>
            <Layout />
          </RequireRole>
        }
      >
        <Route path="/agent" element={<AgentDashboard />} />
        <Route path="/agent/orders/:id" element={<OrderDetail />} />
      </Route>

      <Route
        path="*"
        element={
          loading ? (
            <LoadingBlock />
          ) : (
            <Navigate to={user ? homePath(user.role) : "/login"} replace />
          )
        }
      />
    </Routes>
  );
}
