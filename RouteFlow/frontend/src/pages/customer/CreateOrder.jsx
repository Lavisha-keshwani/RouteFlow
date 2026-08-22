import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { Calculator, PackageCheck, ArrowRight } from "lucide-react";
import { orderApi } from "@/lib/api";
import { Button, Card, Field, PageHeader, Pill, SelectField } from "@/components/ui";
import { getErrorMessage } from "@/lib/client";
import { formatCurrency, formatWeight, humanize } from "@/lib/format";

export default function CreateOrder() {
  const navigate = useNavigate();
  const [quote, setQuote] = useState(null);
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm({
    defaultValues: { order_type: "B2C", payment_type: "PREPAID" },
  });

  const quoteMutation = useMutation({
    mutationFn: (payload) => orderApi.quote(payload),
    onSuccess: (data) => {
      setQuote(data);
      toast.success("Quote calculated");
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const createMutation = useMutation({
    mutationFn: (payload) => orderApi.create(payload, crypto.randomUUID()),
    onSuccess: (order) => {
      toast.success(`Order ${order.order_number} created`);
      navigate(`/orders/${order.id}`);
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  function numberField(name, label) {
    return (
      <Field
        label={label}
        type="number"
        step="0.01"
        min="0"
        error={errors[name]?.message}
        {...register(name, {
          required: "Required",
          valueAsNumber: true,
          min: { value: 0.01, message: "Must be > 0" },
        })}
      />
    );
  }

  return (
    <div>
      <PageHeader
        title="Create order"
        subtitle="Enter package details to get a transparent price quote."
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <Card className="lg:col-span-3">
          <form onSubmit={handleSubmit((v) => quoteMutation.mutate(v))} className="space-y-4">
            <Field
              label="Pickup address"
              placeholder="12 Gandhi Road, Velachery"
              error={errors.pickup_address?.message}
              {...register("pickup_address", { required: "Pickup address is required" })}
            />
            <Field
              label="Drop address"
              placeholder="5 North Usman Road, T Nagar"
              error={errors.drop_address?.message}
              {...register("drop_address", { required: "Drop address is required" })}
            />

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {numberField("length_cm", "Length (cm)")}
              {numberField("width_cm", "Width (cm)")}
              {numberField("height_cm", "Height (cm)")}
              {numberField("actual_weight_kg", "Weight (kg)")}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <SelectField
                label="Order type"
                options={[
                  { value: "B2C", label: "B2C" },
                  { value: "B2B", label: "B2B" },
                ]}
                {...register("order_type")}
              />
              <SelectField
                label="Payment type"
                options={[
                  { value: "PREPAID", label: "Prepaid" },
                  { value: "COD", label: "Cash on Delivery" },
                ]}
                {...register("payment_type")}
              />
            </div>

            <Button
              type="submit"
              variant="secondary"
              loading={quoteMutation.isPending}
              className="w-full"
            >
              <Calculator size={16} /> Calculate price
            </Button>
          </form>
        </Card>

        <div className="lg:col-span-2">
          <Card className="sticky top-6">
            <h3 className="flex items-center gap-2 text-base font-semibold text-slate-900">
              <PackageCheck size={18} className="text-brand-600" /> Price breakdown
            </h3>
            {!quote ? (
              <p className="mt-6 text-sm text-slate-400">
                Fill in the form and calculate to see an itemized, explainable quote.
              </p>
            ) : (
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Detected route</span>
                  <span className="flex items-center gap-1 font-medium text-slate-800">
                    {quote.pickup_zone} <ArrowRight size={12} /> {quote.drop_zone}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Zone type</span>
                  <Pill tone="brand">{humanize(quote.zone_type)}</Pill>
                </div>
                <div className="my-2 border-t border-dashed border-slate-200" />
                <Row label="Actual weight" value={formatWeight(quote.actual_weight)} />
                <Row label="Volumetric weight" value={formatWeight(quote.volumetric_weight)} />
                <Row
                  label="Chargeable weight"
                  value={formatWeight(quote.chargeable_weight)}
                  strong
                />
                <div className="my-2 border-t border-dashed border-slate-200" />
                <Row
                  label={`Base charge (${quote.order_type})`}
                  value={formatCurrency(quote.base_charge)}
                />
                <Row
                  label="COD surcharge"
                  value={quote.payment_type === "COD" ? formatCurrency(quote.cod_surcharge) : "—"}
                />
                <div className="mt-3 flex items-center justify-between rounded-lg bg-brand-50 px-3 py-2">
                  <span className="font-semibold text-brand-700">Total</span>
                  <span className="text-lg font-bold text-brand-700">
                    {formatCurrency(quote.total_charge, quote.currency)}
                  </span>
                </div>
                <Button
                  onClick={() => createMutation.mutate(getValues())}
                  loading={createMutation.isPending}
                  className="mt-3 w-full"
                >
                  Place order
                </Button>
                <p className="text-center text-xs text-slate-400">
                  You'll confirm the order on the next screen.
                </p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value, strong }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{label}</span>
      <span className={strong ? "font-semibold text-slate-900" : "text-slate-700"}>{value}</span>
    </div>
  );
}
