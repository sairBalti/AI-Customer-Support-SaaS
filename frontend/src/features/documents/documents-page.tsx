import { useCallback, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import {
  deleteDocument,
  getStorageUsage,
  listDocuments,
  processDocument,
  reindexDocument,
  restoreDocument,
  uploadDocument,
} from "@/api/documents";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, ErrorBlock, LoadingBlock, PageHeader } from "@/components/ui/page";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useAuth } from "@/hooks/use-auth";
import { getErrorMessage } from "@/lib/api-error";
import { cn, formatDate } from "@/lib/utils";
import type { Document } from "@/types/api";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function statusVariant(status: string): "success" | "warning" | "danger" | "secondary" {
  if (status === "COMPLETED") return "success";
  if (status === "FAILED") return "danger";
  if (status === "PROCESSING" || status === "QUEUED") return "warning";
  return "secondary";
}

export function DocumentsPage() {
  const { can } = useAuth();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  const documentsQuery = useQuery({
    queryKey: ["documents", page, includeDeleted],
    queryFn: () =>
      listDocuments({ page, page_size: 20, include_deleted: includeDeleted }),
    enabled: can("documents.read"),
  });

  const storageQuery = useQuery({
    queryKey: ["documents", "storage"],
    queryFn: () => getStorageUsage(),
    enabled: can("documents.read"),
  });

  const invalidate = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["documents"] });
    void qc.invalidateQueries({ queryKey: ["dashboard", "storage"] });
  }, [qc]);

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      form.append("document_name", file.name.replace(/\.[^.]+$/, "") || file.name);
      setUploadProgress(0);
      return uploadDocument(form, (pct) => setUploadProgress(pct));
    },
    onSuccess: () => {
      toast.success("Document uploaded");
      setUploadProgress(null);
      invalidate();
    },
    onError: (e) => {
      toast.error(getErrorMessage(e));
      setUploadProgress(null);
    },
  });

  const actionMutation = useMutation({
    mutationFn: async ({
      id,
      action,
    }: {
      id: number;
      action: "delete" | "restore" | "process" | "reindex";
    }) => {
      switch (action) {
        case "delete":
          return deleteDocument(id);
        case "restore":
          return restoreDocument(id);
        case "process":
          return processDocument(id);
        case "reindex":
          return reindexDocument(id);
      }
    },
    onSuccess: (_, { action }) => {
      const labels: Record<typeof action, string> = {
        delete: "deleted",
        restore: "restored",
        process: "queued for processing",
        reindex: "reindex queued",
      };
      toast.success(`Document ${labels[action]}`);
      invalidate();
    },
    onError: (e) => toast.error(getErrorMessage(e)),
  });

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files?.length || !can("documents.upload")) return;
      uploadMutation.mutate(files[0]!);
    },
    [can, uploadMutation],
  );

  const filteredItems = useMemo(() => {
    const items = documentsQuery.data?.items ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (doc) =>
        doc.document_name.toLowerCase().includes(q) ||
        doc.original_filename.toLowerCase().includes(q),
    );
  }, [documentsQuery.data?.items, search]);

  const meta = documentsQuery.data?.meta;

  return (
    <div>
      <PageHeader
        title="Documents"
        description="Upload, process, and manage knowledge-base documents."
      />

      {can("documents.read") && storageQuery.data ? (
        <Card className="mb-6">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Storage usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-teal-800">
              {formatBytes(storageQuery.data.used_bytes)}
              <span className="text-base font-normal text-muted-foreground">
                {" "}
                / {formatBytes(storageQuery.data.max_storage_bytes)}
              </span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {storageQuery.data.document_count} document
              {storageQuery.data.document_count === 1 ? "" : "s"}
              {" · "}
              {storageQuery.data.remaining_documents} slots remaining
            </p>
          </CardContent>
        </Card>
      ) : null}

      {can("documents.upload") ? (
        <div
          className={cn(
            "mb-6 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
            dragOver ? "border-teal-500 bg-teal-50" : "border-border bg-card",
            uploadMutation.isPending && "pointer-events-none opacity-70",
          )}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
          }}
        >
          <Upload className="mx-auto h-8 w-8 text-teal-700" />
          <p className="mt-2 text-sm font-medium">Drag and drop a file here</p>
          <p className="mt-1 text-xs text-muted-foreground">or choose a file to upload</p>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <Button
            className="mt-4"
            variant="outline"
            disabled={uploadMutation.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            Choose file
          </Button>
          {uploadProgress !== null ? (
            <p className="mt-3 text-sm font-medium text-teal-800">
              Uploading… {uploadProgress}%
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Input
          placeholder="Search current page…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeDeleted}
            onChange={(e) => {
              setIncludeDeleted(e.target.checked);
              setPage(1);
            }}
          />
          Include deleted
        </label>
      </div>

      {documentsQuery.isLoading ? <LoadingBlock /> : null}
      {documentsQuery.error ? (
        <ErrorBlock message={getErrorMessage(documentsQuery.error)} />
      ) : null}

      {documentsQuery.data && filteredItems.length === 0 ? (
        <EmptyState
          title={search.trim() ? "No matching documents" : "No documents"}
          description={
            search.trim()
              ? "Try a different search on this page."
              : "Upload a document to get started."
          }
        />
      ) : null}

      {documentsQuery.data && filteredItems.length > 0 ? (
        <>
          <div className="rounded-lg border border-border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredItems.map((doc) => (
                  <DocumentRow
                    key={doc.document_id}
                    doc={doc}
                    can={can}
                    pending={actionMutation.isPending}
                    onAction={(action) => {
                      if (action === "delete") {
                        if (!window.confirm("Delete this document?")) return;
                      }
                      actionMutation.mutate({ id: doc.document_id, action });
                    }}
                  />
                ))}
              </TableBody>
            </Table>
          </div>

          {meta && meta.total_pages > 1 ? (
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-muted-foreground">
                Page {meta.page} of {meta.total_pages} · {meta.total_items} total
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= meta.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function DocumentRow({
  doc,
  can,
  pending,
  onAction,
}: {
  doc: Document;
  can: (...permissions: string[]) => boolean;
  pending: boolean;
  onAction: (action: "delete" | "restore" | "process" | "reindex") => void;
}) {
  const deleted = Boolean(doc.deleted_at);

  return (
    <TableRow className={deleted ? "opacity-60" : undefined}>
      <TableCell>
        <div className="font-medium text-teal-800">{doc.document_name}</div>
        <div className="text-xs text-muted-foreground">{doc.original_filename}</div>
        {deleted ? (
          <div className="text-xs text-muted-foreground">Deleted {formatDate(doc.deleted_at)}</div>
        ) : null}
      </TableCell>
      <TableCell>
        <Badge variant={statusVariant(doc.processing_status)}>{doc.processing_status}</Badge>
        {doc.processing_status === "FAILED" && doc.failure_reason ? (
          <p className="mt-1 max-w-xs text-xs text-destructive">{doc.failure_reason}</p>
        ) : null}
      </TableCell>
      <TableCell>{formatBytes(doc.file_size_bytes)}</TableCell>
      <TableCell>{doc.total_chunks}</TableCell>
      <TableCell className="text-right">
        <div className="flex flex-wrap justify-end gap-1">
          {can("knowledge.process") && !deleted ? (
            <Button
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => onAction("process")}
            >
              Process
            </Button>
          ) : null}
          {can("documents.reindex") && !deleted ? (
            <Button
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => onAction("reindex")}
            >
              Reindex
            </Button>
          ) : null}
          {can("documents.delete") ? (
            deleted ? (
              <Button
                size="sm"
                variant="secondary"
                disabled={pending}
                onClick={() => onAction("restore")}
              >
                Restore
              </Button>
            ) : (
              <Button
                size="sm"
                variant="destructive"
                disabled={pending}
                onClick={() => onAction("delete")}
              >
                Delete
              </Button>
            )
          ) : null}
        </div>
      </TableCell>
    </TableRow>
  );
}
