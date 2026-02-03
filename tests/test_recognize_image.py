from pathlib import Path
import unittest
from info_extract.utils import recognize_image

class TestRecognizeImage(unittest.IsolatedAsyncioTestCase):

    async def test_recognize_image(self):
        image_path = Path(__file__).parent / 'files' / 'test1.png'
        result = await recognize_image(str(image_path))
        self.assertIsNotNone(result)
        print(result.to_pandas().iloc[0]) # 打印识别结果 # pyright: ignore