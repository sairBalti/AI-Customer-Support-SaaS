import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { searchKnowledge } from "@/api/knowledge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState, PageHeader } from "@/components/ui/page";
import { getErrorMessage } from "@/lib/api-error";
import type { KnowledgeHit } from "@/types/api";

const schema = z.object({
  query: z.string().min(1, "Enter a search query"),
  top_k: z.number().int().min(1).max(50),
});

type SearchValues = z.infer<typeof schema>;

export function KnowledgePage() {
  const [results, setResults] = useState<KnowledgeHit[]>([]);

  const form = useForm<SearchValues>({
    resolver: zodResolver(schema),
    defaultValues: { query: "", top_k: 5 },
  });

  const searchMutation = useMutation({
    mutationFn: (values: SearchValues) =>
      searchKnowledge({ query: values.query, top_k: values.top_k }),
    onSuccess: (data) => {
      setResults(data.items);
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  return (
    <div>
      <PageHeader
        title="Knowledge search"
        description="Semantic search over processed document chunks."
      />

      <p className="-mt-4 mb-6 text-sm text-muted-foreground">
        To process or reindex documents, go to{" "}
        <Link className="font-medium text-teal-800 hover:underline" to="/app/documents">
          Documents
        </Link>
        .
      </p>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Search</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            className="flex flex-col gap-4 sm:flex-row sm:items-end"
            onSubmit={form.handleSubmit((values) => searchMutation.mutate(values))}
          >
            <div className="flex-1 space-y-1">
              <Label htmlFor="query">Query</Label>
              <Input id="query" placeholder="How do I reset my password?" {...form.register("query")} />
            </div>
            <div className="w-full space-y-1 sm:w-28">
              <Label htmlFor="top_k">Top K</Label>
              <Input
                id="top_k"
                type="number"
                min={1}
                max={50}
                {...form.register("top_k", { valueAsNumber: true })}
              />
            </div>
            <Button type="submit" disabled={searchMutation.isPending}>
              {searchMutation.isPending ? "Searching…" : "Search"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {searchMutation.isSuccess && results.length === 0 ? (
        <EmptyState title="No matches" description="Try a different query or process more documents." />
      ) : null}

      {results.length > 0 ? (
        <div className="space-y-4">
          {results.map((hit) => (
            <Card key={hit.chunk_uuid}>
              <CardHeader className="pb-2">
                <div className="flex flex-wrap items-center gap-2">
                  <CardTitle className="text-sm font-medium">
                    {hit.source_filename ?? `Document #${hit.document_id}`}
                  </CardTitle>
                  {hit.page_number !== null ? (
                    <Badge variant="outline">Page {hit.page_number}</Badge>
                  ) : null}
                  <Badge variant="secondary">Score {(hit.score * 100).toFixed(1)}%</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                  {hit.content}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}
    </div>
  );
}
