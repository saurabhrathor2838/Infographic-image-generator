/**
 * API contract types for the AI Visual Generator backend.
 *
 * These mirror the Pydantic response schemas returned by the FastAPI
 * endpoints ``GET /api/health`` and ``POST /api/generate``.  Keeping them in
 * one place gives the frontend a single source of truth for the response
 * shape returned by the backend.
 *
 * The ``POST /api/plan`` endpoint (Phase 6) returns an SVG document
 * (``image/svg+xml``) on success, or a JSON error body on failure — see
 * ``ApiErrorResponse`` for the error shape.
 */

/** Lifecycle status of a generation request (mirrors the backend enum). */
export type GenerationStatus =
  | "pending"
  | "planning"
  | "generating"
  | "critiquing"
  | "revising"
  | "complete"
  | "failed";

/**
 * The ``result`` payload embedded inside a generation response.
 *
 * ``mock`` is ``true`` while image generation is simulated (Phase 2/3) and
 * will become ``false`` once real providers are wired up (Phase 4+).
 */
export interface GenerationResultData {
  visual_type: string;
  complexity: string;
  routing: string;
  plan: Record<string, unknown> | null;
  iterations: number;
  final_image: unknown | null;
  mock: boolean;
  created_at: string | null;
  updated_at: string | null;
}

/** Shape of the body returned by ``POST /api/generate``. */
export interface GenerationResponse {
  success: boolean;
  timestamp: string;
  request_id: string;
  status: GenerationStatus;
  visual_type: string;
  message: string;
  result: GenerationResultData | null;
}

/** Shape of the body returned by ``GET /api/health``. */
export interface HealthResponse {
  success: boolean;
  timestamp: string;
  status: string;
  service: string;
}

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
  detail?: ApiValidationError[];
}
