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
  if (status === "completed") {
    return "text-signal";
  }

  return status === "failed" || status === "unavailable" ? "text-void" : "";
}

const METRIC_EXPLANATIONS: Record<string, string> = {
  contrast:
    "Shows how clearly text and interface elements stand out from their backgrounds.",
  "visual-complexity":
    "Estimates how visually dense or crowded the interface appears by measuring edge detail.",
  "elements-target-size":
    "Checks whether detected interactive elements are large enough to tap or click comfortably.",
  "hicks-law":
    "Estimates how much choice load the visible controls may create for a user.",
  grouping:
    "Looks at how many visual groups the interface appears to contain and how easy the structure is to scan.",
  "text-density":
    "Measures how much of the screenshot is occupied by text, which can affect reading effort.",
  "whitespace-alignment":
    "Looks at open space and alignment consistency to show whether the layout has room to breathe.",
  colorfulness:
    "Measures the strength of color in the screenshot as a signal for visual emphasis.",
  "fitts-law":
    "Estimates how much effort it may take to move to and use detected controls.",
  "visual-balance":
    "Checks whether visual weight is distributed evenly across the screen."
};

const METRIC_UNAVAILABLE_COPY: Record<
  string,
  { title: string; explanation: string }
> = {
  contrast: {
    title: "Contrast unavailable",
    explanation: "Reliable foreground and background regions could not be detected."
  },
  "visual-complexity": {
    title: "Visual complexity could not be calculated",
    explanation:
      "The edge-density measurement was missing from the deterministic analysis output."
  },
  "elements-target-size": {
    title: "Element target size could not be calculated",
    explanation:
      "No reliable element detections were available to compare against target-size guidance."
  },
  "hicks-law": {
    title: "Hick's Law estimate could not be calculated",
    explanation:
      "The estimate needs detected choices or controls, and that measurement was not available."
  },
  grouping: {
    title: "Grouping could not be calculated",
    explanation:
      "The analyzer could not identify enough stable visual groups in this screenshot."
  },
  "text-density": {
    title: "Text density could not be calculated",
    explanation:
      "No readable text regions were detected for this measurement."
  },
  "whitespace-alignment": {
    title: "Alignment detail could not be calculated",
    explanation:
      "One of the layout measurements needed for this card was missing from the analysis output."
  },
  colorfulness: {
    title: "Colorfulness could not be calculated",
    explanation:
      "The colorfulness signal was not returned for this screenshot."
  },
  "fitts-law": {
    title: "Fitts's Law estimate could not be calculated",
    explanation:
      "No eligible interaction targets were detected for the movement-difficulty estimate."
  },
  "visual-balance": {
    title: "Visual balance could not be calculated",
    explanation:
      "The layout balance signal was not returned for this screenshot."
  }
};

const STATUS_LABELS: Record<StageStatus, string> = {
  completed: "Analysis Completed",
  disabled: "Analysis Disabled",
  unavailable: "Analysis Unavailable",
  fallback: "Fallback Analysis",
  failed: "Analysis Failed"
};

const NORMALIZED_DIRECTION_COPY: Record<string, string> = {
  contrast: "Higher score = stronger estimated contrast.",
  "visual-complexity": "Higher score = lower visual complexity.",
  "elements-target-size": "Higher score = fewer undersized targets.",
  grouping: "Higher score = grouping closer to the reference range.",
  "text-density": "Higher score = lower text density."
};

const RAW_DIRECTION_COPY: Record<string, string> = {
  "hicks-law": "Higher raw estimate = greater choice complexity.",
  "whitespace-alignment":
    "Higher whitespace can mean more open space; lower alignment variance means steadier alignment.",
  colorfulness: "Higher raw value = stronger color intensity.",
  "fitts-law": "Higher raw estimate = greater movement difficulty.",
  "visual-balance": "Higher asymmetry = less visual balance."
};

function metricExplanation(metric: MetricSection) {
  return METRIC_EXPLANATIONS[metric.id] ?? metric.explanation;
}

function metricUnavailableCopy(metric: MetricSection) {
  return (
    METRIC_UNAVAILABLE_COPY[metric.id] ?? {
      title: `${metric.title} could not be calculated`,
      explanation:
        "The source measurement needed for this metric was not available in the analysis output."
    }
  );
}

function hasUnavailableMetricData(metric: MetricSection) {
  const rawDisplay = metric.rawDisplay.toLowerCase();

  return (
    rawDisplay.includes("no data available") ||
    rawDisplay.includes("unavailable") ||
    rawDisplay.includes("could not be calculated")
  );
}

function metricRawDisplay(metric: MetricSection) {
  if (!hasUnavailableMetricData(metric)) {
    return metric.rawDisplay;
  }

  if (metric.rawDisplay.trim() === "No data available") {
    return metricUnavailableCopy(metric).title;
  }

  return metric.rawDisplay.replaceAll(
    "No data available",
    "could not be calculated"
  );
}

function formatScoreValue(score: number | string | null | undefined) {
  if (score === null || score === undefined || score === "") {
    return "not available";
  }

  const numericScore =
    typeof score === "number" ? score : Number.parseFloat(score);

  if (Number.isFinite(numericScore)) {
    return new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 1
    }).format(numericScore);
  }

  return String(score);
}

function formatNormalizedScore(score: number | string | null | undefined) {
  const value = formatScoreValue(score);
  return value === "not available" ? value : `${value} / 100`;
}

function humanizeToken(value: string | null | undefined) {
  if (!value) {
    return "not available";
  }

  return value
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusLabel(status: StageStatus) {
  return STATUS_LABELS[status] ?? humanizeToken(status);
}

function normalizedMetricInterpretation(metric: MetricSection) {
  if (metric.normalizedScore === null) {
    return null;
  }

  const score = metric.normalizedScore;

  if (metric.id === "visual-complexity") {
    if (score >= 70) {
      return "Low Complexity";
    }
    if (score >= 40) {
      return "Moderate Complexity";
    }
    return "High Complexity";
  }

  if (metric.id === "text-density") {
    if (score >= 70) {
      return "Low Text Load";
    }
    if (score >= 40) {
      return "Moderate Text Load";
    }
    return "High Text Load";
  }

  if (score >= 70) {
    return "Strong Result";
  }

  if (score >= 40) {
    return "Moderate";
  }

  return "Needs Attention";
}

function metricDirectionCopy(metric: MetricSection) {
  if (metric.normalizedScore !== null) {
    return (
      NORMALIZED_DIRECTION_COPY[metric.id] ??
      "Higher score = stronger normalized signal."
    );
  }

  return RAW_DIRECTION_COPY[metric.id] ?? "Read this value in the raw unit shown above.";
}

function findMetric(report: AnalysisReport, metricId: string) {
  return report.presentation.metricSections.find((metric) => metric.id === metricId);
}

function sentenceCase(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function visualComplexityFinding(metric: MetricSection) {
  const interpretation = normalizedMetricInterpretation(metric);

  if (!interpretation) {
    return hasUnavailableMetricData(metric)
      ? "Visual complexity could not be measured"
      : "Visual complexity result available";
  }

  return `${sentenceCase(interpretation).replace(" complexity", "")} visual complexity detected`;
}

function targetSizeStatus(metric: MetricSection) {
  if (metric.normalizedScore === null || hasUnavailableMetricData(metric)) {
    return null;
  }

  if (metric.normalizedScore >= 70) {
    return "Meets target";
  }

  if (metric.normalizedScore >= 40) {
    return "Partially meets target";
  }

  return "Needs attention";
}

function buildDeterministicFindings(report: AnalysisReport) {
  const findings: string[] = [];
  const visualComplexityMetric = findMetric(report, "visual-complexity");
  const contrastMetric = findMetric(report, "contrast");
  const targetSizeMetric = findMetric(report, "elements-target-size");
  const normalizedCount = report.presentation.metricSections.filter(
    (metric) => metric.normalizedScore !== null
  );

  if (visualComplexityMetric) {
    findings.push(visualComplexityFinding(visualComplexityMetric));
  }

  if (contrastMetric && hasUnavailableMetricData(contrastMetric)) {
    findings.push("Contrast could not be measured");
  } else if (contrastMetric) {
    findings.push("Contrast result available");
  }

  if (targetSizeMetric && targetSizeStatus(targetSizeMetric)) {
    findings.push(`Target-size status: ${targetSizeStatus(targetSizeMetric)}`);
  } else if (targetSizeMetric && !hasUnavailableMetricData(targetSizeMetric)) {
    findings.push("Target-size results available");
  }

  if (findings.length < 3) {
    findings.push(`${normalizedCount.length} normalized deterministic signals available`);
  }

  return findings.slice(0, 3);
}

function isMockUiclip(report: AnalysisReport) {
  const modelText = [
    report.presentation.uiclipSummary.modelId,
    report.uiclip.modelVersion,
    report.note,
    report.presentation.closingNote
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return modelText.includes("mock") || modelText.includes("offline");
}

function userSubmittedDescription(report: AnalysisReport) {
  if (report.presentation.uiclipSummary.userDescription) {
    return report.presentation.uiclipSummary.userDescription;
  }

  if (report.uiclip.descriptionSource === "user" && report.uiclip.description) {
    return report.uiclip.description;
  }

  return null;
}

function normalizedUiclipScore(report: AnalysisReport) {
  const { uiclip, presentation } = report;
  const { uiclipSummary } = presentation;

  if (uiclipSummary.normalizedScoreDisplay !== null) {
    return formatNormalizedScore(uiclipSummary.normalizedScoreDisplay);
  }

  if (typeof uiclip.normalizedQualityScore === "number") {
    return formatNormalizedScore(uiclip.normalizedQualityScore);
  }

  return "not available";
}

function imageMetadataDisplay(report: AnalysisReport) {
  const { imageMetadata } = report;

  return imageMetadata.width && imageMetadata.height
    ? `${imageMetadata.width} x ${imageMetadata.height}`
    : "not available";
}

function downloadReport(report: AnalysisReport) {
  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json"
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeId = report.analysisId.replace(/[^a-z0-9_-]+/gi, "-");

  link.href = url;
  link.download = `lucidui-report-${safeId}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

interface ReportDashboardProps {
  report: AnalysisReport;
  onAnalyzeAnother?: () => void;
}

export function ReportDashboard({
  report,
  onAnalyzeAnother
}: ReportDashboardProps) {
  return (
    <section className="report-shell mt-10">
      <ScoreMethodBanner />

      <div className="channel-grid mt-6 grid min-w-0 items-stretch gap-6 lg:grid-cols-2">
        <DeterministicSummaryCard report={report} />
        <UiclipSummaryCard report={report} />
      </div>

      <DetailedMetricsSection
        report={report}
        onAnalyzeAnother={onAnalyzeAnother}
      />
      <AnalysisContextSection report={report} />
      <ReportActions report={report} onAnalyzeAnother={onAnalyzeAnother} />
    </section>
  );
}

function ScoreMethodBanner() {
  return (
    <section className="border-2 border-l-8 border-ink border-l-marker bg-paper px-3 py-2 sm:px-4">
      <p className="font-display text-xs font-bold uppercase tracking-[0.14em] text-marker">
        Different Scales
      </p>
      <p className="mt-1 font-body text-sm leading-5">
        These results use different scoring methods and should not be compared directly.
      </p>
    </section>
  );
}

function DeterministicSummaryCard({ report }: ReportDashboardProps) {
  const findings = buildDeterministicFindings(report);

  return (
    <article className="channel-lane lane-deterministic flex h-full min-w-0 flex-col border-2 border-ink border-t-4 border-t-blueprint bg-paper p-4 sm:p-5">
      <LaneHeader
        colorClass="text-blueprint"
        label="DETERMINISTIC"
        title="Rule-Based UI Metrics"
        subline="Calculated only from measurable visual properties of the screenshot."
      />

      <div className="mt-5 min-w-0 border-2 border-ink p-3">
        <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
          Signal Index
        </p>
        <p className="mt-2 break-words font-mono text-4xl leading-none">
          {formatScoreValue(report.presentation.composite.value)}
        </p>
        <p className="mt-3 font-body text-sm leading-6">
          A weighted index from normalized rule-based metrics. It is a review
          signal, not a direct quality grade.
        </p>
      </div>

      <ul className="mt-4 grid gap-2 font-body text-sm leading-6">
        {findings.map((finding) => (
          <li className="border-l-4 border-blueprint pl-3" key={finding}>
            {finding}
          </li>
        ))}
      </ul>
    </article>
  );
}

interface MetricCardProps {
  metric: MetricSection;
  onAnalyzeAnother?: () => void;
}

function MetricCard({ metric, onAnalyzeAnother }: MetricCardProps) {
  const hasUnavailableData = hasUnavailableMetricData(metric);
  const unavailableCopy = metricUnavailableCopy(metric);
  const normalizedInterpretation = normalizedMetricInterpretation(metric);
  const targetStatus = metric.id === "elements-target-size" ? targetSizeStatus(metric) : null;
  const isContrastUnavailable = hasUnavailableData && metric.id === "contrast";
  const shouldShowNormalizedScore =
    metric.normalizedScore !== null && !isContrastUnavailable;
  const explanation = hasUnavailableData
    ? unavailableCopy.explanation
    : metricExplanation(metric);

  return (
    <section className="min-w-0 border-2 border-ink bg-paper p-3 sm:p-4">
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

      <p
        className={cx(
          "mt-3 break-words font-mono leading-tight",
          isContrastUnavailable ? "text-sm text-marker" : "text-2xl",
          hasUnavailableData && !isContrastUnavailable ? "text-void" : ""
        )}
      >
        {metricRawDisplay(metric)}
      </p>
      {shouldShowNormalizedScore ? (
        <p className="mt-2 font-mono text-xs uppercase leading-5">
          Normalized signal: {formatNormalizedScore(metric.normalizedScore)} ·{" "}
          {normalizedInterpretation}
        </p>
      ) : null}
      <p className="mt-3 font-body text-sm leading-6">
        {explanation}
      </p>
      {targetStatus ? (
        <p className="mt-2 font-mono text-xs uppercase leading-5">
          Target-size status: {targetStatus}
        </p>
      ) : null}
      {!isContrastUnavailable ? (
        <p className="mt-2 font-mono text-xs uppercase leading-5">
          Direction: {metricDirectionCopy(metric)}
        </p>
      ) : null}
      {isContrastUnavailable && onAnalyzeAnother ? (
        <button
          className="mt-3 border-2 border-marker bg-paper px-3 py-2 font-display text-[11px] font-bold uppercase text-marker"
          type="button"
          onClick={onAnalyzeAnother}
        >
          Upload a clearer screenshot
        </button>
      ) : null}
    </section>
  );
}

function UiclipSummaryCard({ report }: ReportDashboardProps) {
  const { uiclip, presentation } = report;
  const { uiclipSummary } = presentation;
  const scoreValue = uiclipSummary.rawScoreDisplay ?? uiclip.qualityScore;
  const scoreDisplay = formatScoreValue(scoreValue);
  const isMockResult = isMockUiclip(report);

  return (
    <article className="channel-lane lane-uiclip flex h-full min-w-0 flex-col border-2 border-ink border-t-4 border-t-signal bg-paper p-4 sm:p-5">
      <LaneHeader
        colorClass="text-signal"
        label="INDEPENDENT"
        title="AI-Based Review"
        subline="Generated independently from the screenshot and submitted description."
      />

      <section className="mt-5 min-w-0 border-2 border-ink p-3">
        <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
          Raw AI Score
        </p>
        <div className="mt-3 flex min-w-0 flex-wrap items-center gap-3">
          <p className="break-words font-mono text-4xl leading-none">
            {scoreDisplay}
          </p>
          <StatusBadge status={uiclip.status} />
          {isMockResult ? <MockBadge /> : null}
        </div>
        <p className="mt-3 font-body text-sm leading-6">
          {isMockResult
            ? "Placeholder output from the offline evaluator. No live model evaluation was performed."
            : "Raw model output from the independent AI review."}
        </p>
      </section>
    </article>
  );
}

interface StatusBadgeProps {
  status: StageStatus;
}

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={cx(
        "shrink-0 border-2 border-ink px-2 py-1 font-mono text-[10px]",
        statusTone(status)
      )}
    >
      ● {statusLabel(status)}
    </span>
  );
}

function MockBadge() {
  return (
    <span className="shrink-0 border-2 border-marker px-2 py-1 font-mono text-[10px] uppercase text-marker">
      Mock Result
    </span>
  );
}

function DetailedMetricsSection({
  report,
  onAnalyzeAnother
}: ReportDashboardProps) {
  return (
    <section className="mt-8 border-4 border-ink bg-paper p-4 sm:p-5">
      <SectionHeader
        title="Detailed UI Metrics"
        subline="Deterministic measurements from the screenshot, shown without changing the underlying values."
      />
      <div className="mt-5 grid min-w-0 gap-4 md:grid-cols-2">
        {report.presentation.metricSections.map((metric) => (
          <MetricCard
            key={metric.id}
            metric={metric}
            onAnalyzeAnother={onAnalyzeAnother}
          />
        ))}
      </div>
    </section>
  );
}

function AnalysisContextSection({ report }: ReportDashboardProps) {
  const description = userSubmittedDescription(report);

  return (
    <section className="mt-8 border-4 border-ink bg-paper p-4 sm:p-5">
      <SectionHeader
        title="Analysis Context"
        subline="Submitted context and secondary report metadata."
      />
      <div className="mt-5 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="min-w-0 border-2 border-ink p-3 sm:p-4">
          <p className="font-display text-xs font-bold uppercase tracking-[0.14em]">
            Your Description
          </p>
          {description ? (
            <ExpandableDescription description={description} />
          ) : (
            <p className="mt-2 font-body text-sm leading-6">
              No user description was submitted for this analysis.
            </p>
          )}
        </section>

        <TechnicalDetailsAccordion report={report} />
      </div>
      <RawDataDrawer analysisId={report.analysisId} initialReport={report} />
    </section>
  );
}

interface ExpandableDescriptionProps {
  description: string;
}

function ExpandableDescription({ description }: ExpandableDescriptionProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const canExpand = description.length > 220;

  return (
    <div>
      <p
        className={cx(
          "mt-2 font-body text-sm leading-6",
          canExpand && !isExpanded ? "description-clamp" : ""
        )}
      >
        {description}
      </p>
      {canExpand ? (
        <button
          className="mt-3 border-2 border-ink bg-paper px-3 py-2 font-display text-[11px] font-bold uppercase"
          type="button"
          onClick={() => setIsExpanded((current) => !current)}
        >
          {isExpanded ? "Show less" : "Show more"}
        </button>
      ) : null}
    </div>
  );
}

function TechnicalDetailsAccordion({ report }: ReportDashboardProps) {
  const { uiclip, presentation, timings } = report;
  const { uiclipSummary } = presentation;
  const normalizedScore = normalizedUiclipScore(report);
  const hasRawScore =
    Boolean(uiclipSummary.rawScoreDisplay) ||
    typeof uiclip.qualityScore === "number";
  const modelId = uiclipSummary.modelId ?? uiclip.modelVersion ?? "not available";
  const rawMetadata = [
    `enabled: ${uiclip.enabled ? "yes" : "no"}`,
    `status: ${statusLabel(uiclip.status)}`,
    `inference: ${
      typeof timings.uiclipMs === "number" ? `${timings.uiclipMs} ms` : "not available"
    }`
  ].join("; ");
  const metricSourceNotes = presentation.metricSections
    .filter((metric) => metric.source)
    .map((metric) => `${metric.title}: ${metric.source}`)
    .join("\n");

  return (
    <section className="min-w-0 border-2 border-ink p-3 sm:p-4">
      <details>
        <summary className="cursor-pointer font-display text-xs font-bold uppercase tracking-[0.14em] text-signal">
          Technical Details
        </summary>
        <dl className="mt-3">
          <DetailRow label="Analysis ID" value={report.analysisId} />
          <DetailRow label="Report Status" value={report.status} />
          <DetailRow label="Context" value={report.context} />
          <DetailRow
            label="Total Time"
            value={
              typeof timings.totalMs === "number"
                ? `${timings.totalMs} ms`
                : "not available"
            }
          />
          <DetailRow label="Image" value={imageMetadataDisplay(report)} />
          <DetailRow
            label="Image Format"
            value={report.imageMetadata.format ?? "not available"}
          />
          <DetailRow
            label="Normalized Score"
            value={normalizedScore}
            valueClassName={normalizedScore === "not available" ? "text-void" : ""}
          />
          <DetailRow
            label="Model ID"
            value={modelId}
          />
          <DetailRow
            label="Score Method"
            value={uiclipSummary.scoreType ?? "not available"}
          />
          <DetailRow label="Raw Model Metadata" value={rawMetadata} />
          <DetailRow
            label="Normalized Score Availability"
            value={
              normalizedScore === "not available"
                ? "No normalized UIClip score was returned."
                : normalizedScore
            }
          />
          <DetailRow
            label="Raw Score Source"
            value={hasRawScore ? "UIClip model output" : "not available"}
          />
          <DetailRow
            label="Comparability Note"
            value={uiclipSummary.comparabilityNote}
          />
          <DetailRow
            label="Description Provided By"
            value={humanizeToken(uiclip.descriptionSource)}
          />
          <DetailRow
            label="Mock Provider Details"
            value={
              isMockUiclip(report)
                ? "Offline mock evaluator. No live model evaluation was performed."
                : "No mock provider marker was present in this report."
            }
          />
          <DetailRow
            label="Implementation Notes"
            value={presentation.closingNote}
          />
          <DetailRow
            label="Metric Source Notes"
            value={metricSourceNotes || "not available"}
          />
        </dl>
      </details>
    </section>
  );
}

function ReportActions({ report, onAnalyzeAnother }: ReportDashboardProps) {
  return (
    <section className="mt-8 border-4 border-ink bg-paper p-4 sm:p-5">
      <div className="flex flex-wrap gap-3">
        {onAnalyzeAnother ? (
          <button
            className="border-2 border-ink bg-ink px-4 py-3 font-display text-xs font-bold uppercase tracking-[0.14em] text-paper"
            type="button"
            onClick={onAnalyzeAnother}
          >
            Analyze Another Screenshot
          </button>
        ) : null}
        <button
          className="border-2 border-ink bg-paper px-4 py-3 font-display text-xs font-bold uppercase tracking-[0.14em]"
          type="button"
          onClick={() => downloadReport(report)}
        >
          Download Report
        </button>
      </div>
    </section>
  );
}

interface SectionHeaderProps {
  title: string;
  subline?: string;
}

function SectionHeader({ title, subline }: SectionHeaderProps) {
  return (
    <header>
      <h2 className="font-display text-xl font-bold uppercase tracking-[0.08em]">
        {title}
      </h2>
      {subline ? (
        <p className="mt-2 font-body text-sm leading-6">{subline}</p>
      ) : null}
    </header>
  );
}

interface DetailRowProps {
  label: string;
  value: number | string;
  valueClassName?: string;
}

function DetailRow({ label, value, valueClassName }: DetailRowProps) {
  return (
    <div className="border-t-2 border-ink py-2 first:border-t-0 first:pt-0">
      <dt className="break-words font-display text-[10px] font-bold uppercase tracking-[0.14em]">
        {label}
      </dt>
      <dd
        className={cx(
          "mt-1 whitespace-pre-wrap break-words font-mono text-xs leading-5",
          valueClassName
        )}
      >
        {String(value)}
      </dd>
    </div>
  );
}

interface LaneHeaderProps {
  colorClass: string;
  label: string;
  title: string;
  subline: string;
}

function LaneHeader({ colorClass, label, title, subline }: LaneHeaderProps) {
  return (
    <header>
      <p
        className={cx(
          "font-display text-xs font-bold uppercase tracking-[0.16em]",
          colorClass
        )}
      >
        {label}
      </p>
      <h2 className="mt-2 font-display text-xl font-bold uppercase tracking-[0.08em]">
        {title}
      </h2>
      <p className="mt-2 font-body text-sm leading-6">{subline}</p>
    </header>
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
    <section className="mt-5 border-2 border-ink bg-paper">
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
        <div className="border-t-2 border-ink">
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
