/**
 * ResultArea component — placeholder for the generated image.
 *
 * In Phase 1 this displays a placeholder.  In later phases it will render
 * the actual generated image (or a gallery of revisions).
 */

interface ResultAreaProps {
  imageUrl: string | null;
  loading: boolean;
  message: string;
}

export default function ResultArea({
  imageUrl,
  loading,
  message,
}: ResultAreaProps) {
  return (
    <div className="result-area">
      {imageUrl ? (
        <img src={imageUrl} alt="Generated visual" className="result-image" />
      ) : (
        <div className="result-placeholder">
          <div className="result-icon">🖼️</div>
          <p className="result-text">
            {loading ? "Generating your visual..." : "Your generated image will appear here."}
          </p>
          {message && <p className="result-message">{message}</p>}
        </div>
      )}
    </div>
  );
}
