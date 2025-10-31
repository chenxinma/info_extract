from langextract.core import debug_utils
from langextract.core.tokenizer import CharInterval, Token, TokenType, TokenizedText
import regex
import jieba

jieba.setLogLevel(jieba.logging.INFO)
# Regex patterns for tokenization.
_LETTERS_PATTERN = r"[\p{L}]+"
_DIGITS_PATTERN = r"[\p{Nd}]+"
_SYMBOLS_PATTERN = r"[^\p{L}\p{Nd}\s]+"
_REGEX_FLAGS = regex.VERSION1 | regex.UNICODE
_END_OF_SENTENCE_PATTERN = regex.compile(r"[.?!。？！।۔؟]+$", _REGEX_FLAGS)
_SLASH_ABBREV_PATTERN = r"(?:\p{L}+(?:/\p{L}+)+|\p{Nd}+(?:/\p{Nd}+)+)|(?:\p{Nd}{4}年\p{Nd}{1,2}月(\p{Nd}{1,2}日))"

_CJK_PATTERN = regex.compile(
    r"\p{Han}",
    regex.UNICODE,
)

_TOKEN_PATTERN = regex.compile(
    rf"{_SLASH_ABBREV_PATTERN}|{_LETTERS_PATTERN}|{_DIGITS_PATTERN}|{_SYMBOLS_PATTERN}"
)
_WORD_PATTERN = regex.compile(rf"(?:{_LETTERS_PATTERN}|{_DIGITS_PATTERN})\Z")

# Known abbreviations that should not count as sentence enders.
# TODO: This can potentially be removed given most use cases
# are larger context.
_KNOWN_ABBREVIATIONS = frozenset({"Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "St."})


def _cjk_tokenize(text: str, start_pos: int = 0, token: Token | None = None) -> list[Token]:
    tokens = []
    previous_end = 0
    if not _CJK_PATTERN.match(text) and token is not None:
        return [token]
    for token_index, word in enumerate(jieba.cut(text)):
        _sub_start_pos, _sub_end_pos = previous_end, previous_end + len(word)
        # Create a new token.
        token = Token(
            index=token_index,
            char_interval=CharInterval(start_pos=start_pos + _sub_start_pos, end_pos=start_pos + _sub_end_pos),
            token_type=TokenType.WORD,
            first_token_after_newline=False,
        )
        if token_index > 0:
            gap = text[previous_end:_sub_start_pos]
            if "\n" in gap or "\r" in gap:
                token.first_token_after_newline = True
        tokens.append(token)
        previous_end = _sub_end_pos
    return tokens

@debug_utils.debug_log_calls
def tokenize(text: str) -> TokenizedText:
  """Splits text into tokens (words, digits, or punctuation).

  Each token is annotated with its character position and type (WORD or
  PUNCTUATION). If there is a newline or carriage return in the gap before
  a token, that token's `first_token_after_newline` is set to True.

  Args:
    text: The text to tokenize.

  Returns:
    A TokenizedText object containing all extracted tokens.
  """
  tokenized = TokenizedText(text=text)
  previous_end = 0
  for token_index, match in enumerate(_TOKEN_PATTERN.finditer(text)):
    start_pos, end_pos = match.span()
    matched_text = match.group()
    # Create a new token.
    token = Token(
        index=token_index,
        char_interval=CharInterval(start_pos=start_pos, end_pos=end_pos),
        token_type=TokenType.WORD,
        first_token_after_newline=False,
    )
    # Check if there's a newline in the gap before this token.
    if token_index > 0:
      gap = text[previous_end:start_pos]
      if "\n" in gap or "\r" in gap:
        token.first_token_after_newline = True
    # Classify token type.
    if regex.fullmatch(_DIGITS_PATTERN, matched_text):
      token.token_type = TokenType.NUMBER
    elif regex.fullmatch(_SLASH_ABBREV_PATTERN, matched_text):
      token.token_type = TokenType.ACRONYM
    elif _WORD_PATTERN.fullmatch(matched_text):
      token.token_type = TokenType.WORD
    else:
      token.token_type = TokenType.PUNCTUATION
    
    if token.token_type == TokenType.WORD:
      cjk_tokens = _cjk_tokenize(matched_text, start_pos=start_pos, token=token)
      tokenized.tokens.extend(cjk_tokens)
    else:
      tokenized.tokens.append(token)
    previous_end = end_pos
  return tokenized