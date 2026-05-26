import { parseContextBlocks } from '../../lib/markdown';
import CodeBlock from './CodeBlock';
import MarkdownText from './MarkdownText';

function QuestionContext({ context }: { context?: string | null }) {
  if (typeof context !== 'string' || !context.trim()) {
    return null;
  }
  const blocks = parseContextBlocks(context, { detectCode: true });

  return (
    <section className="question-context" aria-label="Question context">
      <h3>Context</h3>
      <div className="context-blocks">
        {blocks.map((block, index) =>
          block.type === 'code' ? (
            <CodeBlock key={`${block.type}-${index}`} language={block.language} code={block.content} />
          ) : (
            <MarkdownText key={`${block.type}-${index}`} text={block.content} />
          ),
        )}
      </div>
    </section>
  );
}

export default QuestionContext;

