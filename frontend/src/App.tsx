import { FormEvent, useEffect, useMemo, useState } from "react";
import { LucidApiError, fetchRawReport, submitSingleAnalysis } from "./api";
import type {
  AnalysisContext,
  AnalysisReport,
  ApiErrorPayload,
  MetricSection,
  StageStatus
} from "./types";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024;

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

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function formatBytes(bytes?: number) {
  if (typeof bytes !== "number") {
    return "not available";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function statusTone(status: StageStatus) {
  return status === "failed" || status === "unavailable" ? "text-void" : "";
}

function App() {
  const [now, setNow] = useState(() => new Date());
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

  function validateFile(nextFile: File): ApiErrorPayload | null {
    if (!ACCEPTED_TYPES.includes(nextFile.type)) {
      return {
        code: "UNSUPPORTED_MEDIA_TYPE",
        message:
          "Select a PNG, JPG, or WebP screenshot before running analysis.",
        details: { contentType: nextFile.type, allowed: ACCEPTED_TYPES }
      };
    }

    if (nextFile.size > MAX_FILE_SIZE_BYTES) {
      return {
        code: "FILE_TOO_LARGE",
        message: "Select a screenshot under the 20 MB upload limit.",
        details: {
          sizeBytes: nextFile.size,
          maxBytes: MAX_FILE_SIZE_BYTES
        }
      };
    }

    return null;
  }

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
      <Header currentTime={formattedNow} />

      <div className="mx-auto mt-8 max-w-[1500px]">
        <section className="spine-shell">
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
        </section>
      </div>

      <Footer />
    </main>
  );
}

interface HeaderProps {
  currentTime: string;
}

function Header({ currentTime }: HeaderProps) {
  return (
    <header className="mx-auto flex max-w-[1500px] items-start justify-between gap-4">
      <div className="font-display text-4xl font-bold uppercase tracking-[0.12em] sm:text-5xl">
        LucidUI
      </div>
      <div className="border-2 border-ink bg-paper px-3 py-2 text-right font-mono text-xs uppercase shadow-stamp sm:text-sm">
        <div>{currentTime}</div>
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

interface ErrorBannerProps {
  error: ApiErrorPayload;
}

function ErrorBanner({ error }: ErrorBannerProps) {
  return (
    <section className="mt-8 border-4 border-void bg-paper p-4 text-ink">
      <p className="font-display text-sm font-bold uppercase tracking-[0.16em] text-void">
        Request state
      </p>
      <div className="mt-3 grid gap-2 sm:grid-cols-[180px_1fr]">
        <span className="font-mono text-sm text-void">{error.code}</span>
        <p className="font-body text-sm leading-6">{error.message}</p>
      </div>
    </section>
  );
}

interface ReportDashboardProps {
  report: AnalysisReport;
}

function ReportDashboard({ report }: ReportDashboardProps) {
  return (
    <section className="report-shell mt-10">
      <AnalysisSummary report={report} />

      <div className="channel-grid mt-8 grid min-w-0 gap-6 lg:grid-cols-3">
        <DeterministicLane report={report} />
        <LlmLane report={report} />
        <UiclipLane report={report} />
      </div>

      <RawDataDrawer analysisId={report.analysisId} initialReport={report} />
    </section>
  );
}

function AnalysisSummary({ report }: ReportDashboardProps) {
  const { imageMetadata, presentation, timings } = report;

  return (
    <section className="border-4 border-ink bg-paper p-4 sm:p-6">
      <div className="grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
        <div>
          <p className="font-display text-sm font-bold uppercase tracking-[0.18em]">
            Result record
          </p>
          <h2 className="mt-2 font-display text-2xl font-bold uppercase tracking-[0.08em] sm:text-4xl">
            {presentation.title}
          </h2>
          <p className="mt-4 max-w-5xl font-body text-sm leading-6 sm:text-base">
            {presentation.summary}
          </p>
        </div>

        <dl className="grid gap-2 font-mono text-xs uppercase">
          <DataPair label="analysisId" value={report.analysisId} />
          <DataPair label="status" value={report.status} />
          <DataPair label="context" value={report.context} />
          <DataPair label="totalMs" value={timings.totalMs ?? "not available"} />
          <DataPair
            label="image"
            value={
              imageMetadata.width && imageMetadata.height
                ? `${imageMetadata.width} x ${imageMetadata.height}`
                : "not available"
            }
          />
          <DataPair label="format" value={imageMetadata.format ?? "not available"} />
        </dl>
      </div>

      <div className="mt-5 border-2 border-ink p-4">
        <p className="font-mono text-sm leading-6">{presentation.closingNote}</p>
      </div>
    </section>
  );
}

function DeterministicLane({ report }: ReportDashboardProps) {
  return (
    <article className="channel-lane lane-deterministic border-2 border-ink border-t-4 border-t-blueprint bg-paper p-4">
      <LaneHeader
        colorClass="text-blueprint"
        label="DETERMINISTIC"
        subline="Does not see LLM or UIClip output."
      />

      <div className="mt-5 min-w-0 border-2 border-ink p-3">
        <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
          Composite
        </p>
        <p className="mt-2 font-mono text-3xl">
          {report.presentation.composite.rawDisplay}
        </p>
        <p className="mt-3 font-body text-sm leading-6">
          {report.presentation.composite.explanation}
        </p>
      </div>

      <div className="mt-4 grid min-w-0 gap-3">
        {report.presentation.metricSections.map((metric) => (
          <MetricCard key={metric.id} metric={metric} />
        ))}
      </div>
    </article>
  );
}

interface MetricCardProps {
  metric: MetricSection;
}

function MetricCard({ metric }: MetricCardProps) {
  return (
    <section className="min-w-0 border-2 border-ink bg-paper p-3">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-sm font-bold uppercase tracking-[0.12em]">
            {metric.title}
          </h3>
          <p className="mt-1 font-mono text-[11px] uppercase">
            {metric.category}
          </p>
        </div>
        {metric.isProxy ? (
          <span className="shrink-0 border-2 border-ink px-2 py-1 font-mono text-[10px] uppercase">
            proxy
          </span>
        ) : null}
      </div>

      <p className="mt-3 break-words font-mono text-2xl leading-tight">
        {metric.rawDisplay}
      </p>
      <p className="mt-2 font-mono text-xs uppercase">
        normalized:{" "}
        {metric.normalizedScore === null ? "not calculated" : metric.normalizedScore}
      </p>
      <p className="mt-3 font-body text-sm leading-6">{metric.explanation}</p>
      {metric.source ? (
        <p className="mt-3 border-t-2 border-ink pt-2 font-mono text-[11px] leading-5">
          {metric.source}
        </p>
      ) : null}
    </section>
  );
}

function LlmLane({ report }: ReportDashboardProps) {
  const { llmInterpretation } = report;
  const statusClass = statusTone(llmInterpretation.status);

  return (
    <article className="channel-lane lane-llm border-2 border-ink border-t-4 border-t-marker bg-paper p-4">
      <LaneHeader
        colorClass="text-marker"
        label="INTERPRETED"
        subline="Does not see the image."
      />

      <div className="mt-5 border-l-4 border-marker pl-4">
        <p className={cx("font-mono text-sm uppercase", statusClass)}>
          status: {llmInterpretation.status}
        </p>
        <p className="mt-2 font-mono text-xs uppercase">
          provider: {llmInterpretation.provider ?? "not available"}
        </p>

        {llmInterpretation.status === "completed" ? (
          <p className="mt-5 font-body text-base leading-7">
            {llmInterpretation.summary}
          </p>
        ) : (
          <p className={cx("mt-5 font-body text-base leading-7", statusClass)}>
            {llmInterpretation.status}
          </p>
        )}
      </div>

      {llmInterpretation.observations.length > 0 ? (
        <div className="mt-6 space-y-3">
          <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
            Observations
          </p>
          {llmInterpretation.observations.map((observation) => (
            <section className="border-2 border-ink p-3" key={observation.id}>
              <p className="font-body text-sm leading-6">{observation.text}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {observation.metricEvidence.map((path) => (
                  <span
                    className="border-2 border-marker px-2 py-1 font-mono text-[10px]"
                    key={path}
                  >
                    {path}
                  </span>
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <EmptyChannelState text="No LLM observations returned." />
      )}

      <TextList
        items={report.presentation.recommendations}
        title="Recommendations"
      />
      <TextList items={report.presentation.limitations} title="Limitations" />
    </article>
  );
}

function UiclipLane({ report }: ReportDashboardProps) {
  const { uiclip, presentation } = report;
  const { uiclipSummary } = presentation;
  const statusClass = statusTone(uiclip.status);
  const rawScoreDisplay =
    uiclipSummary.rawScoreDisplay ??
    (typeof uiclip.qualityScore === "number"
      ? uiclip.qualityScore.toFixed(2)
      : "not available");
  const emptyObservationText =
    uiclip.status === "completed"
      ? "UIClip returned a score-only result; this provider did not return textual observations."
      : "No UIClip observations returned.";

  return (
    <article className="channel-lane lane-uiclip border-2 border-ink border-t-4 border-t-signal bg-paper p-4">
      <LaneHeader
        colorClass="text-signal"
        label="INDEPENDENT"
        subline="Does not see metrics or LLM output."
      />

      <div className="mt-5 grid gap-3">
        <DataPair
          label="status"
          value={uiclip.status}
          valueClassName={statusClass}
        />
        <DataPair
          label="modelId"
          value={uiclipSummary.modelId ?? "not available"}
        />
        <DataPair
          label="rawScore"
          value={rawScoreDisplay}
        />
        <DataPair
          label="scoreType"
          value={uiclipSummary.scoreType ?? "not available"}
        />
        <DataPair
          label="normalizedQualityScore"
          value={uiclip.normalizedQualityScore ?? "not available"}
          valueClassName={uiclip.normalizedQualityScore === null ? "text-void" : ""}
        />
        <DataPair
          label="descriptionSource"
          value={uiclip.descriptionSource ?? "not available"}
        />
      </div>

      {uiclipSummary.userDescription ? (
        <section className="mt-5 border-2 border-ink p-3">
          <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
            User description
          </p>
          <p className="mt-2 font-body text-sm leading-6">
            {uiclipSummary.userDescription}
          </p>
        </section>
      ) : null}

      <section className="mt-5 min-w-0 border-2 border-ink p-3">
        <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
          Comparability
        </p>
        <p className="mt-2 font-body text-sm leading-6">
          {uiclipSummary.comparabilityNote}
        </p>
      </section>

      {uiclip.observations.length > 0 ? (
        <TextList items={uiclip.observations} title="UIClip observations" />
      ) : (
        <EmptyChannelState text={emptyObservationText} />
      )}
    </article>
  );
}

interface LaneHeaderProps {
  colorClass: string;
  label: string;
  subline: string;
}

function LaneHeader({ colorClass, label, subline }: LaneHeaderProps) {
  return (
    <header>
      <p
        className={cx(
          "font-display text-lg font-bold uppercase tracking-[0.16em]",
          colorClass
        )}
      >
        {label}
      </p>
      <p className="mt-1 font-body text-sm leading-6">{subline}</p>
    </header>
  );
}

interface TextListProps {
  items: string[];
  title: string;
}

function TextList({ items, title }: TextListProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <section className="mt-6 min-w-0">
      <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
        {title}
      </p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <p
            className="min-w-0 break-words border-2 border-ink p-3 font-body text-sm leading-6"
            key={item}
          >
            {item}
          </p>
        ))}
      </div>
    </section>
  );
}

interface EmptyChannelStateProps {
  text: string;
}

function EmptyChannelState({ text }: EmptyChannelStateProps) {
  return (
    <p className="mt-5 border-2 border-ink p-3 font-body text-sm leading-6">
      {text}
    </p>
  );
}

interface DataPairProps {
  label: string;
  value: number | string;
  valueClassName?: string;
}

function DataPair({ label, value, valueClassName }: DataPairProps) {
  return (
    <div className="min-w-0 border-2 border-ink p-2">
      <dt className="break-words font-display text-[10px] font-bold uppercase tracking-[0.14em]">
        {label}
      </dt>
      <dd
        className={cx(
          "mt-1 break-words font-mono text-xs leading-5",
          valueClassName
        )}
      >
        {String(value)}
      </dd>
    </div>
  );
}

interface RawDataDrawerProps {
  analysisId: string;
  initialReport: AnalysisReport;
}

function RawDataDrawer({ analysisId, initialReport }: RawDataDrawerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [rawReport, setRawReport] = useState<AnalysisReport | null>(null);
  const [rawError, setRawError] = useState<ApiErrorPayload | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function toggleRawReport() {
    const nextOpen = !isOpen;
    setIsOpen(nextOpen);

    if (!nextOpen || rawReport || isLoading) {
      return;
    }

    setIsLoading(true);
    setRawError(null);
    try {
      const fetchedReport = await fetchRawReport(analysisId);
      setRawReport(fetchedReport);
    } catch (caughtError) {
      if (caughtError instanceof LucidApiError) {
        setRawError({
          code: caughtError.code,
          message: caughtError.message,
          details: caughtError.details
        });
      } else {
        setRawError({
          code: "RAW_REPORT_FAILED",
          message: "The raw report request did not complete."
        });
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="mt-8 border-4 border-ink bg-paper">
      <button
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between gap-4 bg-paper px-4 py-3 text-left font-display text-sm font-bold uppercase tracking-[0.14em]"
        type="button"
        onClick={toggleRawReport}
      >
        <span>View raw report</span>
        <span className="font-mono text-xs">{isOpen ? "open" : "closed"}</span>
      </button>

      {isOpen ? (
        <div className="border-t-4 border-ink">
          {rawError ? <ErrorBanner error={rawError} /> : null}
          <pre className="max-h-[620px] overflow-auto bg-ink p-4 font-mono text-xs leading-5 text-paper">
            {isLoading
              ? "loading raw report"
              : JSON.stringify(rawReport ?? initialReport, null, 2)}
          </pre>
        </div>
      ) : null}
    </section>
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
