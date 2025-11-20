import DOMPurify from 'isomorphic-dompurify';

/**
 * Parse markdown to HTML with XSS protection
 * Supports: bold, italic, headers, links, lists, code blocks, tables
 * All output is sanitized with DOMPurify to prevent XSS attacks
 */
export const parseMarkdownToHTML = (text) => {
  if (!text) return '';

  // Escape HTML to prevent XSS
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Parse markdown tables first (before other replacements)
  html = parseMarkdownTables(html);

  // Code blocks: ```code``` or `code`
  html = html.replace(/```(.+?)```/gs, '<pre><code>$1</code></pre>');
  html = html.replace(/`(.+?)`/g, '<code>$1</code>');

  // Bold: **text** or __text__
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Italic: *text* or _text_ (but not in middle of words)
  html = html.replace(/\*([^\*]+?)\*/g, '<em>$1</em>');
  html = html.replace(/\b_([^_]+?)_\b/g, '<em>$1</em>');

  // Headers: # Heading
  html = html.replace(/^#### (.+)$/gm, '<h5>$1</h5>');
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');

  // Links: [text](url)
  html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Lists
  html = parseMarkdownLists(html);

  // Paragraphs: double line breaks (but skip tables, headers, lists, code)
  html = html.split('\n\n').map(para => {
    const trimmed = para.trim();
    if (trimmed &&
        !trimmed.startsWith('<h') &&
        !trimmed.startsWith('<ul') &&
        !trimmed.startsWith('<ol') &&
        !trimmed.startsWith('<li') &&
        !trimmed.startsWith('<table') &&
        !trimmed.startsWith('<pre') &&
        !trimmed.startsWith('<code')) {
      return `<p>${para.replace(/\n/g, '<br>')}</p>`;
    }
    return para;
  }).join('\n\n');

  // Sanitize HTML to prevent XSS attacks
  // DOMPurify removes any malicious code while preserving safe HTML
  const sanitizedHTML = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li', 'a', 'code', 'pre', 'table', 'thead', 'tbody',
      'tr', 'th', 'td', 'blockquote', 'hr'
    ],
    ALLOWED_ATTR: ['href', 'target', 'rel', 'class'],
    ALLOW_DATA_ATTR: false,
  });

  return sanitizedHTML;
};

const parseMarkdownLists = (text) => {
  const lines = text.split('\n');
  let inList = false;
  let listType = null;
  const processedLines = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const unorderedMatch = line.match(/^[\*\-] (.+)$/);
    const orderedMatch = line.match(/^\d+\. (.+)$/);

    if (unorderedMatch) {
      if (!inList || listType !== 'ul') {
        if (inList) processedLines.push(`</${listType}>`);
        processedLines.push('<ul>');
        inList = true;
        listType = 'ul';
      }
      processedLines.push(`<li>${unorderedMatch[1]}</li>`);
    } else if (orderedMatch) {
      if (!inList || listType !== 'ol') {
        if (inList) processedLines.push(`</${listType}>`);
        processedLines.push('<ol>');
        inList = true;
        listType = 'ol';
      }
      processedLines.push(`<li>${orderedMatch[1]}</li>`);
    } else {
      if (inList) {
        processedLines.push(`</${listType}>`);
        inList = false;
        listType = null;
      }
      processedLines.push(line);
    }
  }
  if (inList) processedLines.push(`</${listType}>`);
  return processedLines.join('\n');
};

const parseMarkdownTables = (text) => {
  const lines = text.split('\n');
  const result = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Check if this line looks like a table header
    if (line.includes('|') && i + 1 < lines.length) {
      const nextLine = lines[i + 1];

      // Check if next line is a separator (|---|---|)
      if (nextLine.match(/^\|?[\s\-:|]+\|[\s\-:|]+/)) {
        // This is a table!
        const tableLines = [line, nextLine];
        let j = i + 2;

        // Collect all table rows
        while (j < lines.length && lines[j].includes('|')) {
          tableLines.push(lines[j]);
          j++;
        }

        // Parse and convert table
        result.push(convertMarkdownTableToHTML(tableLines));
        i = j;
        continue;
      }
    }

    result.push(line);
    i++;
  }

  return result.join('\n');
};

const convertMarkdownTableToHTML = (tableLines) => {
  if (tableLines.length < 2) return tableLines.join('\n');

  const headerLine = tableLines[0];
  const dataLines = tableLines.slice(2); // Skip separator line

  // Parse header
  const headers = headerLine.split('|')
    .map(h => h.trim())
    .filter(h => h.length > 0);

  // Build table HTML
  let html = '<table class="markdown-table">\n<thead>\n<tr>\n';
  headers.forEach(header => {
    html += `<th>${header}</th>\n`;
  });
  html += '</tr>\n</thead>\n<tbody>\n';

  // Parse data rows
  dataLines.forEach(line => {
    const cells = line.split('|')
      .map(c => c.trim())
      .filter(c => c.length > 0);

    if (cells.length > 0) {
      html += '<tr>\n';
      cells.forEach(cell => {
        html += `<td>${cell}</td>\n`;
      });
      html += '</tr>\n';
    }
  });

  html += '</tbody>\n</table>';
  return html;
};

export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export const formatDate = (isoString) => {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

  return date.toLocaleDateString();
};
