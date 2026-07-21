import { FormEvent, useEffect, useState } from "react";
import { LucidApiError, submitVariantAnalysis } from "./api";
import { DataPair, ErrorBanner, ReportDashboard } from "./ReportDashboard";
import type {
  AnalysisContext,
  ApiErrorPayload,
  MetricDelta,
  VariantAnalysisReport
} from "./types";
import { ACCEPTED_TYPES, validateFile } from "./upload";
import { cx, formatBytes } from "./utils";

type CompareUiState =
  | "idle"
  | "ready"
  | "submitting"
  | "completed"
  | "partial_success"
  | "failed";

export function CompareView() {
  const [uiState, setUiState] = useState<CompareUiState>("idle");
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [previewUrlA, setPreviewUrlA] = useState<string | null>(null);
  const [previewUrlB, setPreviewUrlB] = useState<string | null>(null);
  const [context, setContext] = useState<AnalysisContext>("general");
  const [descriptionA, setDescriptionA] = useState("");
  const [descriptionB, setDescriptionB] = useState("");
  const [runUiclip, setRunUiclip] = useState(true);
  const [report, setReport] = useState<VariantAnalysisReport | null>(null);
  const [error, setError] = useState<ApiErrorPayload | null>(null);

  const isWorking = uiState === "submitting";

  useEffect(() => {
    if (!fileA) {
      setPreviewUrlA(null);
      return;
    }
    const objectUrl = URL.createObjectURL(fileA);
    setPreviewUrlA(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [fileA]);

  useEffect(() => {
    if (!fileB) {
      setPreviewUrlB(null);
      return;
    }
    const objectUrl = URL.createObjectURL(fileB);
    setPreviewUrlB(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [fileB]);

  function selectFile(slot: "a" | "b", nextFile: File | null) {
    if (!nextFile) {
      return;
    }

    const validationError = validateFile(nextFile);
    if (validationError) {
      setError(validationError);
      setUiState("failed");
      return;
    }

    setError(null);
    setReport(null);
    if (slot === "a") {
      setFileA(nextFile);
    } else {
      setFileB(nextFile);
    }
    setUiState("ready");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!fileA || !fileB) {
      setError({
        code: "VALIDATION_ERROR",
        message: "Select a screenshot for both variant A and variant B before comparing."
      });
      setUiState("failed");
      return;
    }

    setError(null);
    setReport(null);
    setUiState("submitting");

    try {
      const nextReport = await submitVariantAnalysis({
        fileA,
        fileB,
        context,
        descriptionA,
        descriptionB,
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
            "The comparison request did not complete. Check the backend service and try again."
        });
      }
      setUiState("failed");
    }
  }

  return (
    <>
      <form
        className="intake-block grid gap-6 border-4 border-ink bg-paper p-4 sm:p-6"
        onSubmit={handleSubmit}
      >
        <div>
          <p className="font-display text-sm font-bold uppercase tracking-[0.18em]">
            Lab intake — compare
          </p>
          <h1 className="mt-2 max-w-3xl font-display text-3xl font-bold uppercase tracking-[0.08em] sm:text-5xl">
            Two variants, one comparison
          </h1>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <VariantIntake
            description={descriptionA}
            file={fileA}
            label="Variant A"
            previewUrl={previewUrlA}
            onDescriptionChange={setDescriptionA}
            onFileSelect={(nextFile) => selectFile("a", nextFile)}
          />
          <VariantIntake
            description={descriptionB}
            file={fileB}
            label="Variant B"
            previewUrl={previewUrlB}
            onDescriptionChange={setDescriptionB}
            onFileSelect={(nextFile) => selectFile("b", nextFile)}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-[0.7fr_1.3fr]">
          <fieldset className="border-2 border-ink p-3">
            <legend className="px-2 font-display text-xs font-bold uppercase tracking-[0.16em]">
              Context (shared)
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
                  onClick={() => setContext(value)}
                >
                  {value}
                </button>
              ))}
            </div>
          </fieldset>

          <label className="flex items-center gap-3 border-2 border-ink p-3 font-body text-sm font-medium">
            <input
              checked={runUiclip}
              className="h-5 w-5 border-2 border-ink accent-signal"
              type="checkbox"
              onChange={(event) => setRunUiclip(event.target.checked)}
            />
            <span>Run UIClip (both variants)</span>
          </label>
        </div>

        <div className="flex justify-end border-2 border-ink p-4">
          <button
            className="border-2 border-ink bg-ink px-6 py-3 font-display text-sm font-bold uppercase tracking-[0.14em] text-paper shadow-stamp disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isWorking}
            type="submit"
          >
            Run comparison
          </button>
        </div>
      </form>

      {error ? <ErrorBanner error={error} /> : null}

      {report ? (
        <section className="mt-10">
          <DeltaPanel report={report} />

          <div className="mt-8 grid gap-6 xl:grid-cols-2">
            <div>
              <VariantLabel label="Variant A" />
              <ReportDashboard report={report.variantA} />
            </div>
            <div>
              <VariantLabel label="Variant B" />
              <ReportDashboard report={report.variantB} />
            </div>
          </div>
        </section>
      ) : null}
    </>
  );
}

interface VariantLabelProps {
  label: string;
}

function VariantLabel({ label }: VariantLabelProps) {
  return (
    <p className="border-2 border-ink bg-ink px-3 py-2 font-display text-xs font-bold uppercase tracking-[0.16em] text-paper">
      {label}
    </p>
  );
}

interface VariantIntakeProps {
  description: string;
  file: File | null;
  label: string;
  previewUrl: string | null;
  onDescriptionChange: (description: string) => void;
  onFileSelect: (file: File | null) => void;
}

function VariantIntake({
  description,
  file,
  label,
  previewUrl,
  onDescriptionChange,
  onFileSelect
}: VariantIntakeProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputId = `variant-upload-${label.toLowerCase().replace(/\s+/g, "-")}`;

  return (
    <div className="border-2 border-ink p-3">
      <p className="font-display text-xs font-bold uppercase tracking-[0.16em]">
        {label}
      </p>

      <div
        className={cx(
          "relative mt-3 border-4 border-ink bg-paper p-4",
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
        <input
          accept={ACCEPTED_TYPES.join(",")}
          className="sr-only"
          id={inputId}
          type="file"
          onChange={(event) => onFileSelect(event.target.files?.item(0) ?? null)}
        />
        <label
          className="flex min-h-28 cursor-pointer flex-col justify-end gap-2"
          htmlFor={inputId}
        >
          <span className="font-display text-base font-bold uppercase tracking-[0.1em]">
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

      <div className="mt-3 flex min-h-32 items-center justify-center border-2 border-ink bg-[#F7F7F2]">
        {previewUrl ? (
          <img
            alt={file?.name ?? `${label} preview`}
            className="max-h-40 w-full object-contain"
            src={previewUrl}
          />
        ) : (
          <p className="px-4 text-center font-mono text-xs uppercase">
            No sample selected
          </p>
        )}
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 font-mono text-xs uppercase">
        <DataPair label="File" value={file?.name ?? "not available"} />
        <DataPair label="Size" value={formatBytes(file?.size)} />
      </dl>

      <label className="mt-3 block">
        <span className="font-display text-xs font-bold uppercase tracking-[0.14em]">
          Description
        </span>
        <textarea
          className="mt-2 min-h-20 w-full resize-y border-2 border-ink bg-paper p-3 font-body text-sm leading-6 outline-none"
          placeholder="Optional description used by UIClip for this variant."
          value={description}
          onChange={(event) => onDescriptionChange(event.target.value)}
        />
      </label>
    </div>
  );
}

interface DeltaPanelProps {
  report: VariantAnalysisReport;
}

function DeltaPanel({ report }: DeltaPanelProps) {
  const { deltas } = report;

  return (
    <section className="border-4 border-ink bg-paper p-4 sm:p-6">
      <p className="font-display text-sm font-bold uppercase tracking-[0.18em]">
        Relative deltas — variant B vs. variant A
      </p>
      <p className="mt-2 font-body text-sm leading-6">{deltas.note}</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <DataPair label="Composite score delta" value={deltas.compositeScoreDeltaDisplay} />
        <DataPair label="UIClip raw score delta" value={deltas.uiclipRawScoreDeltaDisplay} />
      </div>

      <div className="mt-5 grid min-w-0 gap-3">
        {deltas.metricDeltas.map((metricDelta) => (
          <MetricDeltaRow key={metricDelta.id} metricDelta={metricDelta} />
        ))}
      </div>
    </section>
  );
}

interface MetricDeltaRowProps {
  metricDelta: MetricDelta;
}

const DIRECTION_LABEL: Record<MetricDelta["direction"], string> = {
  higher: "▲ higher in B",
  lower: "▼ lower in B",
  equal: "= equal",
  not_available: "not available"
};

function MetricDeltaRow({ metricDelta }: MetricDeltaRowProps) {
  return (
    <section className="min-w-0 border-2 border-ink bg-paper p-3">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-sm font-bold uppercase tracking-[0.12em]">
            {metricDelta.title}
          </h3>
          <p className="mt-1 font-mono text-[11px] uppercase">{metricDelta.category}</p>
        </div>
        <span className="shrink-0 border-2 border-ink px-2 py-1 font-mono text-[10px] uppercase">
          {DIRECTION_LABEL[metricDelta.direction]}
        </span>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2 font-mono text-xs uppercase">
        <DataPair label="A" value={metricDelta.rawDisplayA} />
        <DataPair label="B" value={metricDelta.rawDisplayB} />
      </dl>
    </section>
  );
}
