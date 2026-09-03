/**
 * ResultArea component — displays the outcome of a Phase 12 revision request.
 *
 * Phase 12: renders the :interface:`RevisionResponse` returned by
 * ``POST /api/revisions``:
 *   - SVG preview (via ``dangerouslySetInnerHTML``).
 *   - PNG preview (decoded from ``png_base64``).
 *   - Quality report: score, passed status, issues, warnings, suggestions.
 *   - Revision count and overall pass/fail.
 *   - SVG / PNG download buttons.
 *   - A Regenerate button to produce another variation.
 *   - Loading and error states.
 */

import type { QualityReportData } from "@/types/api";

interface ResultAreaProps {
  svgContent: string | null;
  pngBase64: string | null;
  qualityReport: QualityReportData | null;
  revisions: number | null;
  passed: boolean | null;
  usedTemplate: string | null;
  visualType: string;
  complexity: string;
  loading: boolean;
  error: string | null;
  onRegenerate: () => void;
  regenerateDisabled?: boolean;
}

function svgDataUri(svg: string): string {
  // Encode as UTF-8 base64 so non-ASCII characters in the SVG are safe.
  const encoded = btoa(unescape(encodeURIComponent(svg)));
  return `data:image/svg+xml;base64,${encoded}`;
}

function pngDataUri(base64: string): string {
  return `data:image/png;base64,${base64}`;
}

function renderList(label: string, items: string[]): JSX.Element {
  // Always render the section so Issues / Warnings / Suggestions are visible
  // even when the revision engine resolves all issues (they may be empty).
  return (
    <div className="quality-list">
      <span className="quality-list-label">{label}</span>
      {items && items.length > 0 ? (
        <ul className="quality-list-items">
          {items.map((item, i) => (
            <li key={`${label}-${i}`} className="quality-list-item">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <span className="quality-list-empty">None</span>
      )}
    </div>
  );
}

export default function ResultArea({
  svgContent,
  pngBase64,
  qualityReport,
  revisions,
  passed,
  usedTemplate,
  visualType,
  complexity,
  loading,
  error,
  onRegenerate,
  regenerateDisabled = false,
}: ResultAreaProps) {
  // ── Loading ────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="result-area">
        <div className="result-placeholder">
          <div className="spinner spinner-centered" />
          <p className="result-text">Refining your visual…</p>
          <p className="result-message">
            The backend is running the revision loop (max 3 attempts) and
            rendering the SVG/PNG.
          </p>
        </div>
      </div>
    );
  }

  // ── Error ──────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="result-area">
        <div className="result-placeholder result-error">
          <div className="result-icon">⚠️</div>
          <p className="result-text">Generation failed.</p>
          <p className="result-message error-message">{error}</p>
        </div>
      </div>
    );
  }

  // ── Result ──────────────────────────────────────────────────────────────
  if (svgContent || pngBase64 || qualityReport) {
    const score = qualityReport?.score ?? null;
    const scoreLabel =
      score !== null
        ? `${score > 85 ? "✓" : score > 60 ? "⚠" : "✗"} ${score.toFixed(1)} / 100`
        : "n/a";

    return (
      <div className="result-area">
        <div className="result-content">
          {/* ── Previews ── */}
          <div className="preview-grid">
            {svgContent && (
              <div className="preview pane">
                <div
                  className="svg-container"
                  dangerouslySetInnerHTML={{ __html: svgContent }}
                />
                <a
                  className="btn btn-small btn-outline download-btn"
                  href={svgDataUri(svgContent)}
                  download="visual.svg"
                  title="Download SVG"
                >
                  ⬇ SVG
                </a>
              </div>
            )}

            {pngBase64 && (
              <div className="preview pane">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  className="result-image png-preview"
                  src={pngDataUri(pngBase64)}
                  alt="Generated visual (PNG)"
                />
                <a
                  className="btn btn-small btn-outline download-btn"
                  href={pngDataUri(pngBase64)}
                  download="visual.png"
                  title="Download PNG"
                >
                  ⬇ PNG
                </a>
              </div>
            )}
          </div>

          {/* ── Metadata strip ── */}
          <div className="meta-strip">
            {usedTemplate && (
              <span className="meta-item">
                Template: <strong>{usedTemplate}</strong>
              </span>
            )}
            <span className="meta-item">
              Visual: <strong>{visualType}</strong>
            </span>
            <span className="meta-item">
              Complexity: <strong>{complexity}</strong>
            </span>
          </div>

          {/* ── Quality report ── */}
          {qualityReport && (
            <div className="quality-report">
              <div className="quality-header">
                <span className="quality-score">{scoreLabel}</span>
                <span
                  className={`status-badge ${
                    passed ? "status-complete" : "status-pending"
                  }`}
                >
                  {passed ? "Passed" : "Needs review"}
                </span>
                {revisions !== null && (
                  <span className="meta-item revisions">
                    Revisions: {revisions} (max 3)
                  </span>
                )}
              </div>

              {renderList("Issues", qualityReport.issues)}
              {renderList("Warnings", qualityReport.warnings)}
              {renderList("Suggestions", qualityReport.suggestions)}
            </div>
          )}

          {/* ── Regenerate ── */}
          <div className="regenerate-row">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onRegenerate}
              disabled={regenerateDisabled}
            >
              ↻ Regenerate
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Empty placeholder ──────────────────────────────────────────────────
  return (
    <div className="result-area">
      <div className="result-placeholder">
        <div className="result-icon">🖼️</div>
        <p className="result-text">Your generated visual will appear here.</p>
      </div>
    </div>
  );
}
