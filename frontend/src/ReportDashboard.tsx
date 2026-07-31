import { useState } from "react";
import { LucidApiError, fetchRawReport } from "./api";
import type {
  AnalysisReport,
  ApiErrorPayload,
  MetricSection,
  StageStatus
} from "./types";
import { cx } from "./utils";

function statusTone(status: StageStatus) {
  return status === "failed" || status === "unavailable" ? "text-void" : "";
}

interface ReportDashboardProps {
  report: AnalysisReport;
}

export function ReportDashboard({ report }: ReportDashboardProps) {
  return (
    <section className="report-shell mt-10">
      <AnalysisSummary report={report} />

      <div className="channel-grid mt-8 grid min-w-0 gap-6 lg:grid-cols-2">
        <DeterministicLane report={report} />
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
    </section>
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

export interface DataPairProps {
  label: string;
  value: number | string;
  valueClassName?: string;
}

export function DataPair({ label, value, valueClassName }: DataPairProps) {
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

export interface ErrorBannerProps {
  error: ApiErrorPayload;
}

export function ErrorBanner({ error }: ErrorBannerProps) {
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
