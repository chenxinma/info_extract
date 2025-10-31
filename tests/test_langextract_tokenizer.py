import unittest

from info_extract.extract.tokenizer import tokenize

class TestTokenizer(unittest.TestCase):
    @unittest.skip("skip test_tokenize")
    def test_tokenize(self):
        text = "员工name将于月底离职，最后雇佣日为2022年11月11日，为非自愿离职（协商解除劳动合同）。请协助办理相关离职事宜。谢谢！"
        tokenized = tokenize(text)
        # self.assertEqual(tokens, ["Hello", ",", "world", "!", "12345", "."])
        print(tokenized.text)
        for token in tokenized.tokens:
            print(text[token.char_interval.start_pos:token.char_interval.end_pos], token.token_type, token.char_interval)
    
    # @unittest.skip("skip test_tokenize_2")
    def test_tokenize_2(self):
        text = "| 2025.10增员 | 00002 | 李四 | Hire | 2025/10/9 |  | CNABB NJ | 南京 | 上海外服 | 17200 | 17200 | 610101200001014239 | +86 19951770387 |  |  |  | 2025.10.09 | 2028.10.08 |  |"
        tokenized = tokenize(text)
        print(tokenized.text)
        for token in tokenized.tokens:
            print(text[token.char_interval.start_pos:token.char_interval.end_pos], token.token_type)
    
    def test_tokenize_3(self):
        text = """**CAUTION:** This email originated from outside of the organization. Do not click links, scan QR codes, or open attachments unless you can confirm the sender and know the content is safe. If you think
this email might be suspicious, notify lululemon’s Cybersecurity team by clicking the HOX button.
Eli ji （季子涵） 198581 in China Mainland has completed Onboarding. Below is additional information for the employee to enroll employee in work-injury insurance."""
        tokenized = tokenize(text)
        print(tokenized.text)
        for token in tokenized.tokens:
            print(text[token.char_interval.start_pos:token.char_interval.end_pos], token.token_type)
    