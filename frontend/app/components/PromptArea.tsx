/**
 * PromptArea component — large text input for the user's visual description.
 */

import { useState, useEffect } from "react";

interface PromptAreaProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  maxLength?: number;
}

export default function PromptArea({
  value,
  onChange,
  disabled = false,
  maxLength = 5000,
}: PromptAreaProps) {
  const [charCount, setCharCount] = useState(value.length);

  useEffect(() => {
    setCharCount(value.length);
  }, [value]);

  return (
    <div className="form-group">
      <label htmlFor="prompt" className="form-label">
        What would you like to generate?
      </label>
      <textarea
        id="prompt"
        className="prompt-input"
        placeholder="Describe the visual you want to generate — e.g. 'Create an infographic about the benefits of solar energy for residential homeowners.'"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        maxLength={maxLength}
        rows={6}
      />
      <div className="char-count">
        <span
          className={
            charCount > maxLength * 0.9 ? "char-count-warning" : undefined
          }
        >
          {charCount}
        </span>
        {" / " + maxLength}
      </div>
    </div>
  );
}
