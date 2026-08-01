try:
    from .document_parser import DocumentParser
except Exception:  # pragma: no cover - optional dependency guard
    DocumentParser = None

try:
    from .clause_extractor import ClauseExtractor
except Exception:  # pragma: no cover - optional dependency guard
    ClauseExtractor = None

from .risk_analyzer import RiskAnalyzer

try:
    from .llm_explainer import LLMExplainer
except Exception:  # pragma: no cover - optional dependency guard
    LLMExplainer = None

__all__ = ['DocumentParser', 'ClauseExtractor', 'RiskAnalyzer', 'LLMExplainer']
