export function normalizeCodeWhitespace(code) {
  return String(code || '')
    .replace(/^\s*\n/, '')
    .replace(/\n\s*$/, '');
}

export function formatCodeForLanguage(code, language) {
  const normalizedCode = normalizeCodeWhitespace(code);
  if (language === 'haskell') {
    return repairFlattenedHaskellIndentation(normalizedCode);
  }
  return normalizedCode;
}

export function normalizeCodeLanguage(language) {
  const normalized = String(language || 'text').trim().toLowerCase();
  if (['hs', 'haskell'].includes(normalized)) {
    return 'haskell';
  }
  if (['py', 'python'].includes(normalized)) {
    return 'python';
  }
  if (['js', 'javascript', 'jsx'].includes(normalized)) {
    return 'javascript';
  }
  if (['ts', 'typescript', 'tsx'].includes(normalized)) {
    return 'typescript';
  }
  if (['rs', 'rust'].includes(normalized)) {
    return 'rust';
  }
  if (['java'].includes(normalized)) {
    return 'java';
  }
  if (['kt', 'kotlin'].includes(normalized)) {
    return 'kotlin';
  }
  return normalized || 'text';
}

export function highlightCode(code, language) {
  const syntax = getSyntaxConfig(language);
  if (!syntax) {
    return code;
  }

  const tokenPattern = syntax.pattern;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = tokenPattern.exec(code)) !== null) {
    if (match.index > lastIndex) {
      parts.push(code.slice(lastIndex, match.index));
    }
    const token = match[0];
    parts.push(
      <span key={`${match.index}-${token}`} className={`syntax-${classifyToken(token, syntax)}`}>
        {token}
      </span>,
    );
    lastIndex = tokenPattern.lastIndex;
  }

  if (lastIndex < code.length) {
    parts.push(code.slice(lastIndex));
  }
  return parts;
}

export function looksLikeCode(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed || trimmed.length < 12) {
    return false;
  }
  if (looksLikePseudoInterfaceCode(trimmed)) {
    return true;
  }
  const codeSignals = [
    /\b(public|private|protected|static|class|interface|enum|record|void|int|boolean|String|Map|List|HashMap|new|return|var|fun|val|let|const|function|fn|mut|use|impl|match|struct|enum)\b/,
    /\b(type|data|case|of)\b/,
    /\bprintln!\s*\(|\bvec!\s*\[|String::from|::/,
    /[{};]/,
    /\w+\s*\([^)]*\)\s*\{/,
    /<\s*\w+\s*,\s*\w+\s*>/,
    /\b(if|else|for|while|switch)\s*\(/,
    /=>|->|::/,
  ];
  const signalCount = codeSignals.filter((pattern) => pattern.test(trimmed)).length;
  const proseWords = trimmed.split(/\s+/).filter((word) => /^[A-ZÆØÅa-zæøå]{4,}$/.test(word)).length;
  return signalCount >= 2 && proseWords < 18;
}

export function inferCodeLanguage(text) {
  const trimmed = String(text || '');
  if (looksLikePseudoInterfaceCode(trimmed)) {
    return 'pseudocode';
  }
  if (/\b(fn|let|mut|use|impl|match|struct|enum|trait)\b|println!\s*\(|vec!\s*\[|String::from|&mut\b/.test(trimmed)) {
    return 'rust';
  }
  if (/\b(module|where|data\s+\w+|deriving|case\b.*\bof\b|Maybe\s+Int|Either\s+String\s+Int|::)\b/.test(trimmed)) {
    return 'haskell';
  }
  if (/\b(public|private|protected|static|class|interface|enum|record|void|int|boolean|String|HashMap|implements|extends)\b/.test(trimmed)) {
    return 'java';
  }
  if (/\b(fun|val|var|data class|object)\b/.test(trimmed)) {
    return 'kotlin';
  }
  if (/\b(function|const|let|=>|console\.)\b/.test(trimmed)) {
    return 'javascript';
  }
  return 'text';
}

export function formatDetectedCode(text, language = inferCodeLanguage(text)) {
  const trimmed = String(text || '').trim();
  if (language === 'pseudocode') {
    return formatPseudoInterfaceCode(trimmed);
  }
  if (language === 'haskell') {
    return formatFlattenedHaskellCode(trimmed);
  }
  if (trimmed.includes('\n')) {
    return trimmed;
  }
  if (!/[{};]/.test(trimmed)) {
    return trimmed;
  }
  return trimmed
    .replace(/\{\s*/g, '{\n  ')
    .replace(/;\s*/g, ';\n  ')
    .replace(/\s*\}\s*/g, '\n}\n')
    .split('\n')
    .map((line) => line.trimEnd())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function repairFlattenedHaskellIndentation(code) {
  const lines = String(code || '').split('\n');
  if (lines.some((line) => /^ {2,}\S/.test(line))) {
    return code;
  }

  return lines
    .map((line) => {
      const trimmed = line.trimStart();
      if (!trimmed) {
        return '';
      }
      if (/^(=|\|)\s/.test(trimmed) || /^(Lit|Var|Add|Mul|Let|IfZero)\b.*->/.test(trimmed)) {
        return `  ${trimmed}`;
      }
      return trimmed;
    })
    .join('\n');
}

function looksLikePseudoInterfaceCode(text) {
  const trimmed = String(text || '').trim();
  return /\binterface\s+\w+\s*\{/.test(trimmed) && /\bmethod\s+\w+\s*\(/.test(trimmed);
}

function formatPseudoInterfaceCode(code) {
  return String(code || '')
    .replace(/\s*\{\s*/g, ' {\n')
    .replace(/\s*}\s*/g, '\n}')
    .replace(/\s*\/\/\s*/g, '\n  // ')
    .replace(/\s+(method\s+\w+\s*\()/g, '\n  $1')
    .replace(/;\s*/g, ';\n')
    .replace(/\n[ \t]*\n[ \t]*\n+/g, '\n\n')
    .split('\n')
    .map((line) => line.trimEnd())
    .join('\n')
    .trim();
}

function formatFlattenedHaskellCode(code) {
  return String(code || '')
    .replace(/\s+data\s+/g, '\ndata ')
    .replace(/data ([^=\n]+)\s+=\s+/g, 'data $1\n  = ')
    .replace(/\s+\|\s+/g, '\n  | ')
    .replace(/(Maybe Int|Either String Int)\s+(lookupEnv\b)/g, '$1\n$2')
    .replace(/(Maybe Int|Either String Int)\s+(eval\b)/g, '$1\n$2')
    .replace(/(Nothing|Just v)\s+(lookupEnv\b)/g, '$1\n$2')
    .replace(/(:rest\))\s+(\| )/g, '$1\n  $2')
    .replace(/(Just v)\s+(\| )/g, '$1\n  $2')
    .replace(/(case expr of)\s+/g, '$1\n')
    .replace(/\s+(Lit n ->)/g, '\n  $1')
    .replace(/\s+(Var x ->)/g, '\n  $1')
    .replace(/\s+(Add e1 e2 ->)/g, '\n  $1')
    .replace(/\s+(Mul e1 e2 ->)/g, '\n  $1')
    .replace(/\s+(Let x e body ->)/g, '\n  $1')
    .replace(/\s+(IfZero c t f ->)/g, '\n  $1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function getSyntaxConfig(language) {
  const commonOperatorPattern = String.raw`==|!=|<=|>=|&&|\|\||::|->|=>|[=+\-*/%<>!|&{}[\]().,;:]`;
  const configs = {
    haskell: {
      pattern: new RegExp(
        String.raw`(--.*$|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:module|where|import|qualified|as|type|data|newtype|deriving|instance|class|case|of|let|in|if|then|else|do)\b|\b(?:Integer|String|Bool|Char|Maybe|Map|IO|Eq|Show|Ord|Int|Double|Float)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(Integer|String|Bool|Char|Maybe|Map|IO|Eq|Show|Ord|Int|Double|Float)$/,
    },
    rust: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:as|async|await|break|const|continue|crate|else|enum|extern|false|fn|for|if|impl|in|let|loop|match|mod|move|mut|pub|ref|return|self|Self|static|struct|super|trait|true|type|unsafe|use|where|while)\b|\b(?:String|Vec|Option|Result|Some|None|Ok|Err|Box|usize|isize|u8|u16|u32|u64|i8|i16|i32|i64|bool|char|str)\b|\b\w+!|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(String|Vec|Option|Result|Some|None|Ok|Err|Box|usize|isize|u8|u16|u32|u64|i8|i16|i32|i64|bool|char|str)$/,
    },
    java: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:abstract|assert|boolean|break|byte|case|catch|char|class|const|continue|default|do|double|else|enum|extends|final|finally|float|for|if|implements|import|instanceof|int|interface|long|new|null|package|private|protected|public|record|return|short|static|strictfp|super|switch|synchronized|this|throw|throws|transient|try|var|void|volatile|while)\b|\b(?:String|Integer|Boolean|Character|Double|Float|Long|Short|Byte|Object|List|Map|Set|HashMap|ArrayList|Optional)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(String|Integer|Boolean|Character|Double|Float|Long|Short|Byte|Object|List|Map|Set|HashMap|ArrayList|Optional)$/,
    },
    kotlin: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:as|break|class|continue|data|do|else|false|for|fun|if|import|in|interface|is|null|object|package|return|super|this|throw|true|try|typealias|val|var|when|while)\b|\b(?:String|Int|Boolean|Char|Double|Float|Long|Short|Byte|Any|Unit|List|Map|Set|MutableList|MutableMap)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(String|Int|Boolean|Char|Double|Float|Long|Short|Byte|Any|Unit|List|Map|Set|MutableList|MutableMap)$/,
    },
    javascript: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|` + '`' + String.raw`(?:\\.|[^` + '`' + String.raw`\\])*` + '`' + String.raw`|\b(?:async|await|break|case|catch|class|const|continue|default|do|else|export|extends|finally|for|from|function|if|import|in|let|new|null|return|static|super|switch|this|throw|try|typeof|undefined|var|while|yield)\b|\b(?:Array|Boolean|Date|Map|Number|Object|Promise|Set|String)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(Array|Boolean|Date|Map|Number|Object|Promise|Set|String)$/,
    },
    typescript: {
      pattern: new RegExp(
        String.raw`(//.*$|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|` + '`' + String.raw`(?:\\.|[^` + '`' + String.raw`\\])*` + '`' + String.raw`|\b(?:abstract|any|as|async|await|boolean|break|case|catch|class|const|continue|default|do|else|enum|export|extends|false|finally|for|from|function|if|implements|import|in|interface|keyof|let|namespace|new|null|number|private|protected|public|readonly|return|static|string|super|switch|this|throw|true|try|type|typeof|undefined|var|void|while|yield)\b|\b(?:Array|Boolean|Date|Map|Number|Object|Promise|Set|String)\b|${commonOperatorPattern})`,
        'gm',
      ),
      types: /^(Array|Boolean|Date|Map|Number|Object|Promise|Set|String)$/,
    },
  };
  return configs[language] || null;
}

function classifyToken(token, syntax) {
  if (token.startsWith('--') || token.startsWith('//') || token.startsWith('/*')) {
    return 'comment';
  }
  if (token.startsWith('"') || token.startsWith("'") || token.startsWith('`')) {
    return 'string';
  }
  if (syntax.types.test(token)) {
    return 'type';
  }
  if (/^(==|!=|<=|>=|&&|\|\||::|->|=>|[=+\-*/%<>!|&{}[\]().,;:])$/.test(token)) {
    return 'operator';
  }
  return 'keyword';
}

