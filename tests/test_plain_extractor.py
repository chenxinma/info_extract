from pathlib import Path
import unittest

import langextract as lx
from langextract.data import AnnotatedDocument

from info_extract.extract.plain_extract import PlainExtractor

class TestPlainExtractor(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PlainExtractor()
        return super().setUp()

    def test_extract_one(self):
        fname = Path("./processing/Departure notice (8.42 KB)_20251023153358.txt")
        with open(fname, 'r', encoding='utf-8') as f:
            content = f.read()
            doc = lx.data.Document(content,
                                    document_id=fname.stem)
            result = self.extractor.fetch_all([doc])
            for extract_result in result:
                assert extract_result is not None, "extract_result must not be None"
                assert extract_result.data is not None, "data must not be None"
                print(extract_result.data)
