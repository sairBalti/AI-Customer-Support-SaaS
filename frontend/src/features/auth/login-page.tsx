import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

type LoginLocationState = {
  from?: string;
  email?: string;
  registered?: boolean;
  companyName?: string;
} | null;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state as LoginLocationState) ?? null;
  const [submitting, setSubmitting] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: state?.email ?? "", password: "" },
  });

  useEffect(() => {
    if (state?.email) {
      form.setValue("email", state.email);
    }
  }, [form, state?.email]);

  const onSubmit = form.handleSubmit(async (values) => {
    setSubmitting(true);
    try {
      await login(values.email, values.password);
      toast.success("Signed in");
      const from = state?.from || "/app";
      navigate(from, { replace: true });
    } catch (error) {
      toast.error(getErrorMessage(error, "Login failed"));
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,#99f6e4_0%,transparent_40%),radial-gradient(circle_at_bottom_right,#cbd5e1_0%,transparent_35%)]" />
      <Card className="relative z-10 w-full max-w-md">
        <CardHeader>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
            Support Agent
          </div>
          <CardTitle className="text-2xl">Sign in</CardTitle>
          <CardDescription>Access your AI customer support workspace.</CardDescription>
        </CardHeader>
        <CardContent>
          {state?.registered ? (
            <div className="mb-4 rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-900">
              {state.companyName ? (
                <>
                  <span className="font-medium">{state.companyName}</span> is ready. Sign in with the
                  admin email and password you just created.
                </>
              ) : (
                <>Your company is ready. Sign in with the admin email and password you just created.</>
              )}
            </div>
          ) : null}
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
              {form.formState.errors.email ? (
                <p className="text-xs text-destructive">{form.formState.errors.email.message}</p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <PasswordInput
                id="password"
                autoComplete="current-password"
                {...form.register("password")}
              />
              {form.formState.errors.password ? (
                <p className="text-xs text-destructive">{form.formState.errors.password.message}</p>
              ) : null}
            </div>
            <Button className="w-full" type="submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            New tenant?{" "}
            <Link className="font-medium text-teal-700 hover:underline" to="/register">
              Register a company
            </Link>
          </p>
          <p className="mt-2 text-center text-sm text-muted-foreground">
            <Link className="hover:underline" to="/">
              ← Back to home
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
