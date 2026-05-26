import {
  formatCodeForLanguage,
  highlightCode,
  normalizeCodeLanguage,
} from '../../lib/codeHighlighting';

function CodeBlock({ language, code }) {
  const normalizedLanguage = normalizeCodeLanguage(language);
  const displayCode = formatCodeForLanguage(code, normalizedLanguage);
  return (
    <div className="code-block">
      <div className="code-block-header">{normalizedLanguage}</div>
      <pre>
        <code>{highlightCode(displayCode, normalizedLanguage)}</code>
      </pre>
    </div>
  );
}

export default CodeBlock;

