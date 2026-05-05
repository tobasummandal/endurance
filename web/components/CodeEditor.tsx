'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';

const Monaco = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div style={{ padding: '1rem', color: 'var(--dim)', fontFamily: 'var(--mono)' }}>
      loading editor…
    </div>
  ),
});

type Props = {
  value: string;
  onChange?: (next: string) => void;
  readOnly?: boolean;
  height?: string | number;
  highlightLines?: number[];
};

// Helios theme — dark amber, JetBrains Mono. Defined inline so monaco picks it up.
const HELIOS_THEME = {
  base: 'vs-dark' as const,
  inherit: true,
  rules: [
    { token: 'comment', foreground: '6e7787', fontStyle: 'italic' },
    { token: 'keyword', foreground: 'E8A33D' },
    { token: 'string', foreground: '7FE0E0' },
    { token: 'number', foreground: 'f4c46b' },
    { token: 'identifier', foreground: 'f3ece0' },
    { token: 'type', foreground: 'f4c46b' },
  ],
  colors: {
    'editor.background': '#0c1118',
    'editor.foreground': '#f3ece0',
    'editor.lineHighlightBackground': '#0f1620',
    'editorLineNumber.foreground': '#3a4252',
    'editorLineNumber.activeForeground': '#E8A33D',
    'editor.selectionBackground': '#1a2230',
    'editorCursor.foreground': '#E8A33D',
    'editorIndentGuide.background': '#1a2230',
    'editor.findMatchHighlightBackground': '#E8A33D33',
  },
};

export default function CodeEditor({
  value,
  onChange,
  readOnly = false,
  height = 460,
  highlightLines = [],
}: Props) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!mounted) {
    return (
      <div className="code-surface" style={{ minHeight: height, padding: '1rem', color: 'var(--dim)' }}>
        loading editor…
      </div>
    );
  }

  return (
    <div className="code-surface" style={{ overflow: 'hidden' }}>
      <Monaco
        height={height}
        defaultLanguage="python"
        value={value}
        onChange={(v) => onChange?.(v ?? '')}
        beforeMount={(monaco) => {
          monaco.editor.defineTheme('helios', HELIOS_THEME);
        }}
        onMount={(editor, monaco) => {
          monaco.editor.setTheme('helios');
          if (highlightLines.length) {
            editor.deltaDecorations(
              [],
              highlightLines.map((ln) => ({
                range: new monaco.Range(ln, 1, ln, 1),
                options: {
                  isWholeLine: true,
                  className: 'helios-bug-line',
                  glyphMarginClassName: 'helios-bug-glyph',
                },
              })),
            );
          }
        }}
        options={{
          readOnly,
          fontFamily: 'JetBrains Mono, ui-monospace, monospace',
          fontSize: 13,
          lineHeight: 22,
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          padding: { top: 16, bottom: 16 },
          smoothScrolling: true,
          renderLineHighlight: 'line',
          fontLigatures: true,
        }}
      />
    </div>
  );
}
