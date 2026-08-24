/**
 * Header component — displays the application title and subtitle.
 */

export default function Header() {
  return (
    <header className="header">
      <div className="container">
        <h1 className="header-title">AI Visual Generator</h1>
        <p className="header-subtitle">
          Generate infographic images and complex technical visuals using an
          agentic AI workflow.
        </p>
      </div>
    </header>
  );
}
