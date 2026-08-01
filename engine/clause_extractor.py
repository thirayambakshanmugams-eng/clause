"""
Clause Extractor Module for ClauseGuard Engine.

Provides the ClauseExtractor class that uses spaCy NLP to segment
document text into logical clauses, detect section headers, and
extract named entities from each clause.
"""

import re
from typing import List, Dict, Optional, Any

try:
    import spacy
    from spacy.language import Language
except ImportError:
    spacy = None


class ClauseExtractor:
    """Segments document text into logical clauses using spaCy NLP.

    Uses spaCy's sentence boundary detection and named entity recognition
    to produce structured clause objects. Falls back to regex-based
    sentence splitting when spaCy is unavailable.

    Attributes:
        SECTION_PATTERNS: Compiled regex patterns for detecting section headers.
        MIN_CLAUSE_WORDS: Minimum word count for a clause to be included.
        ENTITY_LABELS: NER labels to extract from clauses.
    """

    SECTION_PATTERNS: List[str] = [
        r'^\s*(?:section|article|clause|part)\s+\d+',       # Section 1, Article 2
        r'^\s*\d+\.\d*\s+',                                  # 1. or 1.2
        r'^\s*\([a-z]\)',                                     # (a), (b)
        r'^\s*[A-Z][A-Z\s]{2,}:?\s*$',                       # ALL CAPS HEADER
        r'^\s*(?:[IVXLC]+\.)',                                # Roman numerals I. II. III.
        r'^\s*\d+\)\s+',                                     # 1) 2)
        r'^\s*[a-z]\)\s+',                                   # a) b)
        r'^\s*(?:schedule|exhibit|appendix|annex)\s+',        # Schedule A, Exhibit 1
    ]

    MIN_CLAUSE_WORDS: int = 10
    ENTITY_LABELS: set = {'ORG', 'PERSON', 'DATE', 'MONEY', 'GPE'}

    def __init__(self) -> None:
        """Initialize the extractor, attempting to load the spaCy model."""
        self.nlp: Optional[Any] = None
        self._compiled_patterns: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in self.SECTION_PATTERNS
        ]

        if spacy is not None:
            try:
                self.nlp = spacy.load('en_core_web_sm')
            except OSError:
                self.nlp = None

    @property
    def has_nlp(self) -> bool:
        """Whether spaCy NLP model is available."""
        return self.nlp is not None

    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract clauses from document text.

        Splits text into paragraphs, detects section headers, segments
        sentences using spaCy (or fallback), groups them into clauses,
        and extracts named entities.

        Args:
            text: The full document text to segment.

        Returns:
            A list of clause dicts, each containing:
                - id (str): Clause identifier like 'clause_1'.
                - text (str): The full clause text.
                - section_header (str or None): Detected section header, if any.
                - entities (list): Named entities found in the clause.
                - sentence_count (int): Number of sentences in the clause.
        """
        if not text or not text.strip():
            return []

        paragraphs = self._split_paragraphs(text)
        raw_clauses = self._group_into_clauses(paragraphs)
        clauses = self._build_clause_dicts(raw_clauses)

        return clauses

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs on double newlines or blank lines.

        Args:
            text: Raw document text.

        Returns:
            List of non-empty paragraph strings.
        """
        # Split on one or more blank lines
        parts = re.split(r'\n\s*\n', text)
        return [p.strip() for p in parts if p.strip()]

    def _is_section_header(self, text: str) -> bool:
        """Check if a text line matches any known section header pattern.

        Args:
            text: A single paragraph or line of text.

        Returns:
            True if the text matches a section header pattern.
        """
        # Only check the first line of the paragraph
        first_line = text.split('\n')[0].strip()
        if not first_line:
            return False

        for pattern in self._compiled_patterns:
            if pattern.match(first_line):
                return True

        return False

    def _extract_header_text(self, paragraph: str) -> str:
        """Extract the section header text from a paragraph.

        Takes the first line of the paragraph as the header.

        Args:
            paragraph: The paragraph text.

        Returns:
            The cleaned header string.
        """
        first_line = paragraph.split('\n')[0].strip()
        # Clean up trailing colons and extra whitespace
        return re.sub(r':?\s*$', '', first_line).strip()

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using spaCy or regex fallback.

        Args:
            text: Text to split into sentences.

        Returns:
            List of sentence strings.
        """
        if self.nlp is not None:
            # Use spaCy sentence boundary detection
            # Process in chunks if text is very long to avoid memory issues
            max_chars = 100000
            if len(text) > max_chars:
                sentences = []
                for i in range(0, len(text), max_chars):
                    chunk = text[i:i + max_chars]
                    doc = self.nlp(chunk)
                    sentences.extend([sent.text.strip() for sent in doc.sents if sent.text.strip()])
                return sentences
            else:
                doc = self.nlp(text)
                return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        else:
            return self._fallback_split_sentences(text)

    def _fallback_split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex when spaCy is unavailable.

        Handles common abbreviations and edge cases in legal text.

        Args:
            text: Text to split.

        Returns:
            List of sentence strings.
        """
        # Two-pass approach to avoid variable-width look-behind (not supported in Python re):
        # 1. Temporarily protect known abbreviations by replacing their trailing period
        abbreviations = ['Mr', 'Mrs', 'Ms', 'Dr', 'Jr', 'Sr', 'Inc', 'Ltd', 'Corp', 'Co',
                         'vs', 'etc', 'i.e', 'e.g', 'No', 'Art', 'Sec']
        protected = text
        for abbr in abbreviations:
            protected = protected.replace(abbr + '.', abbr + '\x00')

        # 2. Split on sentence-ending punctuation followed by whitespace and uppercase letter
        pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        parts = re.split(pattern, protected)

        # 3. Restore protected abbreviation periods
        sentences = [s.replace('\x00', '.').strip() for s in parts if s.strip()]
        return sentences

    def _extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extract named entities from text using spaCy NER.

        Args:
            text: Text to extract entities from.

        Returns:
            List of entity dicts with 'text' and 'label' keys.
            Returns empty list if spaCy is unavailable.
        """
        if self.nlp is None:
            return []

        doc = self.nlp(text[:100000])  # Limit for performance
        entities = []
        seen = set()

        for ent in doc.ents:
            if ent.label_ in self.ENTITY_LABELS:
                key = (ent.text.strip(), ent.label_)
                if key not in seen:
                    seen.add(key)
                    entities.append({
                        'text': ent.text.strip(),
                        'label': ent.label_,
                    })

        return entities

    def _group_into_clauses(self, paragraphs: List[str]) -> List[Dict[str, Any]]:
        """Group paragraphs into logical clauses based on section boundaries.

        Each paragraph becomes its own clause. Section headers are attached
        to the following clause content. Consecutive non-header paragraphs
        under the same section share that section's header.

        Args:
            paragraphs: List of paragraph strings.

        Returns:
            List of raw clause dicts with 'text', 'section_header', and 'sentences'.
        """
        clauses: List[Dict[str, Any]] = []
        current_header: Optional[str] = None

        for paragraph in paragraphs:
            is_header = self._is_section_header(paragraph)

            if is_header:
                header_text = self._extract_header_text(paragraph)
                current_header = header_text

                # Check if there's content beyond the header line
                lines = paragraph.split('\n')
                remaining_text = '\n'.join(lines[1:]).strip()

                if remaining_text and len(remaining_text.split()) >= self.MIN_CLAUSE_WORDS:
                    sentences = self._split_sentences(remaining_text)
                    clauses.append({
                        'text': remaining_text,
                        'section_header': current_header,
                        'sentences': sentences,
                    })
            else:
                # Regular paragraph — treat as a clause
                sentences = self._split_sentences(paragraph)
                word_count = len(paragraph.split())

                if word_count >= self.MIN_CLAUSE_WORDS:
                    clauses.append({
                        'text': paragraph,
                        'section_header': current_header,
                        'sentences': sentences,
                    })

        return clauses

    def _build_clause_dicts(self, raw_clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build final clause dicts with IDs and entity extraction.

        Args:
            raw_clauses: List of raw clause dicts from _group_into_clauses.

        Returns:
            List of finalized clause dicts.
        """
        clauses = []

        for idx, raw in enumerate(raw_clauses, start=1):
            entities = self._extract_entities(raw['text'])
            clause = {
                'id': f'clause_{idx}',
                'text': raw['text'],
                'section_header': raw.get('section_header'),
                'entities': entities,
                'sentence_count': len(raw['sentences']),
            }
            clauses.append(clause)

        return clauses
