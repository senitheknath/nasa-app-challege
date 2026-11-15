import { Fragment } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { colors, radius, size, space } from '@/theme/tokens';
import { typography } from '@/theme/typography';

type Block =
  | { type: 'heading'; level: 1 | 2 | 3; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; ordered: boolean; items: string[] }
  | { type: 'code'; code: string }
  | { type: 'table'; headers: string[]; rows: string[][] };

function isTableSeparator(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.includes('|')) return false;
  const cells = trimmed
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|');
  return cells.length >= 1 && cells.every((cell) => /^:?-{2,}:?$/.test(cell.trim()));
}

function parseTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

function parseMarkdown(source: string): Block[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // Fenced code block
    if (trimmed.startsWith('```')) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      blocks.push({ type: 'code', code: codeLines.join('\n') });
      continue;
    }

    // Markdown table
    if (trimmed.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = parseTableRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim() !== '') {
        rows.push(parseTableRow(lines[i]));
        i++;
      }
      blocks.push({ type: 'table', headers, rows });
      continue;
    }

    // Headings
    const headingMatch = /^(#{1,3})\s+(.+)$/.exec(trimmed);
    if (headingMatch) {
      const level = headingMatch[1].length as 1 | 2 | 3;
      blocks.push({ type: 'heading', level, text: headingMatch[2] });
      i++;
      continue;
    }

    // Bullet list
    if (/^[-*•]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*•]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*•]\s+/, ''));
        i++;
      }
      blocks.push({ type: 'list', ordered: false, items });
      continue;
    }

    // Ordered list
    if (/^\d+[.)]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+[.)]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+[.)]\s+/, ''));
        i++;
      }
      blocks.push({ type: 'list', ordered: true, items });
      continue;
    }

    // Paragraph (collect contiguous non-special lines)
    const paraLines: string[] = [trimmed];
    i++;
    while (i < lines.length) {
      const next = lines[i].trim();
      if (
        !next ||
        next.startsWith('```') ||
        /^#{1,3}\s+/.test(next) ||
        /^[-*•]\s+/.test(next) ||
        /^\d+[.)]\s+/.test(next) ||
        (next.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
      ) {
        break;
      }
      paraLines.push(next);
      i++;
    }
    blocks.push({ type: 'paragraph', text: paraLines.join(' ') });
  }

  return blocks;
}

function InlineText({ text, baseStyle }: { text: string; baseStyle?: object }) {
  // Tokenize **bold**, *italic*, and `code`
  const tokens = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g).filter(Boolean);
  return (
    <Text style={[styles.bodyText, baseStyle]}>
      {tokens.map((token, idx) => {
        if (token.startsWith('**') && token.endsWith('**') && token.length > 4) {
          return (
            <Text key={idx} style={styles.bold}>
              {token.slice(2, -2)}
            </Text>
          );
        }
        if (token.startsWith('*') && token.endsWith('*') && token.length > 2) {
          return (
            <Text key={idx} style={styles.italic}>
              {token.slice(1, -1)}
            </Text>
          );
        }
        if (token.startsWith('`') && token.endsWith('`') && token.length > 2) {
          return (
            <Text key={idx} style={styles.inlineCode}>
              {token.slice(1, -1)}
            </Text>
          );
        }
        return <Fragment key={idx}>{token}</Fragment>;
      })}
    </Text>
  );
}

export function MarkdownContent({ content }: { content: string }) {
  const blocks = parseMarkdown(content);

  return (
    <View style={styles.container}>
      {blocks.map((block, index) => {
        if (block.type === 'heading') {
          const style =
            block.level === 1
              ? styles.h1
              : block.level === 2
                ? styles.h2
                : styles.h3;
          return <InlineText key={index} text={block.text} baseStyle={style} />;
        }

        if (block.type === 'paragraph') {
          return <InlineText key={index} text={block.text} />;
        }

        if (block.type === 'list') {
          return (
            <View key={index} style={styles.list}>
              {block.items.map((item, idx) => (
                <View key={idx} style={styles.listRow}>
                  <Text style={styles.bullet}>
                    {block.ordered ? `${idx + 1}.` : '•'}
                  </Text>
                  <View style={styles.listTextWrap}>
                    <InlineText text={item} />
                  </View>
                </View>
              ))}
            </View>
          );
        }

        if (block.type === 'code') {
          return (
            <ScrollView
              key={index}
              horizontal
              showsHorizontalScrollIndicator={false}
              style={styles.codeBlock}
            >
              <Text style={styles.codeText}>{block.code}</Text>
            </ScrollView>
          );
        }

        if (block.type === 'table') {
          const colCount = Math.max(
            block.headers.length,
            ...block.rows.map((r) => r.length),
          );
          const colWidth = colCount <= 2 ? 150 : colCount === 3 ? 130 : 118;
          return (
            <ScrollView
              key={index}
              horizontal
              showsHorizontalScrollIndicator
              style={styles.tableScroll}
              contentContainerStyle={styles.tableWrap}
            >
              <View style={styles.table}>
                <View style={[styles.tableRow, styles.tableHeaderRow]}>
                  {Array.from({ length: colCount }).map((_, cIdx) => (
                    <View key={cIdx} style={[styles.tableCell, { width: colWidth }]}>
                      <InlineText
                        text={block.headers[cIdx] ?? ''}
                        baseStyle={styles.tableHeaderText}
                      />
                    </View>
                  ))}
                </View>
                {block.rows.map((row, rIdx) => (
                  <View
                    key={rIdx}
                    style={[
                      styles.tableRow,
                      rIdx % 2 === 1 && styles.tableRowAlt,
                    ]}
                  >
                    {Array.from({ length: colCount }).map((_, cIdx) => (
                      <View key={cIdx} style={[styles.tableCell, { width: colWidth }]}>
                        <InlineText
                          text={row[cIdx] ?? '–'}
                          baseStyle={styles.tableCellText}
                        />
                      </View>
                    ))}
                  </View>
                ))}
              </View>
            </ScrollView>
          );
        }

        return null;
      })}
    </View>
  );
}

const monoFont = Platform.select({
  ios: 'Menlo',
  android: 'monospace',
  default: 'monospace',
});

const styles = StyleSheet.create({
  container: { gap: space.sm },
  bodyText: {
    ...typography.caption,
    color: colors.cream,
    lineHeight: 21,
  },
  bold: {
    fontWeight: '700',
    color: colors.cream,
  },
  italic: {
    fontStyle: 'italic',
    color: colors.secondary,
  },
  inlineCode: {
    fontFamily: monoFont,
    fontSize: 12,
    color: colors.accent,
    backgroundColor: colors.innerDark,
    paddingHorizontal: space.xs,
    borderRadius: 4,
  },
  h1: {
    ...typography.title,
    color: colors.accent,
    marginTop: space.xs,
  },
  h2: {
    ...typography.action,
    color: colors.cream,
    marginTop: space.xs,
  },
  h3: {
    ...typography.smallBold,
    color: colors.sage,
    marginTop: space.xs,
  },
  list: { gap: space.xs },
  listRow: { flexDirection: 'row', alignItems: 'flex-start', gap: space.sm },
  bullet: {
    ...typography.caption,
    color: colors.accent,
    fontWeight: '700',
    minWidth: 16,
  },
  listTextWrap: { flex: 1, minWidth: 0 },
  codeBlock: {
    backgroundColor: colors.innerDark,
    borderRadius: radius.tile / 2,
    borderWidth: size.hairline,
    borderColor: colors.border,
    padding: space.md,
  },
  codeText: {
    fontFamily: monoFont,
    fontSize: 12,
    lineHeight: 18,
    color: colors.cream,
  },
  tableScroll: {
    borderRadius: radius.tile / 2,
    borderWidth: size.hairline,
    borderColor: colors.glassBorder,
    backgroundColor: colors.innerDark,
  },
  tableWrap: { flexGrow: 1 },
  table: { minWidth: '100%' },
  tableRow: {
    flexDirection: 'row',
    borderBottomWidth: size.hairline,
    borderBottomColor: colors.border,
  },
  tableHeaderRow: {
    backgroundColor: colors.forest800,
    borderBottomColor: colors.accentBorder,
  },
  tableRowAlt: {
    backgroundColor: 'rgba(255,255,255,0.03)',
  },
  tableCell: {
    paddingHorizontal: space.sm,
    paddingVertical: space.sm,
    borderRightWidth: size.hairline,
    borderRightColor: colors.border,
  },
  tableHeaderText: {
    ...typography.label,
    color: colors.accent,
    fontWeight: '700',
  },
  tableCellText: {
    ...typography.label,
    color: colors.cream,
    lineHeight: 17,
  },
});
