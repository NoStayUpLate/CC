"""
关键词提取服务（English NLP）。

仅支持英语，使用 re + collections.Counter 实现，无需外部 NLP 库。
- 正则分词：提取 3-20 字符的英文单词
- 停用词过滤：剔除高频无意义功能词
- 结果：返回词频最高的前 N 个词，dict[str, int]

日语/韩语等需重型分词库的语言返回 None（零数据保护）。
"""
import re
from collections import Counter
from typing import Optional

# 英语停用词（含功能词、助动词、代词、常见副词等）
_EN_STOPWORDS = frozenset([
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "can", "not", "no", "nor",
    "so", "yet", "both", "either", "neither", "each", "few", "more",
    "most", "other", "some", "such", "than", "too", "very", "just",
    "this", "that", "these", "those", "it", "its", "he", "she", "they",
    "we", "you", "i", "me", "my", "him", "her", "us", "his", "our",
    "their", "your", "who", "what", "which", "when", "where", "how",
    "all", "any", "once", "only", "own", "same", "then", "there",
    "here", "into", "after", "before", "about", "between", "through",
    "during", "again", "further", "over", "under", "while", "because",
    "if", "as", "up", "out", "down", "off", "back", "also", "even",
    "well", "still", "already", "now", "got", "get", "go", "said",
    "like", "one", "two", "three", "first", "last", "new", "old",
    "long", "great", "little", "good", "high", "big", "man", "woman",
    "day", "time", "way", "come", "make", "take", "see", "know",
    "look", "think", "feel", "want", "need", "say", "tell", "let",
    "seem", "turn", "move", "live", "give", "never", "ever", "always",
    "much", "many", "every", "around", "later", "since", "put", "use",
    "find", "keep", "ask", "try", "call", "far", "away", "left",
    "right", "hand", "face", "head", "eye", "eyes", "voice", "word",
    "room", "door", "things", "thing", "world", "life", "people",
    "years", "year", "months", "days", "something", "nothing",
    "everything", "anything", "someone", "anyone", "everyone", "them",
    "able", "didn", "don", "doesn", "isn", "wasn", "weren", "won",
    "wouldn", "couldn", "shouldn", "hadn", "haven", "mustn", "aren",
    "that", "what", "just", "from", "your", "they", "with", "have",
    "this", "will", "been", "were", "their", "said", "each", "which",
    "she", "into", "than", "could", "when", "there", "some", "these",
    "would", "make", "like", "him", "has", "two", "more", "very",
    "after", "words", "its", "him", "his", "how", "man", "our",
    "out", "about", "also", "then", "them", "she", "many", "some",
    "came", "thought", "looked", "stood", "walked", "seemed",
    "felt", "heard", "saw", "knew", "said", "asked", "told",
    "going", "being", "having", "doing", "saying", "made", "took",
    "came", "went", "got", "knew", "saw", "let", "put", "set",
    "had", "was", "were", "been", "are", "the", "but", "and",
    "with", "for", "that", "not", "this", "you", "from", "his",
    "they", "she", "have", "her", "can", "all", "which", "one",
    "would", "there", "their", "what", "out", "about", "who",
    "get", "when", "will", "more", "no", "him", "into", "time",
    "has", "look", "two", "how", "its", "then", "some", "than",
    "could", "these", "do", "other", "may", "know", "an", "to",
])

_EN_WORD_RE = re.compile(r"\b[a-zA-Z]{3,20}\b")
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_html(html: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = _HTML_TAG_RE.sub(" ", html)
    return _WHITESPACE_RE.sub(" ", text).strip()


def extract_keywords_en(text: str, top_n: int = 20) -> dict[str, int]:
    """
    从英文文本中提取高频关键词。
    使用正则分词 + 停用词过滤 + Counter 统计。
    """
    words = _EN_WORD_RE.findall(text.lower())
    filtered = [w for w in words if w not in _EN_STOPWORDS]
    counter = Counter(filtered)
    return dict(counter.most_common(top_n))


def extract_keywords(text: str, lang: str, top_n: int = 20) -> Optional[dict[str, int]]:
    """
    根据语言提取关键词。不支持的语言（如日语、韩语）返回 None。

    Args:
        text: 原始正文（可含 HTML 标签，会自动剥离）
        lang: 语言代码，当前仅支持 "en"
        top_n: 返回词频最高的 N 个词

    Returns:
        dict[词, 频率] 或 None（无数据/不支持）
    """
    if not text or not text.strip():
        return None
    if lang == "en":
        result = extract_keywords_en(text, top_n)
        return result if result else None
    # 日语/韩语分词需要 janome/konlpy 等重型库，当前返回 None
    return None
