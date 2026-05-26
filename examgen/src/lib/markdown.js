import {
  formatDetectedCode,
  inferCodeLanguage,
  looksLikeCode,
  normalizeCodeWhitespace,
} from './codeHighlighting';

export function parseContextBlocks(context, options = {}) {
  const blocks = [];
  const fencePattern = /```([A-Za-z0-9_-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = fencePattern.exec(context)) !== null) {
    pushTextBlocks(blocks, context.slice(lastIndex, match.index));
    blocks.push({
      type: 'code',
      language: match[1] || 'text',
      content: normalizeCodeWhitespace(match[2]),
    });
    lastIndex = fencePattern.lastIndex;
  }

  pushTextBlocks(blocks, context.slice(lastIndex));
  if (blocks.length === 0) {
    pushTextBlocks(blocks, context);
  }
  return options.detectCode ? applyCodeDetection(blocks) : blocks;
}

function pushTextBlocks(blocks, text) {
  const paragraphs = String(text || '')
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
  paragraphs.forEach((paragraph) => blocks.push({ type: 'text', content: paragraph }));
}

function applyCodeDetection(blocks) {
  const detectedBlocks = blocks.map((block) => {
    if (block.type !== 'text' || !looksLikeCode(block.content)) {
      return block;
    }
    const language = inferCodeLanguage(block.content);
    return {
      type: 'code',
      language,
      content: normalizeCodeWhitespace(formatDetectedCode(block.content, language)),
    };
  });
  return mergeAdjacentCodeBlocks(detectedBlocks);
}

function mergeAdjacentCodeBlocks(blocks) {
  return blocks.reduce((merged, block) => {
    const previous = merged[merged.length - 1];
    if (
      previous?.type === 'code' &&
      block.type === 'code' &&
      previous.language === block.language
    ) {
      previous.content = `${previous.content}\n\n${block.content}`;
      return merged;
    }
    merged.push({ ...block });
    return merged;
  }, []);
}

