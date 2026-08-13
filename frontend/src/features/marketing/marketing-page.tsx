import { Link } from "react-router-dom";
import {
  ArrowRight,
  Building2,
  Check,
  FileText,
  MessageSquare,
  Search,
  Shield,
  Ticket,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const FEATURES = [
  {
    icon: MessageSquare,
    title: "AI support chat",
    description:
      "Give customers instant answers grounded in your own knowledge base, with a clear path to human handoff.",
  },
  {
    icon: Search,
    title: "Knowledge search",
    description:
      "Upload policies and product docs once. The agent retrieves the right context before it replies.",
  },
  {
    icon: Ticket,
    title: "Ticket workspace",
    description:
      "Track open issues, assign agents, set priority, and close the loop without leaving the platform.",
  },
  {
    icon: FileText,
    title: "Document library",
    description:
      "Centralize PDFs and guides per tenant, with processing status and storage limits by plan.",
  },
  {
    icon: Building2,
    title: "Multi-tenant companies",
    description:
      "Each company gets its own users, documents, and quotas—ideal for agencies and SaaS operators.",
  },
  {
    icon: Shield,
    title: "Roles & audit trail",
    description:
      "Super Admin, Company Admin, agents, and customers see only what they should. Sensitive actions are logged.",
  },
] as const;

const STEPS = [
  {
    step: "01",
    title: "Register your company",
    description: "Create a tenant with timezone, plan, and ops email in under a minute.",
  },
  {
    step: "02",
    title: "Add docs & teammates",
    description: "Upload knowledge, invite admins and agents, and set roles that match how you work.",
  },
  {
    step: "03",
    title: "Go live with AI chat",
    description: "Customers ask questions, get grounded answers, and escalate to tickets when needed.",
  },
] as const;

const PLANS = [
  {
    name: "Free",
    price: "$0",
    blurb: "Try the platform with light usage.",
    highlights: ["Up to 5 users", "50 documents", "500 MB storage", "AI chat & tickets"],
    featured: false,
  },
  {
    name: "Starter",
    price: "$49",
    blurb: "For early support teams.",
    highlights: ["10 users", "200 documents", "2 GB storage", "Priority ticket workflows"],
    featured: false,
  },
  {
    name: "Pro",
    price: "$149",
    blurb: "For growing support orgs.",
    highlights: ["25 users", "500 documents", "10 GB storage", "Higher AI token quota"],
    featured: true,
  },
  {
    name: "Business",
    price: "$399",
    blurb: "For multi-team operations.",
    highlights: ["100 users", "2,000 documents", "50 GB storage", "Audit-ready controls"],
    featured: false,
  },
] as const;

export function MarketingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border/80 bg-card/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <a href="#top" className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-xs font-bold text-primary-foreground">
              ACS
            </span>
            <span className="text-sm font-semibold tracking-tight sm:text-base">
              AI Customer Support
            </span>
          </a>
          <nav className="hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a className="hover:text-foreground" href="#features">
              Features
            </a>
            <a className="hover:text-foreground" href="#how-it-works">
              How it works
            </a>
            <a className="hover:text-foreground" href="#pricing">
              Pricing
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
              <Link to="/login">Sign in</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/register">
                Start free <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,#99f6e4_0%,transparent_42%),radial-gradient(circle_at_bottom_right,#cbd5e1_0%,transparent_40%)]" />
          <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
                Support Agent Platform
              </p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-5xl lg:text-[3.25rem] lg:leading-[1.1]">
                Customer support that answers with your knowledge—not guesswork.
              </h1>
              <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
                Multi-tenant AI chat, searchable documents, tickets, and role-based admin in one
                workspace. Launch a company, upload your docs, and let the agent help customers
                around the clock.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <Link to="/register">
                    Register your company <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline">
                  <Link to="/login">Sign in to workspace</Link>
                </Button>
              </div>
              <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <Check className="h-4 w-4 text-teal-700" /> Tenant isolation
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Check className="h-4 w-4 text-teal-700" /> RBAC for every role
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <Check className="h-4 w-4 text-teal-700" /> Audit-ready activity
                </span>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-card p-5 shadow-lg shadow-slate-200/60">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">
                    Live workspace
                  </p>
                  <p className="text-sm text-muted-foreground">What your team sees after signup</p>
                </div>
                <span className="rounded-full bg-accent px-2.5 py-1 text-xs font-medium text-accent-foreground">
                  Demo preview
                </span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  { label: "Open tickets", value: "12", icon: Ticket },
                  { label: "Active chats", value: "8", icon: MessageSquare },
                  { label: "Documents", value: "146", icon: FileText },
                  { label: "Knowledge hits", value: "94%", icon: Zap },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="rounded-xl border border-border bg-muted/40 p-4"
                  >
                    <item.icon className="h-4 w-4 text-teal-700" />
                    <p className="mt-3 text-2xl font-semibold">{item.value}</p>
                    <p className="text-xs text-muted-foreground">{item.label}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-xl border border-dashed border-teal-200 bg-teal-50/60 p-4">
                <p className="text-sm font-medium text-teal-900">
                  “How do I reset my billing contact?”
                </p>
                <p className="mt-2 text-sm text-teal-800/80">
                  Agent cites your uploaded policy, answers in seconds, then offers a ticket if
                  the customer still needs help.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="border-t border-border bg-card">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
                Features
              </p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">
                Everything a modern support stack needs
              </h2>
              <p className="mt-3 text-muted-foreground">
                Built for AI Customer Support Agent: chat, knowledge, tickets, documents, companies,
                users, and audit—wired through clean RBAC.
              </p>
            </div>
            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature) => (
                <article
                  key={feature.title}
                  className="rounded-xl border border-border bg-background p-5 shadow-sm"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                    <feature.icon className="h-5 w-5" />
                  </div>
                  <h3 className="mt-4 text-base font-semibold">{feature.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{feature.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-t border-border">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
                How it works
              </p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">
                Live in three steps
              </h2>
            </div>
            <div className="mt-10 grid gap-4 lg:grid-cols-3">
              {STEPS.map((item) => (
                <article key={item.step} className="rounded-xl border border-border bg-card p-6">
                  <p className="text-sm font-semibold text-teal-700">{item.step}</p>
                  <h3 className="mt-2 text-lg font-semibold">{item.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="pricing" className="border-t border-border bg-card">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-700">
                Pricing
              </p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">
                Plans that scale with your tenants
              </h2>
              <p className="mt-3 text-muted-foreground">
                Quotas match the product subscription tiers. Start on Free, upgrade when your team
                and document library grow.
              </p>
            </div>
            <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {PLANS.map((plan) => (
                <article
                  key={plan.name}
                  className={cn(
                    "flex flex-col rounded-xl border bg-background p-6 shadow-sm",
                    plan.featured ? "border-primary ring-2 ring-primary/20" : "border-border",
                  )}
                >
                  {plan.featured ? (
                    <span className="mb-3 w-fit rounded-full bg-primary px-2.5 py-0.5 text-xs font-medium text-primary-foreground">
                      Most popular
                    </span>
                  ) : (
                    <span className="mb-3 h-5" />
                  )}
                  <h3 className="text-lg font-semibold">{plan.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{plan.blurb}</p>
                  <p className="mt-4 text-3xl font-semibold tracking-tight">
                    {plan.price}
                    <span className="text-sm font-normal text-muted-foreground">/mo</span>
                  </p>
                  <ul className="mt-5 space-y-2 text-sm text-muted-foreground">
                    {plan.highlights.map((line) => (
                      <li key={line} className="flex items-start gap-2">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
                        {line}
                      </li>
                    ))}
                  </ul>
                  <Button asChild className="mt-6 w-full" variant={plan.featured ? "default" : "outline"}>
                    <Link to="/register">Get started</Link>
                  </Button>
                </article>
              ))}
            </div>
            <p className="mt-6 text-center text-sm text-muted-foreground">
              Need Enterprise limits? Register a company and ask your Super Admin to set the
              Enterprise plan.
            </p>
          </div>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
            <div className="overflow-hidden rounded-2xl border border-border bg-[linear-gradient(135deg,#134e4a_0%,#1f5c52_45%,#0f172a_100%)] px-6 py-12 text-center text-teal-50 sm:px-10">
              <h2 className="text-3xl font-semibold tracking-tight">
                Ready to replace inbox chaos with grounded AI support?
              </h2>
              <p className="mx-auto mt-3 max-w-2xl text-sm text-teal-100/90 sm:text-base">
                Create a tenant, invite your team, and ship a support experience your customers can
                trust.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Button asChild size="lg" className="bg-white text-teal-900 hover:bg-teal-50">
                  <Link to="/register">Create company</Link>
                </Button>
                <Button
                  asChild
                  size="lg"
                  variant="outline"
                  className="border-teal-200/40 bg-transparent text-teal-50 hover:bg-white/10 hover:text-white"
                >
                  <Link to="/login">Sign in</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div>
            <p className="font-medium text-foreground">AI Customer Support</p>
            <p className="mt-1">Multi-tenant AI support for modern teams.</p>
          </div>
          <div className="flex flex-wrap gap-4">
            <Link className="hover:text-foreground" to="/login">
              Sign in
            </Link>
            <Link className="hover:text-foreground" to="/register">
              Register
            </Link>
            <a className="hover:text-foreground" href="#features">
              Features
            </a>
            <a className="hover:text-foreground" href="#pricing">
              Pricing
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
