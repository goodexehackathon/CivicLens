import os
MAX_FILE_MB = int(os.getenv("CL_MAX_FILE_MB", "25"))
MIN_RELEVANCE = float(os.getenv("CL_MIN_RELEVANCE", "0.12"))  # uncalibrated cosine score, NOT a probability
TOP_K = int(os.getenv("CL_TOP_K", "5"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # never hardcode
ABSTAIN_MSG = "I cannot verify this from the uploaded documents."
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # configurable; verify availability in your account
MIN_COVERAGE = float(os.getenv("CL_MIN_COVERAGE", "0.4"))  # min share of query terms found in a passage
