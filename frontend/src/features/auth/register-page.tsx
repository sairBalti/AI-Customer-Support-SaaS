import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { registerCompany } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { TimezoneSelect } from "@/components/ui/timezone-select";
import { getErrorMessage } from "@/lib/api-error";

const schema = z
  .object({
    company_name: z.string().min(3).max(150),
    email: z.string().email(),
    company_slug: z.string().max(150).optional(),
    timezone: z.string().min(1),
    admin_first_name: z.string().min(2, "First name is required").max(100),
    admin_last_name: z.string().min(2, "Last name is required").max(100),
    admin_password: z
      .string()
      .min(12, "Password must be at least 12 characters")
      .regex(/[A-Z]/, "Include an uppercase letter")
      .regex(/[a-z]/, "Include a lowercase letter")
      .regex(/[0-9]/, "Include a number")
      .regex(/[^A-Za-z0-9]/, "Include a special character"),
    confirm_password: z.string().min(1, "Confirm your password"),
  })
  .refine((values) => values.admin_password === values.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export function RegisterCompanyPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [showMore, setShowMore] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_name: "",
      email: "",
      company_slug: "",
      timezone: "UTC",
      admin_first_name: "",
      admin_last_name: "",
      admin_password: "",
      confirm_password: "",
    },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setSubmitting(true);
    try {
      await registerCompany({
        company_name: values.company_name,
        email: values.email,
        company_slug: values.company_slug || undefined,
        timezone: values.timezone || "UTC",
        admin_password: values.admin_password,
        admin_first_name: values.admin_first_name,
        admin_last_name: values.admin_last_name,
      });
      toast.success("Company created. Sign in with your admin account.");
      navigate("/login", {
        replace: true,
        state: {
          email: values.email.trim(),
          registered: true,
          companyName: values.company_name.trim(),
        },
      });
    } catch (error) {
      toast.error(getErrorMessage(error, "Registration failed"));
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,#99f6e4_0%,transparent_40%),linear-gradient(180deg,#f8fafc,#e2e8f0)]" />
      <Card className="relative z-10 w-full max-w-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-xl">Register company</CardTitle>
          <CardDescription>Create your workspace and admin login.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-3" onSubmit={onSubmit}>
            <div className="space-y-1">
              <Label htmlFor="company_name">Company name</Label>
              <Input id="company_name" {...form.register("company_name")} />
              {form.formState.errors.company_name ? (
                <p className="text-xs text-destructive">{form.formState.errors.company_name.message}</p>
              ) : null}
            </div>

            <div className="space-y-1">
              <Label htmlFor="email">Admin email</Label>
              <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
              {form.formState.errors.email ? (
                <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
              ) : null}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label htmlFor="admin_first_name">First name</Label>
                <Input
                  id="admin_first_name"
                  autoComplete="given-name"
                  {...form.register("admin_first_name")}
                />
                {form.formState.errors.admin_first_name ? (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.admin_first_name.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="admin_last_name">Last name</Label>
                <Input
                  id="admin_last_name"
                  autoComplete="family-name"
                  {...form.register("admin_last_name")}
                />
                {form.formState.errors.admin_last_name ? (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.admin_last_name.message}
                  </p>
                ) : null}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label htmlFor="admin_password">Password</Label>
                <PasswordInput
                  id="admin_password"
                  autoComplete="new-password"
                  {...form.register("admin_password")}
                />
                {form.formState.errors.admin_password ? (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.admin_password.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="confirm_password">Confirm</Label>
                <PasswordInput
                  id="confirm_password"
                  autoComplete="new-password"
                  {...form.register("confirm_password")}
                />
                {form.formState.errors.confirm_password ? (
                  <p className="text-xs text-destructive">
                    {form.formState.errors.confirm_password.message}
                  </p>
                ) : null}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              12+ chars with upper, lower, number, and symbol.
            </p>

            <button
              type="button"
              className="text-xs font-medium text-teal-700 hover:underline"
              onClick={() => setShowMore((open) => !open)}
            >
              {showMore ? "Hide optional settings" : "Optional: slug & timezone"}
            </button>

            {showMore ? (
              <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-3">
                <div className="space-y-1">
                  <Label htmlFor="company_slug">Slug</Label>
                  <Input id="company_slug" placeholder="auto-generated" {...form.register("company_slug")} />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="timezone">Timezone</Label>
                  <TimezoneSelect
                    id="timezone"
                    value={form.watch("timezone")}
                    onChange={(value) => form.setValue("timezone", value, { shouldValidate: true })}
                  />
                </div>
              </div>
            ) : null}

            <Button className="w-full" type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create company & continue"}
            </Button>
          </form>
          <p className="mt-3 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link className="font-medium text-teal-700 hover:underline" to="/login">
              Sign in
            </Link>
            {" · "}
            <Link className="hover:underline" to="/">
              Home
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
