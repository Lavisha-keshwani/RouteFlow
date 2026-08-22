import { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { Boxes, Truck, ShieldCheck, User as UserIcon } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button, Field } from "@/components/ui";
import { getErrorMessage } from "@/lib/client";

const DEMO = [
  { label: "Admin", email: "admin@routeflow.app", icon: ShieldCheck },
  { label: "Customer", email: "customer@routeflow.app", icon: UserIcon },
  { label: "Agent", email: "agent@routeflow.app", icon: Truck },
];
const DEMO_PASSWORD = "Password123!";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm();

  async function onSubmit(values) {
    setSubmitting(true);
    try {
      const user = await login(values.email, values.password);
      toast.success(`Welcome back, ${user.full_name.split(" ")[0]}!`);
      navigate(
        user.role === "ADMIN" ? "/admin" : user.role === "DELIVERY_AGENT" ? "/agent" : "/"
      );
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function quickLogin(email) {
    setValue("email", email);
    setValue("password", DEMO_PASSWORD);
    await onSubmit({ email, password: DEMO_PASSWORD });
  }

  return (
    <div className="flex min-h-screen">
      <div className="hidden w-1/2 flex-col justify-between bg-brand-700 p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15">
            <Boxes size={24} />
          </div>
          <span className="text-xl font-bold">RouteFlow</span>
        </div>
        <div>
          <h1 className="text-4xl font-bold leading-tight">
            Last-mile delivery,
            <br />
            engineered end to end.
          </h1>
          <p className="mt-4 max-w-md text-brand-100">
            Configurable rate engine, automatic zone detection, intelligent agent assignment and an
            immutable tracking timeline — in one operations dashboard.
          </p>
          <ul className="mt-8 space-y-2 text-sm text-brand-100">
            <li>• Transparent, explainable pricing</li>
            <li>• Smart auto-assignment with scoring</li>
            <li>• Failure-aware reschedule workflow</li>
          </ul>
        </div>
        <p className="text-sm text-brand-200">© {new Date().getFullYear()} RouteFlow</p>
      </div>

      <div className="flex w-full items-center justify-center p-6 lg:w-1/2">
        <div className="w-full max-w-sm">
          <h2 className="text-2xl font-bold text-slate-900">Sign in</h2>
          <p className="mt-1 text-sm text-slate-500">Access your delivery dashboard.</p>

          <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
            <Field
              label="Email"
              type="email"
              placeholder="you@example.com"
              error={errors.email?.message}
              {...register("email", { required: "Email is required" })}
            />
            <Field
              label="Password"
              type="password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register("password", { required: "Password is required" })}
            />
            <Button type="submit" loading={submitting} className="w-full">
              Sign in
            </Button>
          </form>

          <div className="mt-6">
            <p className="mb-2 text-center text-xs font-medium uppercase tracking-wide text-slate-400">
              Quick demo login
            </p>
            <div className="grid grid-cols-3 gap-2">
              {DEMO.map((d) => (
                <button
                  key={d.label}
                  onClick={() => quickLogin(d.email)}
                  disabled={submitting}
                  className="flex flex-col items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-3 text-xs font-medium text-slate-600 transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 disabled:opacity-60"
                >
                  <d.icon size={18} />
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <p className="mt-6 text-center text-sm text-slate-500">
            No account?{" "}
            <Link to="/register" className="font-semibold text-brand-600 hover:text-brand-700">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
