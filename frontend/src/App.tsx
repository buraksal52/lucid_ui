import { FormEvent, useEffect, useMemo, useState } from "react";
import { LucidApiError, submitSingleAnalysis } from "./api";
import { CompareView } from "./CompareView";
import { DataPair, ErrorBanner, ReportDashboard } from "./ReportDashboard";
import type {
  AnalysisContext,
  AnalysisReport,
  ApiErrorPayload
} from "./types";
import { ACCEPTED_TYPES, validateFile } from "./upload";
import { cx, formatBytes } from "./utils";

type UiState =
  | "idle"
  | "file_selected"
  | "submitting"
  | "analyzing_metrics"
  | "running_uiclip"
  | "interpreting"
  | "completed"
  | "partial_success"
  | "failed";

type DashboardMode = "single" | "compare";

function App() {
  const [now, setNow] = useState(() => new Date());
  const [mode, setMode] = useState<DashboardMode>("single");
  const [uiState, setUiState] = useState<UiState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [context, setContext] = useState<AnalysisContext>("general");
  const [description, setDescription] = useState("");
  const [runUiclip, setRunUiclip] = useState(true);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [error, setError] = useState<ApiErrorPayload | null>(null);

  const isWorking =
    uiState === "submitting" ||
    uiState === "analyzing_metrics" ||
    uiState === "running_uiclip" ||
    uiState === "interpreting";

  const formattedNow = useMemo(
    () =>
      new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "medium"
      }).format(now),
    [now]
  );

  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);

    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  useEffect(() => {
    if (uiState !== "submitting") {
      return;
    }

    const timers = [
      window.setTimeout(() => setUiState("analyzing_metrics"), 500),
      window.setTimeout(() => setUiState("running_uiclip"), 1300),
      window.setTimeout(() => setUiState("interpreting"), 2200)
    ];

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [uiState]);

  function selectFile(nextFile: File | null) {
    if (!nextFile) {
      return;
    }

    const validationError = validateFile(nextFile);
    if (validationError) {
      setError(validationError);
      setUiState("failed");
      return;
    }

    setFile(nextFile);
    setError(null);
    setReport(null);
    setUiState("file_selected");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      setError({
        code: "VALIDATION_ERROR",
        message: "Select a screenshot before running analysis."
      });
      setUiState("failed");
      return;
    }

    setError(null);
    setReport(null);
    setUiState("submitting");

    try {
      const nextReport = await submitSingleAnalysis({
        file,
        context,
        description,
        runUiclip
      });

      setReport(nextReport);
      setUiState(
        nextReport.status === "partial_success" ? "partial_success" : "completed"
      );
    } catch (caughtError) {
      if (caughtError instanceof LucidApiError) {
        setError({
          code: caughtError.code,
          message: caughtError.message,
          details: caughtError.details
        });
      } else {
        setError({
          code: "REQUEST_FAILED",
          message:
            "The analysis request did not complete. Check the backend service and try again."
        });
      }
      setUiState("failed");
    }
  }

  return (
    <main className="min-h-screen bg-paper px-4 py-5 text-ink sm:px-6 lg:px-10">
      <Header currentTime={formattedNow} mode={mode} onModeChange={setMode} />

      <div className="mx-auto mt-8 max-w-[1500px]">
        <section className="spine-shell">
          {mode === "single" ? (
            <>
              <IntakeBlock
                context={context}
                description={description}
                file={file}
                isWorking={isWorking}
                previewUrl={previewUrl}
                runUiclip={runUiclip}
                uiState={uiState}
                onContextChange={setContext}
                onDescriptionChange={setDescription}
                onFileSelect={selectFile}
                onRunUiclipChange={setRunUiclip}
                onSubmit={handleSubmit}
              />

              {error ? <ErrorBanner error={error} /> : null}

              {report ? <ReportDashboard report={report} /> : null}
            </>
          ) : (
            <CompareView />
          )}
        </section>
      </div>

      <Footer />
    </main>
  );
}

interface HeaderProps {
  currentTime: string;
  mode: DashboardMode;
  onModeChange: (mode: DashboardMode) => void;
}

function Header({ currentTime, mode, onModeChange }: HeaderProps) {
  return (
    <header className="mx-auto flex max-w-[1500px] flex-wrap items-start justify-between gap-4">
      <div className="font-display text-4xl font-bold uppercase tracking-[0.12em] sm:text-5xl">
        LucidUI
      </div>

      <div className="flex flex-wrap items-start gap-3">
        <div className="flex border-2 border-ink" role="tablist" aria-label="Dashboard mode">
          {(["single", "compare"] as const).map((value) => (
            <button
              aria-selected={mode === value}
              className={cx(
                "px-4 py-2 font-display text-xs font-bold uppercase tracking-[0.14em]",
                mode === value ? "bg-ink text-paper" : "bg-paper text-ink"
              )}
              key={value}
              role="tab"
              type="button"
              onClick={() => onModeChange(value)}
            >
              {value === "single" ? "Single" : "Compare"}
            </button>
          ))}
        </div>

        <div className="border-2 border-ink bg-paper px-3 py-2 text-right font-mono text-xs uppercase shadow-stamp sm:text-sm">
          <div>{currentTime}</div>
        </div>
      </div>
    </header>
  );
}

interface IntakeBlockProps {
  context: AnalysisContext;
  description: string;
  file: File | null;
  isWorking: boolean;
  previewUrl: string | null;
  runUiclip: boolean;
  uiState: UiState;
  onContextChange: (context: AnalysisContext) => void;
  onDescriptionChange: (description: string) => void;
  onFileSelect: (file: File | null) => void;
  onRunUiclipChange: (runUiclip: boolean) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function IntakeBlock({
  context,
  description,
  file,
  isWorking,
  previewUrl,
  runUiclip,
  uiState,
  onContextChange,
  onDescriptionChange,
  onFileSelect,
  onRunUiclipChange,
  onSubmit
}: IntakeBlockProps) {
  return (
    <form
      className="intake-block grid gap-6 border-4 border-ink bg-paper p-4 sm:p-6 lg:grid-cols-[1.1fr_0.9fr]"
      onSubmit={onSubmit}
    >
      <div className="space-y-5">
        <div>
          <p className="font-display text-sm font-bold uppercase tracking-[0.18em]">
            Lab intake
          </p>
          <h1 className="mt-2 max-w-3xl font-display text-3xl font-bold uppercase tracking-[0.08em] sm:text-5xl">
            Three independent UI signals
          </h1>
        </div>

        <Dropzone file={file} onFileSelect={onFileSelect} />

        <div className="grid gap-4 md:grid-cols-[0.7fr_1.3fr]">
          <fieldset className="border-2 border-ink p-3">
            <legend className="px-2 font-display text-xs font-bold uppercase tracking-[0.16em]">
              Context
            </legend>
            <div className="grid grid-cols-2 gap-2">
              {(["general", "expert"] as const).map((value) => (
                <button
                  className={cx(
                    "border-2 border-ink px-3 py-2 font-mono text-xs uppercase",
                    context === value ? "bg-ink text-paper" : "bg-paper text-ink"
                  )}
                  key={value}
                  type="button"
                  onClick={() => onContextChange(value)}
                >
                  {value}
                </button>
              ))}
            </div>
          </fieldset>

          <label className="block border-2 border-ink p-3">
            <span className="font-display text-xs font-bold uppercase tracking-[0.16em]">
              Description
            </span>
            <textarea
              className="mt-3 min-h-28 w-full resize-y border-2 border-ink bg-paper p-3 font-body text-sm leading-6 outline-none"
              placeholder="Optional description used by UIClip."
              value={description}
              onChange={(event) => onDescriptionChange(event.target.value)}
            />
          </label>
        </div>

        <div className="flex flex-col gap-4 border-2 border-ink p-4 sm:flex-row sm:items-center sm:justify-between">
          <label className="flex items-center gap-3 font-body text-sm font-medium">
            <input
              checked={runUiclip}
              className="h-5 w-5 border-2 border-ink accent-signal"
              type="checkbox"
              onChange={(event) => onRunUiclipChange(event.target.checked)}
            />
            <span>Run UIClip</span>
          </label>

          <button
            className="border-2 border-ink bg-ink px-6 py-3 font-display text-sm font-bold uppercase tracking-[0.14em] text-paper shadow-stamp disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isWorking}
            type="submit"
          >
            Run analysis
          </button>
        </div>
      </div>

      <ImagePreview file={file} previewUrl={previewUrl} uiState={uiState} />
    </form>
  );
}

interface DropzoneProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
}

function Dropzone({ file, onFileSelect }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  return (
    <div
      className={cx(
        "relative border-4 border-ink bg-paper p-5",
        isDragging && "outline outline-4 outline-offset-4 outline-marker"
      )}
      onDragLeave={() => setIsDragging(false)}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragging(true);
      }}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragging(false);
        onFileSelect(event.dataTransfer.files.item(0));
      }}
    >
      <div className="absolute right-4 top-4 border-4 border-blueprint px-4 py-1 font-display text-sm font-bold uppercase tracking-[0.2em] text-blueprint">
        Sample
      </div>
      <input
        accept={ACCEPTED_TYPES.join(",")}
        className="sr-only"
        id="sample-upload"
        type="file"
        onChange={(event) => onFileSelect(event.target.files?.item(0) ?? null)}
      />
      <label
        className="flex min-h-44 cursor-pointer flex-col justify-end gap-3 pr-28"
        htmlFor="sample-upload"
      >
        <span className="font-display text-xl font-bold uppercase tracking-[0.12em]">
          Drag or select a screenshot
        </span>
        <span className="font-mono text-xs uppercase">
          PNG / JPG / WebP, max 20 MB
        </span>
        {file ? (
          <span className="break-all font-mono text-sm">{file.name}</span>
        ) : null}
      </label>
    </div>
  );
}

interface ImagePreviewProps {
  file: File | null;
  previewUrl: string | null;
  uiState: UiState;
}

function ImagePreview({ file, previewUrl, uiState }: ImagePreviewProps) {
  return (
    <aside className="border-2 border-ink p-4">
      <div className="flex items-start justify-between gap-4">
        <p className="font-display text-xs font-bold uppercase tracking-[0.16em]">
          Preview
        </p>
        <p className="font-mono text-xs uppercase">{uiState}</p>
      </div>

      <div className="mt-4 flex min-h-80 items-center justify-center border-2 border-ink bg-[#F7F7F2]">
        {previewUrl ? (
          <img
            alt={file?.name ?? "Selected screenshot preview"}
            className="max-h-[520px] w-full object-contain"
            src={previewUrl}
          />
        ) : (
          <p className="px-6 text-center font-mono text-sm uppercase">
            No sample selected
          </p>
        )}
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-2 font-mono text-xs uppercase">
        <DataPair label="File" value={file?.name ?? "not available"} />
        <DataPair label="Size" value={formatBytes(file?.size)} />
        <DataPair label="Type" value={file?.type || "not available"} />
        <DataPair label="State" value={uiState} />
      </dl>
    </aside>
  );
}

function Footer() {
  return (
    <footer className="mx-auto mt-10 max-w-[1500px] border-t-4 border-ink py-5 font-body text-sm">
      LucidUI reports measurable signals side by side and does not issue a
      verdict.
    </footer>
  );
}

export default App;
