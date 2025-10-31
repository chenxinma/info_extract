from pathlib import Path
import unittest

from info_extract.extract import SpreadsheetExtractor

class TestSpreadsheetExtractor(unittest.TestCase):
    def setUp(self) -> None:
        processing_dir = r"D:\tmp\info_extract\work\processing"
        self.extractor = SpreadsheetExtractor(processing_dir)
        self.extractor.pre_results = [
           (str(f), []) for f in Path(processing_dir).glob("*.parquet")
        ]
        return super().setUp()
    
    def test_run(self):
        for extract_result in self.extractor.run():
            print(extract_result[0])