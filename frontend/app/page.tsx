/**
 * AI Visual Generator — Main Page
 *
 * Combines the Header, PromptArea, VisualTypeSelector, ComplexitySelector,
 * TemplateSelector, GenerateButton and ResultArea into a single-page
 * revision-based generation interface.
 *
 * Phase 12: generation is performed with ``POST /api/revisions``.  The request
 * sends the prompt, visual type, complexity **and** the selected template
 * (or ``null`` for auto-selection).  The response is a JSON
 * :interface:`RevisionResponse` containing the rendered SVG, a base64-encoded
 * PNG, a :class:`QualityReport` (score / issues / warnings / suggestions), the
 * revision count and an overall pass/fail flag.  Available templates are
 * fetched from ``GET /api/templates`` to populate the Template selector.
 *
 * All image generation is 100% Python on the backend — no AI image-generation
 * APIs are used here.
 */

"use client";

import { useState, useEffect } from "react";

import type {
  QualityReportData,
  RevisionResponse,
  HealthResponse,
} from "@/types/api";

import Header from "@/components/Header";
import PromptArea from "@/components/PromptArea";
import VisualTypeSelector, {
  VisualType,
} from "@/components/VisualTypeSelector";
import ComplexitySelector, {
  Complexity,
} from "@/components/ComplexitySelector";
import TemplateSelector from "@/components/TemplateSelector";
import GenerateButton from "@/components/GenerateButton";
import RegenerateButton from "@/components/RegenerateButton";
import ResultArea from "@/components/ResultArea";

export default function Home() {
  // ── Form state ────────────────────────────────────────────────────────
  const [prompt, setPrompt] = useState("");
  const [visualType, setVisualType] = useState<VisualType>("auto");
  const [complexity, setComplexity] = useState<Complexity>("medium");
  const [template, setTemplate] = useState<string | null>(null);

  // ── Result state (Phase 12 RevisionResponse) ─────────────────────────
  const [isGenerating, setIsGenerating] = useState(false);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [pngBase64, setPngBase64] = useState<string | null>(null);
  const [qualityReport, setQualityReport] = useState<QualityReportData | null>(
    null,
  );
  const [revisions, setRevisions] = useState<number | null>(null);
  const [passed, setPassed] = useState<boolean | null>(null);
  const [usedTemplate, setUsedTemplate] = useState<string | null>(null);

  // ── API / UI state ─────────────────────────────────────────────────────
  const [error, setError] = useState<string | null>(null);
  const [statusText, setStatusText] = useState("");
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);

  // ── Health check on mount ─────────────────────────────────────────────
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        if (res.ok) {
          const data: HealthResponse = await res.json();
          setBackendConnected(true);
          setStatusText(`Backend connected · ${data.service}`);
        } else {
          setBackendConnected(false);
          setStatusText("Backend reachable but unhealthy");
        }
      } catch {
        setBackendConnected(false);
        setStatusText("Backend not connected — running in standalone mode");
      }
    }
    checkHealth();
  }, []);

  // ── Generate handler (Phase 12: POST /api/revisions) ──────────────────
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("Please enter a prompt first.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setSvgContent(null);
    setPngBase64(null);
    setQualityReport(null);
    setRevisions(null);
    setPassed(null);
    setUsedTemplate(null);

    setStatusText(
      visualType === "infographic"
        ? "Refining your infographic…"
        : visualType === "complexity_image"
          ? "Refining your complexity visualization…"
          : "Refining your visual…",
    );

    try {
      const res = await fetch("/api/revisions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          visual_type: visualType,
          complexity,
          template,
        }),
        cache: "no-store",
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(formatError(res.status, data));
        return;
      }

      const data: RevisionResponse = await res.json();
      setSvgContent(data.svg);
      setPngBase64(data.png_base64 ?? null);
      setQualityReport(data.quality_report);
      setRevisions(data.revisions);
      setPassed(data.passed);
      setUsedTemplate(data.template);
      setStatusText("");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`Network error — could not reach the backend. (${message})`);
    } finally {
      setIsGenerating(false);
    }
  };

  // ── Regenerate: re-run with the current inputs ────────────────────────
  const handleRegenerate = () => {
    handleGenerate();
  };

  /** Build a friendly, human-readable error string from a failed response. */
  function formatError(status: number, data: unknown): string {
    const api = (data || {}) as { detail?: string | { msg?: string }[] };
    const detail = api.detail;

    if (status === 422 && Array.isArray(detail)) {
      const msgs = detail
        .map((d) => d.msg || "validation error")
        .join("; ");
      return `Validation error: ${msgs}.`;
    }

    if (typeof detail === "string" && detail) {
      return `Generation failed (${status}): ${detail}`;
    }

    return `Generation failed (${status}). Please check your input and try again.`;
  }

  return (
    <div className="page-wrapper">
      <Header />

      <main className="main-content">
        <div className="card">
          {/* ── Input Section ─────────────────────────────────────────── */}
          <section className="input-section">
            <h2 className="section-title">Create Your Visual</h2>

            <PromptArea
              value={prompt}
              onChange={setPrompt}
              disabled={isGenerating}
            />

            <VisualTypeSelector
              value={visualType}
              onChange={setVisualType}
              disabled={isGenerating}
            />

            <ComplexitySelector
              value={complexity}
              onChange={setComplexity}
              disabled={isGenerating}
            />

            <TemplateSelector
              value={template}
              onChange={setTemplate}
              disabled={isGenerating}
            />

            <div className="generate-section">
              <GenerateButton
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
                loading={isGenerating}
              />

              {/* Regenerate is shown only when a result exists. */}
              {(usedTemplate !== null || svgContent) && !isGenerating && (
                <RegenerateButton
                  onClick={handleRegenerate}
                  disabled={isGenerating || !prompt.trim()}
                  loading={isGenerating}
                />
              )}

              {/* Transient status / connectivity message */}
              {statusText && (
                <p
                  className={`status-message ${
                    backendConnected ? "positive" : "negative"
                  }`}
                >
                  {statusText}
                </p>
              )}

              {/* Persistent error message */}
              {error && (
                <p className="status-message negative error-message">
                  {error}
                </p>
              )}
            </div>
          </section>

          {/* ── Result Section ───────────────────────────────────────── */}
          <section className="result-section">
            <h2 className="section-title">Result</h2>
            <ResultArea
              svgContent={svgContent}
              pngBase64={pngBase64}
              qualityReport={qualityReport}
              revisions={revisions}
              passed={passed}
              usedTemplate={usedTemplate}
              visualType={visualType}
              complexity={complexity}
              loading={isGenerating}
              error={error}
              onRegenerate={handleRegenerate}
              regenerateDisabled={isGenerating || !prompt.trim()}
            />
          </section>
        </div>
      </main>
    </div>
  );
}
