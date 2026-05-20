# -*- coding: utf-8 -*-
"""
龙虾调研助手  - 文本压缩工具与测试套件
"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
from dataclasses import dataclass


@dataclass
class CompressStats:
    original_length: int = 0
    compressed_length: int = 0
    sentence_count_original: int = 0
    sentence_count_deduplicated: int = 0
    sentence_count_final: int = 0
    duplicate_removed: int = 0
    redundant_removed: int = 0
    compress_ratio: float = 0.0


class TextCompressor:
    def __init__(self, ngram_size: int = 2, min_sentence_length: int = 5, max_sentence_length: int = 1000):
        self.ngram_size = ngram_size
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length
        self.stats = CompressStats()
        self.sentence_terminators = re.compile(r'[。！？；;!\?\n\r]+')
        self.noise_chars = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9\s\.,\'\"\-:%/°]')
        self.punctuation_spaces = re.compile(r'\s+')
        self.bracket_patterns = [
            re.compile(r'【[^】]*】'),
            re.compile(r'《[^》]*》'),
            re.compile(r'\([^)]*\)'),
            re.compile(r'（[^）]*）'),
            re.compile(r'『[^』]*』'),
            re.compile(r'「[^」]*」'),
        ]
        self.useless_prefixes = re.compile(
            r'^(记者|编辑|来源|发布时间|摘要|核心|关键词|导读|本文|本网|讯|最新|公告|资讯|报告|分析|点评|快评|速览|提示)[:： ]*',
            re.IGNORECASE
        )
        self.stop_fragments = {
            '', '-', '—', '–', '.', ',', ':', '：', ';', '；',
            '!', '!', '?', '？', ' ', '  ', '   '
        }

    def clean_brackets(self, text: str) -> str:
        for pattern in self.bracket_patterns:
            text = pattern.sub('', text)
        return text

    def normalize_whitespace(self, text: str) -> str:
        return self.punctuation_spaces.sub(' ', text).strip()

    def remove_useless_prefix(self, text: str) -> str:
        return self.useless_prefixes.sub('', text).strip()

    def clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.strip()
        text = self.clean_brackets(text)
        text = self.noise_chars.sub(' ', text)
        text = self.remove_useless_prefix(text)
        text = self.normalize_whitespace(text)
        return text

    def create_fingerprint(self, sentence: str) -> str:
        cleaned = self.clean_text(sentence).lower()
        if len(cleaned) < self.min_sentence_length:
            return ""
        return cleaned

    def split_into_sentences(self, text: str) -> List[str]:
        if not text:
            return []
        raw_sentences = self.sentence_terminators.split(text)
        valid_sentences = []
        for s in raw_sentences:
            s = s.strip()
            if self.min_sentence_length <= len(s) <= self.max_sentence_length and s not in self.stop_fragments:
                valid_sentences.append(s)
        return valid_sentences

    def deduplicate_sentences(self, sentences: List[str]) -> List[str]:
        unique = []
        seen = set()
        for sent in sentences:
            fp = self.create_fingerprint(sent)
            if not fp:
                continue
            if fp not in seen:
                seen.add(fp)
                unique.append(sent)
        self.stats.duplicate_removed = len(sentences) - len(unique)
        self.stats.sentence_count_deduplicated = len(unique)
        return unique

    def compute_ngram_frequency(self, text: str) -> Counter:
        chars = list(text)
        ngrams = []
        for i in range(len(chars) - self.ngram_size + 1):
            gram = ''.join(chars[i:i+self.ngram_size])
            if gram.strip():
                ngrams.append(gram)
        return Counter(ngrams)

    def filter_redundant_sentences(self, sentences: List[str]) -> List[str]:
        if len(sentences) <= 1:
            return sentences
        full_text = ''.join(sentences)
        freq = self.compute_ngram_frequency(full_text)
        if not freq:
            return sentences
        max_freq = max(freq.values())
        # 如果没有任何 n-gram 重复，则不存在冗余
        if max_freq <= 1:
            self.stats.redundant_removed = 0
            self.stats.sentence_count_final = len(sentences)
            return sentences
        keep = []
        for sent in sentences:
            sent_chars = list(sent)
            score = 0
            ngram_count = 0
            for i in range(len(sent_chars) - self.ngram_size + 1):
                gram = ''.join(sent_chars[i:i+self.ngram_size])
                score += freq.get(gram, 0)
                ngram_count += 1
            # 平均 n-gram 频率: 1.0 = 全唯一, >1.0 = 存在重叠
            avg_freq = score / ngram_count if ngram_count > 0 else 0
            # 阈值基于最大频率动态调整
            threshold = 1.0 + (max_freq - 1.0) * 0.5
            if avg_freq <= threshold:
                keep.append(sent)
        self.stats.redundant_removed = len(sentences) - len(keep)
        self.stats.sentence_count_final = len(keep)
        return keep

    def compress_plain_text(self, text: str) -> str:
        if not text or len(text) < self.min_sentence_length:
            return text
        self.stats = CompressStats()
        self.stats.original_length = len(text)
        sents = self.split_into_sentences(text)
        self.stats.sentence_count_original = len(sents)
        if not sents:
            return ""
        deduped = self.deduplicate_sentences(sents)
        filtered = self.filter_redundant_sentences(deduped)
        compressed = ' '.join(filtered)
        self.stats.compressed_length = len(compressed)
        if self.stats.original_length > 0:
            self.stats.compress_ratio = round(self.stats.compressed_length / self.stats.original_length, 3)
        return compressed

    def _traverse_and_compress(self, data: Any, target_keys: Optional[List[str]]) -> Any:
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, str):
                    if target_keys is None or key in target_keys:
                        if len(value) >= 20:
                            result[key] = self.compress_plain_text(value)
                        else:
                            result[key] = value
                    else:
                        result[key] = value
                elif isinstance(value, (dict, list)):
                    result[key] = self._traverse_and_compress(value, target_keys)
                else:
                    result[key] = value
            return result
        elif isinstance(data, list):
            return [self._traverse_and_compress(item, target_keys) for item in data]
        else:
            return data

    def compress_json(self, json_data: Dict[str, Any], target_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        return self._traverse_and_compress(json_data, target_keys)

    # ── 跨字段语料压缩 ─────────────────────────────────────────
    _SKIP_KEYS = frozenset({
        'url', '文章来源', '来源', 'source', 'date', '发布时间',
        '代码', 'code', '数据源', '格式', 'format',
    })

    def _is_content_field(self, key: str) -> bool:
        """判断字段名是否属于'正文内容'型字段"""
        content_keys = {'新闻内容', '新闻标题', '内容', '标题', 'title',
                        'content', 'snippet', '摘要', '正文', '描述',
                        'raw_text', 'desc', 'description'}
        return key in content_keys

    def _collect_long_strings(self, data: Any, parent_key: str = "") -> List[str]:
        """DFS 收集正文类长字符串（跳过 URL/来源/代码等字段）"""
        result = []
        if isinstance(data, dict):
            for k, v in data.items():
                if k in self._SKIP_KEYS:
                    continue
                if isinstance(v, str) and len(v) >= 20:
                    result.append(v)
                else:
                    result.extend(self._collect_long_strings(v, k))
        elif isinstance(data, list):
            for item in data:
                result.extend(self._collect_long_strings(item))
        elif isinstance(data, str) and len(data) >= 20:
            # 没有父 key 上下文时也收集（如数组直接元素）
            result.append(data)
        return result

    def _build_global_ngram_freq(self, data: Any) -> Counter:
        """遍历全 JSON 建立全局 n-gram 频率"""
        all_texts = self._collect_long_strings(data)
        if not all_texts:
            return Counter()
        corpus = ''.join(all_texts)
        return self.compute_ngram_frequency(corpus)

    def _filter_redundant_sentences_with_freq(
        self, sentences: List[str], global_freq: Counter
    ) -> List[str]:
        """用外部 n-gram 频率过滤冗余句子"""
        if len(sentences) <= 1:
            return sentences
        if not global_freq:
            return sentences
        max_freq = max(global_freq.values())
        if max_freq <= 1:
            return sentences
        keep = []
        for sent in sentences:
            sent_chars = list(sent)
            score = 0
            ngram_count = 0
            for i in range(len(sent_chars) - self.ngram_size + 1):
                gram = ''.join(sent_chars[i:i+self.ngram_size])
                score += global_freq.get(gram, 0)
                ngram_count += 1
            avg_freq = score / ngram_count if ngram_count > 0 else 0
            threshold = 1.0 + (max_freq - 1.0) * 0.5
            if avg_freq <= threshold:
                keep.append(sent)
        self.stats.redundant_removed = len(sentences) - len(keep)
        self.stats.sentence_count_final = len(keep)
        return keep

    def _compress_text_with_global_freq(self, text: str, global_freq: Counter) -> str:
        """用全局 n-gram 频率压缩单段文本"""
        if not text or len(text) < self.min_sentence_length:
            return text
        sents = self.split_into_sentences(text)
        if not sents:
            return ""
        deduped = self.deduplicate_sentences(sents)
        filtered = self._filter_redundant_sentences_with_freq(deduped, global_freq)
        compressed = ' '.join(filtered)
        return compressed

    def _traverse_and_compress_with_global(self, data: Any, global_freq: Counter) -> Any:
        """遍历 JSON，用全局频率压缩每个长文本字符串字段"""
        if isinstance(data, dict):
            result = {}
            for k, v in data.items():
                if isinstance(v, str) and len(v) >= 20 and k not in self._SKIP_KEYS:
                    result[k] = self._compress_text_with_global_freq(v, global_freq)
                else:
                    result[k] = self._traverse_and_compress_with_global(v, global_freq)
            return result
        elif isinstance(data, list):
            return [
                self._traverse_and_compress_with_global(item, global_freq)
                for item in data
            ]
        elif isinstance(data, str) and len(data) >= 20:
            return self._compress_text_with_global_freq(data, global_freq)
        else:
            return data

    def compress_json_corpus(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        跨字段语料压缩。
        先遍历全 JSON 建立全局 n-gram 频率（跨所有字段/条目），
        再用全局频率逐个压缩长文本字段。
        """
        global_freq = self._build_global_ngram_freq(json_data)
        result = self._traverse_and_compress_with_global(json_data, global_freq)

        # 统计——重跑一次 collect 算整体长度
        orig_texts = self._collect_long_strings(json_data)
        comp_texts = self._collect_long_strings(result)
        self.stats = CompressStats()
        self.stats.original_length = sum(len(t) for t in orig_texts)
        self.stats.compressed_length = sum(len(t) for t in comp_texts)
        if self.stats.original_length > 0:
            self.stats.compress_ratio = round(
                self.stats.compressed_length / self.stats.original_length, 3
            )
        return result

    def auto_compress(self, content: Any, target_keys: Optional[List[str]] = None) -> Any:
        if isinstance(content, str):
            return self.compress_plain_text(content)
        elif isinstance(content, (dict, list)):
            return self.compress_json(content, target_keys)
        else:
            return content

    def get_stats(self) -> CompressStats:
        return self.stats

    def print_stats(self):
        s = self.stats
        print(f"=== 压缩统计 ===")
        print(f"原始长度: {s.original_length}")
        print(f"压缩后长度: {s.compressed_length}")
        print(f"压缩比: {s.compress_ratio:.1%}")
        print(f"原始句子: {s.sentence_count_original}")
        print(f"去重后: {s.sentence_count_deduplicated}")
        print(f"过滤冗余后: {s.sentence_count_final}")
        print(f"删除重复句: {s.duplicate_removed}")
        print(f"删除冗余句: {s.redundant_removed}")


# ═══════════════════════════════════════════════════════════
#  测试套件
# ═══════════════════════════════════════════════════════════

def test_clean_brackets():
    """测试清理各类括号"""
    c = TextCompressor()
    assert c.clean_brackets("【公告】内容") == "内容"
    assert c.clean_brackets("《报告》全文") == "全文"
    assert c.clean_brackets("(备注)正文") == "正文"
    assert c.clean_brackets("（备注）正文") == "正文"
    assert c.clean_brackets("无括号文本") == "无括号文本"


def test_normalize_whitespace():
    """测试空白标准化"""
    c = TextCompressor()
    assert c.normalize_whitespace("多  个   空格") == "多 个 空格"
    assert c.normalize_whitespace("  首尾空格  ") == "首尾空格"
    assert c.normalize_whitespace("正常文本") == "正常文本"


def test_remove_useless_prefix():
    """测试清除无用前缀"""
    c = TextCompressor()
    assert c.remove_useless_prefix("记者 张三 报道") == "张三 报道"
    assert c.remove_useless_prefix("编辑 李四") == "李四"
    assert c.remove_useless_prefix("来源 某某网") == "某某网"
    assert c.remove_useless_prefix("普通文本") == "普通文本"


def test_split_into_sentences():
    """测试按标点分句及长度过滤"""
    c = TextCompressor(min_sentence_length=3)
    sents = c.split_into_sentences("第一句。第二句。第三句。")
    assert len(sents) == 3, f"Expected 3 sentences, got {len(sents)}"
    sents2 = c.split_into_sentences("ab")
    assert all(len(s) >= 3 for s in sents2), "短句过滤失效"


def test_deduplicate_sentences():
    """测试句子去重"""
    c = TextCompressor()
    sents = ["这是第一句话。", "这是第一句话。", "这是不同的句子。"]
    deduped = c.deduplicate_sentences(sents)
    assert len(deduped) == 2, f"Expected 2 after dedup, got {len(deduped)}"
    assert c.stats.duplicate_removed == 1


def test_compute_ngram_frequency():
    """测试n-gram频率计算"""
    c = TextCompressor(ngram_size=2)
    freq = c.compute_ngram_frequency("人工智能")
    assert len(freq) > 0
    assert "人工" in freq, "bigram 人工 should be found"


def test_compress_plain_text():
    """测试完整压缩流程"""
    c = TextCompressor()
    text = "人工智能是重要技术方向。人工智能是重要技术方向。今天天气很好。"
    compressed = c.compress_plain_text(text)
    assert len(compressed) <= len(text), "压缩后应更短或相等"
    assert c.stats.duplicate_removed > 0, "重复句应被去重"


def test_compress_json():
    """测试JSON递归压缩，target_keys指定的字段被压缩"""
    c = TextCompressor()
    data = {
        "title": "报告标题",
        "content": "这是很长的一段。" * 20,
        "metadata": {"description": "简短描述"}
    }
    compressed = c.compress_json(data, target_keys=["content"])
    assert len(compressed["content"]) < len(data["content"]), "content 应被压缩"
    assert compressed["title"] == data["title"], "title 未在 target_keys 中，应不变"


def test_auto_compress():
    """测试自动模式检测（string走文本, dict走JSON）"""
    c = TextCompressor()
    text_result = c.auto_compress("很长很长" * 20)
    assert isinstance(text_result, str), "字符串输入应返回字符串"
    json_result = c.auto_compress({"key": "很长很长" * 20})
    assert isinstance(json_result, dict), "dict输入应返回dict"
    assert c.auto_compress(12345) == 12345, "数字应原样返回"


def test_filter_redundant_sentences():
    """测试冗余句子过滤"""
    c = TextCompressor(ngram_size=2)
    sents = ["人工智能技术在快速发展。", "人工智能技术正在不断进步。"]
    filtered = c.filter_redundant_sentences(sents)
    assert len(filtered) >= 1, "应至少保留1个句子"


def run_all_tests():
    """运行所有 test_ 开头的测试函数"""
    test_fns = [v for k, v in globals().items() if k.startswith("test_")]
    passed = 0
    failed = 0
    failures = []
    print(f"\n{'='*50}")
    print("  TextCompressor 测试套件")
    print(f"{'='*50}")
    for fn in test_fns:
        try:
            fn()
            print(f"  [PASS] {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {fn.__name__}: {e}")
            failed += 1
            failures.append(fn.__name__)
        except Exception as e:
            print(f"  [ERROR] {fn.__name__}: {e}")
            failed += 1
            failures.append(fn.__name__)
    print(f"{'='*50}")
    print(f"  结果: {passed} 通过, {failed} 失败, 共 {passed+failed} 项")
    if failures:
        print(f"  失败: {', '.join(failures)}")
    print(f"{'='*50}\n")
    return failed == 0


if __name__ == "__main__":
    import sys

    if "--demo" in sys.argv:
        compressor = TextCompressor()
        test_text = """
        人工智能是一门旨在使计算机系统能够模拟、延伸和扩展人类智能的技术科学。
        人工智能研究的领域包括机器学习、自然语言处理、计算机视觉、专家系统、机器人技术等方向。
        机器学习作为人工智能的核心分支，通过算法让计算机从数据中自动学习规律并进行预测与决策。
        机器学习是人工智能的核心分支，通过算法让计算机从数据中自动学习规律并进行预测与决策。
        深度学习属于机器学习的子类，依赖深层神经网络模型，在图像识别、语音识别、机器翻译等任务上表现极强。
        """
        compressed = compressor.compress_plain_text(test_text)
        print("压缩后:\n", compressed)
        compressor.print_stats()
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)
