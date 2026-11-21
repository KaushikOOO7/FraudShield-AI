import math
from collections import Counter
from urllib.parse import parse_qsl

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from backend.app.utils.urls import parse_public_url

FEATURE_VERSION = "url-text-features-v1"
FEATURE_NAMES = ["url_length", "host_length", "path_length", "query_length", "host_labels", "is_ip", "https_scheme", "digits", "hyphens", "percent_signs", "slashes", "at_signs", "question_marks", "query_fields", "entropy", "lexical_tokens"]


def features(value):
    parsed = parse_public_url(value)
    text = parsed.normalized
    counts = Counter(text)
    entropy = -sum((count / len(text)) * math.log2(count / len(text)) for count in counts.values())
    from urllib.parse import urlsplit
    query = urlsplit(text).query
    return [len(text), len(parsed.hostname), len(parsed.path), len(query), len(parsed.hostname.split(".")), int(parsed.ip_literal), int(parsed.scheme == "https"), sum(char.isdigit() for char in text), text.count("-"), text.count("%"), text.count("/"), text.count("@"), text.count("?"), len(parse_qsl(query)), entropy, sum(token in text.casefold() for token in ("login", "verify", "secure", "bank", "kyc", "update"))]


class URLFeatures(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return np.asarray([features(value) for value in X], dtype=np.float64)


def domain_group(value):
    parsed = parse_public_url(value)
    return parsed.hostname if parsed.ip_literal else ".".join(parsed.hostname.split(".")[-2:])
