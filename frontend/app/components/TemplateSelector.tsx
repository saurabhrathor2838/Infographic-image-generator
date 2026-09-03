/**
 * TemplateSelector component — lets the user pick a template (or let the AI
 * auto-select one) by populating the options from ``GET /api/templates``.
 *
 * Phase 12: the list of available templates (with human-readable display names
 * and descriptions) is fetched from the backend ``/api/templates`` endpoint and
 * rendered as a <select>.  The selected value is controlled by the parent via
 * the ``value``/``onChange`` props; ``null`` means "auto-select".
 */

import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";

import type { TemplateInfo } from "@/types/api";

interface TemplateSelectorProps {
  value: string | null;
  onChange: (template: string | null) => void;
  disabled?: boolean;
}

export default function TemplateSelector({
  value,
  onChange,
  disabled = false,
}: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    fetch("/api/templates", { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error(`Templates request failed (${res.status})`);
        return res.json() as Promise<{ templates: TemplateInfo[] }>;
      })
      .then((data) => {
        if (!cancelled) {
          setTemplates(data.templates);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Could not load templates");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // value === "" maps to "auto-select" (null) for the consumer.
  const handleChange = (e: ChangeEvent<HTMLSelectElement>) => {
    const v = e.target.value;
    onChange(v === "" ? null : v);
  };

  return (
    <div className="form-group">
      <label htmlFor="template" className="form-label">
        Template
      </label>
      <select
        id="template"
        className="template-select"
        value={value ?? ""}
        onChange={handleChange}
        disabled={disabled || loading}
        title={
          loadError
            ? loadError
            : "Choose a template, or leave on Auto to let the AI decide"
        }
      >
        <option value="" disabled={loading}>
          {loading ? "Loading templates…" : "Auto (let the AI decide)"}
        </option>
        {templates.map((t) => (
          <option key={t.name} value={t.name} title={t.description}>
            {t.display_name}
          </option>
        ))}
      </select>
      {loadError && (
        <p className="form-hint hint-error">
          Templates unavailable — falling back to auto-selection.
        </p>
      )}
    </div>
  );
}
