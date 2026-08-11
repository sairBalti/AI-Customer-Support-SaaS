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
import { getErrorMessage } from "@/lib/api-error";

const schema = z.object({
  company_name: z.string().min(3).max(150),
  email: z.string().email(),
  company_slug: z.string().max(150).optional(),
  timezone: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

export function RegisterCompanyPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { company_name: "", email: "", company_slug: "", timezone: "UTC" },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    setSubmitting(true);
    try {
      await registerCompany({
        company_name: values.company_name,
        email: values.email,
        company_slug: values.company_slug || undefined,
        timezone: values.timezone || "UTC",
      });
      toast.success("Company registered. Sign in with your admin account when provisioned.");
      navigate("/login");
    } catch (error) {
      toast.error(getErrorMessage(error, "Registration failed"));
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,#99f6e4_0%,transparent_40%),linear-gradient(180deg,#f8fafc,#e2e8f0)]" />
      <Card className="relative z-10 w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Register company</CardTitle>
          <CardDescription>Public onboarding for a new tenant workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="company_name">Company name</Label>
              <Input id="company_name" {...form.register("company_name")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Ops email</Label>
              <Input id="email" type="email" {...form.register("email")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="company_slug">Slug (optional)</Label>
              <Input id="company_slug" {...form.register("company_slug")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <Input id="timezone" {...form.register("timezone")} />
            </div>
            <Button className="w-full" type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create company"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link className="font-medium text-teal-700 hover:underline" to="/login">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
