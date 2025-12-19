// Utilities for Groq Query Language Support

export const GROQ_KEYWORDS = [
  '*', 'match', 'in', 'asc', 'desc', 'order', 'score', 'boost',
  'count', 'defined', 'now', 'references', 'coalesce', 'round',
  'select', 'lower', 'upper', 'length', 'pt', 'geo'
];

export const GROQ_OPERATORS = [
  '==', '!=', '<', '>', '<=', '>=', '&&', '||', '!'
];

export const GROQ_TYPES = [
  '_type', '_id', '_rev', '_createdAt', '_updatedAt', 
  'title', 'description', 'slug', 'image', 'file', 'reference'
];

export interface CompletionItem {
  label: string;
  type: 'keyword' | 'function' | 'operator' | 'field';
  description?: string;
}

export const getGroqCompletions = (input: string): CompletionItem[] => {
  const lastWord = input.split(/[\s\[\](){},]+/).pop() || '';
  
  if (!lastWord) return [];

  const completions: CompletionItem[] = [
    ...GROQ_KEYWORDS.map(k => ({ label: k, type: 'keyword' as const })),
    ...GROQ_OPERATORS.map(o => ({ label: o, type: 'operator' as const })),
    ...GROQ_TYPES.map(t => ({ label: t, type: 'field' as const }))
  ];

  return completions.filter(item => 
    item.label.toLowerCase().startsWith(lastWord.toLowerCase())
  );
};

export const validateGroqQuery = (query: string): string | null => {
  if (!query) return null;

  // Basic validation
  const openBrackets = (query.match(/\[/g) || []).length;
  const closeBrackets = (query.match(/\]/g) || []).length;
  if (openBrackets !== closeBrackets) return "Unbalanced brackets []";

  const openParens = (query.match(/\(/g) || []).length;
  const closeParens = (query.match(/\)/g) || []).length;
  if (openParens !== closeParens) return "Unbalanced parentheses ()";

  const openBraces = (query.match(/\{/g) || []).length;
  const closeBraces = (query.match(/\}/g) || []).length;
  if (openBraces !== closeBraces) return "Unbalanced braces {}";
  
  // Check for common syntax errors
  if (query.includes('==') && !query.includes(' ')) {
      // Very rough heuristic, just a placeholder for more complex checks
  }

  return null;
};

export const highlightGroqSyntax = (text: string): React.ReactNode[] => {
  if (!text) return [];

  // Simple tokenizer
  // Split by whitespace but keep delimiters
  // This is a simplified highlighter for demo purposes
  const tokens = text.split(/(\s+|[\[\](){},]|\*|==|!=|&&|\|\|)/g);
  
  return tokens.map((token, index) => {
    let className = "text-white";
    
    if (GROQ_KEYWORDS.includes(token)) {
      className = "text-purple-400 font-bold";
    } else if (GROQ_OPERATORS.includes(token)) {
      className = "text-pink-400";
    } else if (GROQ_TYPES.includes(token)) {
      className = "text-blue-400";
    } else if (token.startsWith('"') || token.startsWith("'")) {
      className = "text-green-300";
    } else if (!isNaN(Number(token)) && token.trim() !== '') {
      className = "text-orange-300";
    } else if (token === '[' || token === ']' || token === '{' || token === '}') {
        className = "text-yellow-400";
    }

    return (
      <span key={index} className={className}>
        {token}
      </span>
    );
  });
};
