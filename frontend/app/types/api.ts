/**
 * API contract types for the AI Visual Generator backend.
 *
 * These mirror the Pydantic response/request schemas returned by the FastAPI
 * endpoints.  Keeping them in one place gives the frontend a single source of
 * truth for the shapes exchanged with the backend.
 *
 * Phase 12 integration
 * --------------------
 * The frontend consumes three Phase 12 endpoints:
 *   - ``GET  /api/health``        → :interface:`HealthResponse`
 *   - ``GET  /api/templates``     → :interface:`TemplatesResponse`
 *   - ``POST /api/revisions``     → :interface:`RevisionResponse`
 *
 * ``POST /api/revisions`` accepts the fields of :interface:`RevisionRequest`
 * and returns a :interface:`RevisionResponse` containing the rendered SVG, a
 * base64-encoded PNG, a :class:`QualityReport`, the revision count and the
 * overall pass/fail status.  All image generation is pure-Python on the
 * backend — no paid image APIs are involved.
 */

/** A single field-level validation error from FastAPI (422 responses). */
export interface ApiValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** Shape of a generic API error response. */
export interface ApiErrorResponse {
  success?: boolean;
  error?: string;
  details?: string;
  detail?: string | ApiValidationError[];
}

/** Shape of the body returned by ``GET /api/health``. */
export interface HealthResponse {
  success: boolean;
  timestamp: string;
  status: string;
  service: string;
}

/** Metadata about a single template (from ``GET /api/templates``). */
export interface TemplateInfo {
  name: string;
  display_name: string;
  description: string;
}

/** A single visual-type or complexity option returned by ``GET /api/templates``. */
export interface OptionItem {
  value: string;
  label: string;
}

/** Shape of the body returned by ``GET /api/templates``. */
export interface TemplatesResponse {
  templates: TemplateInfo[];
  visual_types: OptionItem[];
  complexities: OptionItem[];
}

/** Serialized :class:`QualityReport` from ``POST /api/revisions``. */
export interface QualityReportData {
  passed: boolean;
  score: number;
  issues: string[];
  warnings: string[];
  suggestions: string[];
}

/** Request payload for ``POST /api/revisions``. */
export interface RevisionRequest {
  prompt: string;
  visual_type?: string;
  complexity?: string;
  template?: string | null;
}

/** Response returned by ``POST /api/revisions`` (Phase 12). */
export interface RevisionResponse {
  success: boolean;
  svg: string;
  png_base64: string | null;
  quality_report: QualityReportData;
  revisions: number;
  passed: boolean;
  template: string;
  visual_type: string;
  complexity: string;
  prompt: string;
}
