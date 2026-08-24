/**
 * VisualTypeSelector component — lets the user choose between
 * Auto, Infographic, and Complexity Image.
 */

export type VisualType = "auto" | "infographic" | "complexity_image";

export interface VisualTypeOption {
  value: VisualType;
  label: string;
  description: string;
  icon: string;
}

export const VISUAL_TYPE_OPTIONS: VisualTypeOption[] = [
  {
    value: "auto",
    label: "Auto",
    description: "Let the AI decide the best visual type",
    icon: "🤖",
  },
  {
    value: "infographic",
    label: "Infographic",
    description: "Data-driven visual with text, charts, and icons",
    icon: "📊",
  },
  {
    value: "complexity_image",
    label: "Complexity Image",
    description: "Complex technical visual with diagrams and abstract elements",
    icon: "🧩",
  },
];

interface VisualTypeSelectorProps {
  value: VisualType;
  onChange: (value: VisualType) => void;
  disabled?: boolean;
}

export default function VisualTypeSelector({
  value,
  onChange,
  disabled = false,
}: VisualTypeSelectorProps) {
  return (
    <div className="form-group">
      <label className="form-label">Visual Type</label>
      <div className="segmented-control">
        {VISUAL_TYPE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`segment ${value === option.value ? "segment-active" : ""}`}
            onClick={() => !disabled && onChange(option.value)}
            disabled={disabled}
            title={option.description}
          >
            <span className="segment-icon">{option.icon}</span>
            <span className="segment-label">{option.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
