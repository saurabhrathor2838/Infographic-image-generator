/**
 * RegenerateButton component — secondary call-to-action that re-runs
 * generation with the *current* inputs (prompt, visual type, complexity and
 * selected template).
 *
 * Phase 12: shown alongside a result so the user can quickly produce another
 * variation without re-entering their request.
 */

interface RegenerateButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export default function RegenerateButton({
  onClick,
  disabled = false,
  loading = false,
}: RegenerateButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn-secondary ${loading ? "btn-loading" : ""}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? (
        <span className="btn-content">
          <span className="spinner spinner-muted" />
          Regenerating…
        </span>
      ) : (
        "↻ Regenerate"
      )}
    </button>
  );
}
