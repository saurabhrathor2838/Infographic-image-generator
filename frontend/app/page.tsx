/**
 * AI Visual Generator — Main Page
 *
 * Combines the Header, PromptArea, VisualTypeSelector, ComplexitySelector,
 * GenerateButton, and ResultArea into a single-page generation interface.
 *
 * Phase 3: The Generate button is connected to the backend
 * ``POST /api/generate`` endpoint.  On submit the frontend sends the prompt,
 * visual type and complexity to the API, then displays the structured plan,
 * routing decision and request status returned by the backend.
 *
 * Phase 6: When the user selects "Infographic" (or "Auto"), the request is
 * routed to the ``POST /api/plan`` endpoint, which uses the AI Planner Agent
 * to generate a ``VisualSpecification`` and renders it to SVG.  The SVG is
 * displayed directly in the ResultArea.
 *
 * Phase 7: When the user selects "Complexity Image", the request is also
 * routed to ``POST /api/plan``.  The AI Planner generates a more detailed
 * ``VisualSpecification`` based on the selected complexity level (Low/Medium/High)
 * and renders it to SVG.  The Complexity selector is preserved unchanged.
 *
 * No paid image-generation APIs are used — the LLM provider is injected via
 * FastAPI dependency injection and can be swapped for a mock
 * (``AI_PROVIDER=mock``) for local development and testing.
 */

"use client";

import { useState, useEffect } from "react";

import type { GenerationResponse, HealthResponse } from "@/types/api";

import Header from "@/components/Header";
import PromptArea from "@/components/PromptArea";
import VisualTypeSelector, {
  VisualType,
} from "@/components/VisualTypeSelector";
import ComplexitySelector, {
  Complexity,
} from "@/components/ComplexitySelector";
import GenerateButton from "@/components/GenerateButton";
import ResultArea from "@/components/ResultArea";

export default function Home() {
  // ── Form state ────────────────────────────────────────────────────────
  const [prompt, setPrompt] = useState("");
  const [visualType, setVisualType] = useState<VisualType>("auto");
  const [complexity, setComplexity] = useState<Complexity>("medium");

  // ── API / UI state ─────────────────────────────────────────────────────
  const [isGenerating, setIsGenerating] = useState(false);
  const [response, setResponse] = useState<GenerationResponse | null>(null);
  const [svgContent, setSvgContent] = useState<string | null>(null);
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

  // ── Generate handler ──────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setError("Please enter a prompt first.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setResponse(null);
    setSvgContent(null);

    // All visual types now use the AI Planner → SVG flow (Phase 7).
    // The Complexity selector controls the detail level of the generated spec.
    const endpoint = "/api/plan";

    setStatusText(
      visualType === "infographic"
        ? "AI Planner is designing your infographic…"
        : visualType === "complexity_image"
        ? "AI Planner is generating your complexity visualization…"
        : "AI Planner is designing your visual…"
    );

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          visual_type: visualType,
          complexity,
        }),
        cache: "no-store",
      });

      if (!res.ok) {
        // /api/plan returns a JSON error body on failure (422 / 502 / 503).
        const data = await res.json().catch(() => ({}));
        setError(formatError(res.status, data));
        return;
      }

      // /api/plan returns an SVG document on success (200).
      const svgText = await res.text();
      setSvgContent(svgText);
      setResponse(null);
      setStatusText("");
    } catch (err: unknown) {
      // Network error — the backend is unreachable.
      const message = err instanceof Error ? err.message : String(err);
      setError(
        `Network error — could not reach the backend. (${message})`
      );
    } finally {
      setIsGenerating(false);
    }
  };

  /** Build a friendly, human-readable error string from a failed response. */
  function formatError(status: number, data: unknown): string {
    if (status === 422) {
      // FastAPI validation error: { detail: [{ loc, msg, type }, ...] }
      if (Array.isArray((data as { detail?: unknown })?.detail)) {
        const details = (data as { detail: { msg?: string }[] }).detail
          .map((d) => d.msg || "validation error")
          .join("; ");
        return `Validation error: ${details}.`;
      }
      return "Validation error — please check your input.";
    }

    if (status === 503) {
      const api = data as { detail?: string };
      return (
        api?.detail ||
        "The AI planner is not available. Please configure an LLM provider."
      );
    }

    if (status === 502) {
      const api = data as { detail?: string };
      return (
        api?.detail ||
        "Planning failed — the AI could not produce a valid visual specification."
      );
    }

    const api = data as { message?: string; error?: string; detail?: string };
    const summary =
      api?.message ||
      api?.error ||
      api?.detail ||
      `Request failed with status ${status}`;
    return `Generation failed (${status}): ${summary}`;
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

            <div className="generate-section">
              <GenerateButton
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
                loading={isGenerating}
              />

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
            </div>
          </section>

          {/* ── Result Section ───────────────────────────────────────── */}
          <section className="result-section">
            <h2 className="section-title">Result</h2>
            <ResultArea
              imageUrl={null}
              svgContent={svgContent}
              loading={isGenerating}
              error={error}
              response={response}
              visualType={visualType}
              complexity={complexity}
            />
          </section>
        </div>
      </main>
    </div>
  );
}
