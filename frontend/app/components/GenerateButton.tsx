/**
 * GenerateButton component — primary call-to-action.
 */

interface GenerateButtonProps {
  onClick: () => void;
  disabled?: boolean;
  loading?: boolean;
}

export default function GenerateButton({
  onClick,
  disabled = false,
  loading = false,
}: GenerateButtonProps) {
  return (
    <button
      type="button"
      className={`btn btn-primary ${loading ? "btn-loading" : ""}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading ? (
        <span className="btn-content">
          <span className="spinner" />
          Generating...
        </span>
      ) : (
        "Generate Visual"
      )}
    </button>
  );
}
