/**
 * ComplexitySelector component — lets the user choose Low / Medium / High.
 */

export type Complexity = "low" | "medium" | "high";

export interface ComplexityOption {
  value: Complexity;
  label: string;
  description: string;
}

export const COMPLEXITY_OPTIONS: ComplexityOption[] = [
  {
    value: "low",
    label: "Low",
    description: "Simple, clean, minimal designs",
  },
  {
    value: "medium",
    label: "Medium",
    description: "Moderate detail with balanced elements",
  },
  {
    value: "high",
    label: "High",
    description: "Highly detailed, data-rich visualisations",
  },
];

interface ComplexitySelectorProps {
  value: Complexity;
  onChange: (value: Complexity) => void;
  disabled?: boolean;
}

export default function ComplexitySelector({
  value,
  onChange,
  disabled = false,
}: ComplexitySelectorProps) {
  return (
    <div className="form-group">
      <label className="form-label">Complexity</label>
      <div className="segmented-control">
        {COMPLEXITY_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`segment ${value === option.value ? "segment-active" : ""}`}
            onClick={() => !disabled && onChange(option.value)}
            disabled={disabled}
            title={option.description}
          >
            <span className="segment-label">{option.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
