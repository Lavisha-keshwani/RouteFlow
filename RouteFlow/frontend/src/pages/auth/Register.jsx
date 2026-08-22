import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Boxes } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button, Field } from "@/components/ui";
import { getErrorMessage } from "@/lib/client";

export default function Register() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  async function onSubmit(values) {
    setSubmitting(true);
    try {
      await registerUser(values);
      toast.success("Account created!");
      navigate("/");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
            <Boxes size={22} />
          </div>
          <span className="text-xl font-bold text-slate-900">RouteFlow</span>
        </div>
        <div className="card p-6">
          <h2 className="text-xl font-bold text-slate-900">Create your account</h2>
          <p className="mt-1 text-sm text-slate-500">Start creating and tracking deliveries.</p>
          <form onSubmit={handleSubmit(onSubmit)} className="mt-5 space-y-4">
            <Field
              label="Full name"
              error={errors.full_name?.message}
              {...register("full_name", { required: "Name is required" })}
            />
            <Field
              label="Email"
              type="email"
              error={errors.email?.message}
              {...register("email", { required: "Email is required" })}
            />
            <Field label="Phone (optional)" {...register("phone")} />
            <Field
              label="Password"
              type="password"
              error={errors.password?.message}
              {...register("password", {
                required: "Password is required",
                minLength: { value: 8, message: "At least 8 characters" },
              })}
            />
            <Button type="submit" loading={submitting} className="w-full">
              Create account
            </Button>
          </form>
          <p className="mt-5 text-center text-sm text-slate-500">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-700">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
