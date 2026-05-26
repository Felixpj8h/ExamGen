import {
  formatCodeForLanguage,
  highlightCode,
  normalizeCodeLanguage,
} from '../../lib/codeHighlighting';

interface CodeBlockProps {
  language?: string;
  code: string;
}

function CodeBlock({ language, code }: CodeBlockProps) {
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

