import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "../components/AppShell";
import { documentsApi, DocumentItem } from "../api/endpoints";

export default function Documents() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => documentsApi.list().then((r) => r.data),
    // Poll while anything is still indexing so status updates without a manual refresh.
    refetchInterval: (query) => {
      const docs = query.state.data?.documents ?? [];
      const stillProcessing = docs.some((d) => d.status === "pending" || d.status === "processing");
      return stillProcessing ? 2000 : false;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsApi.upload(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
    onError: (e: any) => setErr(e?.response?.data?.detail ?? "Upload failed."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => documentsApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setErr(null);
    for (const file of Array.from(files)) {
      // eslint-disable-next-line no-await-in-loop
      await uploadMutation.mutateAsync(file).catch(() => {});
    }
  }

  function del(id: string) {
    if (!confirm("Delete this document?")) return;
    deleteMutation.mutate(id);
  }

  const docs = data?.documents ?? [];

  return (
    <AppShell>
      <div className="mx-auto max-w-6xl px-6 py-10 md:px-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-3xl font-semibold tracking-tight">Documents</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Upload company documents to make them searchable in Chat.
            </p>
          </div>
          <label className="btn-primary cursor-pointer">
            {uploadMutation.isPending ? "Uploading…" : "Upload document"}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              hidden
              onChange={(e) => {
                handleFiles(e.target.files);
                e.target.value = "";
              }}
              accept=".pdf,.docx,.txt,.md"
              disabled={uploadMutation.isPending}
            />
          </label>
        </div>

        {err && (
          <div className="mt-6 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            {err}
          </div>
        )}

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            if (!uploadMutation.isPending) handleFiles(e.dataTransfer.files);
          }}
          className={`mt-6 rounded-2xl border-2 border-dashed p-10 text-center transition ${
            dragOver ? "border-primary bg-primary/5" : "border-border/60 bg-card/20"
          }`}
        >
          <div className="font-display text-lg">Drop files to upload</div>
          <div className="mt-1 text-sm text-muted-foreground">PDF · DOCX · TXT · MD</div>
        </div>

        <div className="mt-8 overflow-hidden rounded-2xl border border-border/60 bg-card/40">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase tracking-wider text-muted-foreground">
              <tr className="border-b border-border/60">
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Size</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Uploaded</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-muted-foreground">
                    Loading…
                  </td>
                </tr>
              )}
              {!isLoading && docs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-muted-foreground">
                    No documents yet. Upload one to get started.
                  </td>
                </tr>
              )}
              {docs.map((d) => (
                <DocRow key={d.id} doc={d} onDelete={() => del(d.id)} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}

function DocRow({ doc, onDelete }: { doc: DocumentItem; onDelete: () => void }) {
  const badge =
    doc.status === "failed"
      ? "bg-red-500/15 text-red-300 border-red-500/30"
      : doc.status === "indexed"
        ? "bg-green-500/10 text-green-300 border-green-500/30"
        : "bg-yellow-500/10 text-yellow-300 border-yellow-500/30";

  return (
    <tr className="border-t border-border/40">
      <td className="px-4 py-4 font-medium">{doc.filename}</td>
      <td className="px-4 py-4 text-muted-foreground">{formatBytes(doc.size_bytes)}</td>
      <td className="px-4 py-4">
        <span className={`inline-block rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wider ${badge}`}>
          {doc.status}
        </span>
        {doc.status === "failed" && doc.error_message && (
          <div className="mt-1 max-w-md text-xs text-red-300/80">{doc.error_message}</div>
        )}
      </td>
      <td className="px-4 py-4 text-muted-foreground">{formatDate(doc.created_at)}</td>
      <td className="px-4 py-4 text-right">
        <button onClick={onDelete} className="text-xs text-muted-foreground hover:text-red-300">
          Delete
        </button>
      </td>
    </tr>
  );
}

function formatBytes(bytes: number) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(s?: string | null) {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString();
  } catch {
    return s;
  }
}
