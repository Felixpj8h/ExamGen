import { formatDisplayText } from '../../lib/textFormatting';
import { parseContextBlocks } from '../../lib/markdown';
import CodeBlock from './CodeBlock';

export function RichTextBlocks({ text, className = '', detectCode = false }) {
  if (typeof text !== 'string' || !text.trim()) {
    return null;
  }
  const blocks = parseContextBlocks(text, { detectCode });
  return (
    <div className={`rich-text-blocks ${className}`}>
      {blocks.map((block, index) =>
        block.type === 'code' ? (
          <CodeBlock key={`${block.type}-${index}`} language={block.language} code={block.content} />
        ) : (
          <MarkdownText key={`${block.type}-${index}`} text={block.content} />
        ),
      )}
    </div>
  );
}

function MarkdownText({ text }) {
  const lines = String(text || '')
    .split('\n')
    .map((line) => line.trimEnd());
  const elements = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();
    if (!line) {
      index += 1;
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = Math.min(heading[1].length + 3, 6);
      const HeadingTag = `h${level}`;
      elements.push(
        <HeadingTag key={`heading-${index}`} className="markdown-heading">
          {renderInlineMarkdown(heading[2])}
        </HeadingTag>,
      );
      index += 1;
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^[-*]\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^[-*]\s+/, ''));
        index += 1;
      }
      elements.push(
        <ul key={`ul-${index}`} className="markdown-list">
          {items.map((item, itemIndex) => (
            <li key={`${itemIndex}-${item}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index].trim())) {
        items.push(lines[index].trim().replace(/^\d+\.\s+/, ''));
        index += 1;
      }
      elements.push(
        <ol key={`ol-${index}`} className="markdown-list markdown-list-ordered">
          {items.map((item, itemIndex) => (
            <li key={`${itemIndex}-${item}`}>{renderInlineMarkdown(item)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    if (isMarkdownTableStart(lines, index)) {
      const tableLines = [];
      while (index < lines.length && looksLikeMarkdownTableRow(lines[index])) {
        tableLines.push(lines[index].trim());
        index += 1;
      }
      elements.push(<MarkdownTable key={`table-${index}`} lines={tableLines} />);
      continue;
    }

    const paragraphLines = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^(#{1,4})\s+/.test(lines[index].trim()) &&
      !/^[-*]\s+/.test(lines[index].trim()) &&
      !/^\d+\.\s+/.test(lines[index].trim()) &&
      !isMarkdownTableStart(lines, index)
    ) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    elements.push(
      <p key={`p-${index}`}>
        {paragraphLines.map((paragraphLine, lineIndex) => (
          <span key={`${lineIndex}-${paragraphLine}`}>
            {lineIndex > 0 && <br />}
            {renderInlineMarkdown(paragraphLine)}
          </span>
        ))}
      </p>,
    );
  }

  return <div className="markdown-text">{elements}</div>;
}

function MarkdownTable({ lines }) {
  const rows = lines
    .filter((line, index) => index !== 1 || !looksLikeMarkdownTableDivider(line))
    .map(parseMarkdownTableRow)
    .filter((cells) => cells.length > 0);

  if (rows.length === 0) {
    return null;
  }

  const [headers, ...bodyRows] = rows;

  return (
    <div className="markdown-table-wrap">
      <table className="markdown-table">
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th key={`${index}-${header}`}>{renderInlineMarkdown(header)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {bodyRows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {headers.map((_, cellIndex) => (
                <td key={`cell-${rowIndex}-${cellIndex}`}>
                  {renderInlineMarkdown(row[cellIndex] || '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function isMarkdownTableStart(lines, index) {
  return (
    looksLikeMarkdownTableRow(lines[index]) &&
    looksLikeMarkdownTableDivider(lines[index + 1])
  );
}

function looksLikeMarkdownTableRow(line) {
  const trimmed = String(line || '').trim();
  return trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.split('|').length >= 3;
}

function looksLikeMarkdownTableDivider(line) {
  const trimmed = String(line || '').trim();
  return looksLikeMarkdownTableRow(trimmed) && /^(\|\s*:?-{3,}:?\s*)+\|$/.test(trimmed);
}

function parseMarkdownTableRow(line) {
  return String(line || '')
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

function renderInlineMarkdown(text) {
  const formattedText = formatDisplayText(text);
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = pattern.exec(formattedText)) !== null) {
    if (match.index > lastIndex) {
      parts.push(formattedText.slice(lastIndex, match.index));
    }

    const token = match[0];
    const key = `${match.index}-${token}`;
    if (token.startsWith('`')) {
      parts.push(
        <code key={key} className="inline-code">
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith('**') || token.startsWith('__')) {
      parts.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else {
      parts.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < formattedText.length) {
    parts.push(formattedText.slice(lastIndex));
  }

  return parts;
}

export default MarkdownText;

