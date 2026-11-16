import tempfile
import unittest
import zipfile
from pathlib import Path
from undock import chunks, extract


class UndockTests(unittest.TestCase):
    def test_chunk_overlap_and_validation(self):
        self.assertEqual(chunks('abcdefgh', 5, 2), ['abcde', 'defgh'])
        with self.assertRaises(ValueError):
            chunks('abc', 3, 3)

    def test_extract_html_and_docx(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / 'page.html'
            page.write_text('<h1>Привет</h1><script>secret()</script><p>Мир</p>', encoding='utf-8')
            self.assertEqual(extract(page), 'Привет\n\nМир')
            doc = root / 'a.docx'
            with zipfile.ZipFile(doc, 'w') as archive:
                archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Текст</w:t></w:r></w:p></w:body></w:document>')
            self.assertEqual(extract(doc), 'Текст')


if __name__ == '__main__':
    unittest.main()
