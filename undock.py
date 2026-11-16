"""Извлечение текста и разбиение документов на фрагменты."""
import argparse
import html.parser
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


class HtmlText(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.hidden += 1
        if not self.hidden and tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'tr'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript') and self.hidden:
            self.hidden -= 1
        elif not self.hidden and tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def extract(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in ('.txt', '.md'):
        text = path.read_text(encoding='utf-8-sig')
    elif suffix in ('.html', '.htm'):
        parser = HtmlText()
        parser.feed(path.read_text(encoding='utf-8-sig'))
        text = ''.join(parser.parts)
    elif suffix == '.docx':
        with zipfile.ZipFile(path) as doc:
            xml = doc.read('word/document.xml')
        root = ElementTree.fromstring(xml)
        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text = '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in root.findall('.//w:p', ns))
    elif suffix == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError('Для PDF установите зависимости: pip install -r requirements.txt') from exc
        text = '\n\n'.join(page.extract_text() or '' for page in PdfReader(str(path)).pages)
    else:
        raise ValueError(f'Формат {suffix or "без расширения"} не поддерживается')
    return re.sub(r'\n{3,}', '\n\n', text.replace('\r\n', '\n')).strip()


def chunks(text, size=1500, overlap=150):
    if size < 1 or not 0 <= overlap < size:
        raise ValueError('Размер должен быть положительным, а перекрытие — меньше размера')
    result = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        result.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return result


def main():
    parser = argparse.ArgumentParser(description='Извлечь текст из документа и сохранить фрагменты в JSON')
    parser.add_argument('document', type=Path)
    parser.add_argument('-o', '--output', type=Path)
    parser.add_argument('--size', type=int, default=1500)
    parser.add_argument('--overlap', type=int, default=150)
    args = parser.parse_args()
    try:
        text = extract(args.document)
        result = {'source': args.document.name, 'characters': len(text), 'chunks': chunks(text, args.size, args.overlap)}
        output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.write_text(output, encoding='utf-8')
        else:
            sys.stdout.write(output)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ElementTree.ParseError, RuntimeError) as error:
        parser.exit(1, f'Ошибка: {error}\n')


if __name__ == '__main__':
    main()
