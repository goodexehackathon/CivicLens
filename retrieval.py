"""Lexical TF-IDF retrieval (no network, works for Devanagari tokens too).
Scores are uncalibrated cosine similarities, used only for ranking + thresholding."""
import math, re
from collections import Counter
from config import MIN_RELEVANCE, TOP_K, MIN_COVERAGE

STOP = set("the a an of to is are was be in on or and for by at as it this that what which when who how do does की का के है में से क्या कब को और पर".split())

def tokens(t):
    return [w for w in re.findall(r"[\w\u0900-\u097F]+", t.lower()) if w not in STOP and len(w) > 1]

class Index:
    def __init__(self, chunks):
        self.chunks = chunks
        self.tf = [Counter(tokens(c.text)) for c in chunks]
        df = Counter(w for tf in self.tf for w in tf)
        n = len(chunks)
        self.idf = {w: math.log((n + 1) / (d + 1)) + 1 for w, d in df.items()}
        self.norm = [math.sqrt(sum((v * self.idf[w]) ** 2 for w, v in tf.items())) or 1 for tf in self.tf]

    def search(self, query, k=TOP_K, threshold=MIN_RELEVANCE):
        q = Counter(tokens(query))
        qn = math.sqrt(sum((v * self.idf.get(w, 1)) ** 2 for w, v in q.items())) or 1
        res = []
        for c, tf, nm in zip(self.chunks, self.tf, self.norm):
            s = sum(v * self.idf.get(w, 1) * tf[w] * self.idf.get(w, 1) for w, v in q.items() if w in tf) / (qn * nm)
            cov = sum(1 for w in q if w in tf) / (len(q) or 1)  # share of distinct query terms present
            if s >= threshold and cov >= MIN_COVERAGE:
                res.append((s, c))
        res.sort(key=lambda x: -x[0])
        return res[:k]   # empty list == explicit no-evidence result
