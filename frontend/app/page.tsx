/**
 * AI Visual Generator — Main Page
 *
 * Combines the Header, PromptArea, VisualTypeSelector, ComplexitySelector,
 * GenerateButton, and ResultArea into a single-page generation interface.
 *
 * Phase 1: The Generate button shows a loading state and then displays a
 * placeholder.  Real image generation is deferred to later phases.
 */

"use client";

import { useState, useEffect } from "react";

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

  // ── UI state ──────────────────────────────────────────────────────────
  const [isGenerating, setIsGenerating] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [message, setMessage] = useState("");

  // ── Health check on mount ─────────────────────────────────────────────
  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch("/api/health");
        if (res.ok) {
          setMessage("Backend connected ✅");
        } else {
          setMessage("Backend unreachable ⚠️");
        }
      } catch {
        setMessage("Backend not connected — running in standalone mode");
      }
    }
    checkHealth();
  }, []);

  // ── Generate handler ──────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setMessage("Please enter a prompt first.");
      return;
    }

    setIsGenerating(true);
    setMessage("Preparing generation workflow...");

    // Phase 1: simulate a brief loading state, then show placeholder.
    await new Promise((resolve) => setTimeout(resolve, 1500));

    setMessage(
      "Image generation is not yet implemented in Phase 1. " +
        "This result area will display generated images in a future phase."
    );
    setImageUrl(null);
    setIsGenerating(false);
  };

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
              {message && <p className="status-message">{message}</p>}
            </div>
          </section>

          {/* ── Result Section ───────────────────────────────────────── */}
          <section className="result-section">
            <h2 className="section-title">Result</h2>
            <ResultArea
              imageUrl={imageUrl}
              loading={isGenerating}
              message={message}
            />
          </section>
        </div>
      </main>
    </div>
  );
}
