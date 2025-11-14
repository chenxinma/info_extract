from pathlib import Path
import unittest

from info_extract.extract import SpreadsheetExtractor

class TestSpreadsheetExtractor(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        processing_dir = r"/data/home/macx/work/tmp/processing"
        self.extractor = SpreadsheetExtractor(processing_dir)
        self.extractor.pre_results = [
           (str(f), []) for f in Path(processing_dir).glob("*.parquet")
        ]
    
    async def test_run(self):
        async for extract_result in self.extractor.run():
            print(extract_result[0])