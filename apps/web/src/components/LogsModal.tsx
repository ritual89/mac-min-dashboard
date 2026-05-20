interface LogsModalProps {
  title: string;
  body: string;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

export function LogsModal({
  title,
  body,
  loading,
  error,
  onClose,
}: LogsModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Logs for ${title}`}
    >
      <div className="flex max-h-[80vh] w-full max-w-3xl flex-col rounded border border-border bg-panel shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold">Logs — {title}</h2>
          <button
            type="button"
            className="rounded px-2 py-1 text-sm text-gray-300 hover:bg-row"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <pre className="overflow-auto p-4 font-mono text-xs leading-relaxed text-gray-200">
          {loading && "Loading…"}
          {!loading && error && `Error: ${error}`}
          {!loading && !error && (body || "(empty)")}
        </pre>
      </div>
    </div>
  );
}
