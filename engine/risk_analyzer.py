"""
Risk Analyzer Module for ClauseGuard Engine.

Provides the RiskAnalyzer class that uses TF-IDF vectorization and
cosine similarity to classify contract clause risk levels. Contains
50+ risk patterns across high, medium, and low risk categories.
"""

import re
import warnings
warnings.filterwarnings("ignore")
from typing import List, Dict, Any, Tuple, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.svm import LinearSVC


class RiskAnalyzer:
    """Classifies contract clause risk using TF-IDF and cosine similarity.

    Maintains a comprehensive dictionary of risk patterns organized by
    risk level and category. Uses scikit-learn's TfidfVectorizer to
    vectorize patterns and input clauses, then computes cosine similarity
    to find the closest matches and assign risk scores.

    Attributes:
        SIMILARITY_THRESHOLD: Minimum cosine similarity to consider a match.
        HIGH_RISK_FLOOR: Minimum score assigned to high-risk matches.
        MEDIUM_RISK_FLOOR: Minimum score assigned to medium-risk matches.
        LOW_RISK_FLOOR: Minimum score assigned to low-risk matches.
        UNMATCHED_BASELINE: Score range for clauses with no pattern match.
    """

    SIMILARITY_THRESHOLD: float = 0.3
    HIGH_RISK_FLOOR: int = 70
    MEDIUM_RISK_FLOOR: int = 40
    LOW_RISK_FLOOR: int = 15
    UNMATCHED_BASELINE: Tuple[int, int] = (10, 25)

    def __init__(self) -> None:
        """Initialize the analyzer with risk patterns and build the TF-IDF-based classifier."""
        self.risk_patterns: Dict[str, Dict[str, List[str]]] = self._define_risk_patterns()
        self._pattern_list: List[Dict[str, str]] = []
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._pattern_vectors = None
        self._classifier = None
        self._classifier_pipeline = None
        self._build_vectorizer()
        self._build_classifier()

    def _define_risk_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Define comprehensive risk patterns organized by level and category.

        Returns:
            Nested dict: risk_level -> category_name -> list of pattern strings.
        """
        return {
            'high': {
                'Indemnification': [
                    'shall indemnify and hold harmless',
                    'indemnify defend and hold harmless',
                    'full indemnification',
                    'indemnify against all claims losses and damages',
                    'bear all costs of indemnification',
                    'unconditional indemnification obligation',
                    'indemnify from and against any and all liabilities',
                    'hold harmless from any claims',
                ],
                'Unlimited Liability': [
                    'unlimited liability',
                    'liable for all damages',
                    'no limitation on liability',
                    'liable without limitation',
                    'unlimited financial responsibility',
                    'no cap on liability',
                    'liability shall not be limited',
                    'responsible for all losses without limit',
                ],
                'Auto Renewal': [
                    'automatically renew',
                    'automatic renewal',
                    'shall automatically extend',
                    'renews unless terminated',
                    'auto-renew for successive periods',
                    'automatically renewed for additional terms',
                    'renewal without notice required',
                    'deemed renewed unless written notice',
                ],
                'Non-Compete': [
                    'non-compete',
                    'non-competition',
                    'shall not compete',
                    'restrictive covenant',
                    'covenant not to compete',
                    'refrain from competing',
                    'not engage in any competing business',
                    'non-compete obligation',
                    'prohibited from competing',
                    'competitive restriction',
                ],
                'IP Assignment': [
                    'assigns all intellectual property',
                    'work made for hire',
                    'all rights title and interest',
                    'hereby assigns',
                    'transfer of ownership',
                    'assign all patents copyrights and trademarks',
                    'intellectual property shall belong exclusively',
                    'irrevocable assignment of all IP rights',
                    'all inventions shall be the property of',
                    'transfer all intellectual property rights',
                ],
                'Unilateral Termination': [
                    'terminate at any time without cause',
                    'terminate without notice',
                    'sole discretion to terminate',
                    'terminate for convenience',
                    'may terminate immediately',
                    'right to terminate without reason',
                    'unilateral right to cancel',
                    'terminate this agreement at will',
                ],
                'Rights Waiver': [
                    'waive any and all claims',
                    'waiver of rights',
                    'release all claims',
                    'forever discharge',
                    'irrevocably waive',
                    'waive right to trial by jury',
                    'relinquish all rights',
                    'surrender any claim or cause of action',
                ],
                'Penalty Clauses': [
                    'liquidated damages',
                    'penalty for breach',
                    'shall pay penalty',
                    'punitive damages',
                    'penalty interest',
                    'financial penalty upon default',
                    'penalty equal to total contract value',
                    'damages in excess of actual losses',
                ],
                'Perpetual Terms': [
                    'perpetual license',
                    'irrevocable',
                    'survive termination indefinitely',
                    'in perpetuity',
                    'perpetual and irrevocable',
                    'rights that survive forever',
                    'obligations shall continue indefinitely',
                    'no expiration of obligations',
                ],
                'Data Rights': [
                    'unlimited right to use data',
                    'share data with third parties without consent',
                    'collect and sell personal data',
                    'unrestricted access to all user data',
                    'transfer personal information without limitation',
                    'use data for any purpose including commercial',
                    'right to monetize user data',
                    'data may be sold to advertisers',
                ],
            },
            'medium': {
                'Liability Caps': [
                    'limitation of liability',
                    'aggregate liability shall not exceed',
                    'cap on damages',
                    'liability limited to fees paid',
                    'maximum liability shall not exceed',
                    'total liability capped at',
                    'in no event shall liability exceed',
                    'damages shall be limited to direct damages',
                ],
                'Confidentiality': [
                    'confidential information',
                    'non-disclosure',
                    'proprietary information',
                    'trade secrets',
                    'confidentiality obligations',
                    'maintain strict confidence',
                    'not disclose without prior consent',
                    'confidential and proprietary materials',
                ],
                'Data Usage': [
                    'collect personal information',
                    'data processing',
                    'share information with partners',
                    'data retention',
                    'process personal data',
                    'data collection and storage',
                    'information may be shared with affiliates',
                    'retain data for business purposes',
                ],
                'Jurisdiction': [
                    'governing law',
                    'exclusive jurisdiction',
                    'venue shall be',
                    'dispute resolution',
                    'binding arbitration',
                    'subject to the laws of',
                    'courts of exclusive jurisdiction',
                    'disputes shall be resolved through arbitration',
                    'choice of forum',
                    'mandatory arbitration',
                ],
                'Force Majeure': [
                    'force majeure',
                    'act of god',
                    'beyond reasonable control',
                    'unforeseeable circumstances',
                    'events outside the control of the parties',
                    'natural disaster or civil unrest',
                    'excused from performance due to force majeure',
                    'pandemic epidemic or outbreak',
                ],
                'Assignment': [
                    'may assign this agreement',
                    'transfer obligations',
                    'delegate duties',
                    'novation',
                    'assign without consent',
                    'right to transfer this agreement',
                    'assignment of rights and obligations',
                    'assignee shall assume all obligations',
                ],
                'Warranty': [
                    'as is',
                    'without warranty',
                    'disclaimer of warranties',
                    'no representations',
                    'provided without any warranty express or implied',
                    'no warranty of merchantability',
                    'disclaimer of all implied warranties',
                    'as is where is condition',
                ],
                'Notice': [
                    'notice period',
                    'days written notice',
                    'prior written notice',
                    'notice shall be delivered',
                    'written notification required',
                    'notice by certified mail',
                    'advance written notice of termination',
                    'notice of intent to terminate',
                ],
                'Payment Terms': [
                    'late payment fee',
                    'interest on overdue',
                    'net 30',
                    'payment upon receipt',
                    'late fees and penalties',
                    'interest charged on overdue invoices',
                    'payment due within specified period',
                    'past due amounts accrue interest',
                ],
                'Scope Changes': [
                    'modify terms at any time',
                    'reserve the right to change',
                    'amend without notice',
                    'unilateral modification of terms',
                    'terms may be updated at discretion',
                    'right to revise these terms',
                    'amendments effective upon posting',
                    'changes to terms without prior notice',
                ],
            },
            'low': {
                'Mutual Terms': [
                    'mutual agreement',
                    'both parties agree',
                    'mutually agreed',
                    'by mutual written consent',
                    'jointly agreed upon terms',
                    'mutual obligations and responsibilities',
                    'reciprocal agreement between parties',
                    'agreed upon by both parties in writing',
                ],
                'Reasonable Standards': [
                    'reasonable efforts',
                    'commercially reasonable',
                    'reasonable notice',
                    'reasonable time',
                    'best reasonable efforts',
                    'commercially reasonable endeavors',
                    'within a reasonable timeframe',
                    'reasonable and customary practices',
                ],
                'Standard Boilerplate': [
                    'entire agreement',
                    'severability',
                    'counterparts',
                    'headings for convenience',
                    'this agreement constitutes the entire understanding',
                    'if any provision is found unenforceable',
                    'may be executed in counterparts',
                    'section headings are for reference only',
                ],
                'Written Consent': [
                    'prior written consent',
                    'written approval',
                    'signed by both parties',
                    'consent in writing',
                    'written authorization required',
                    'approval in writing from both parties',
                    'executed with written consent',
                    'requires written agreement of both parties',
                ],
                'Good Faith': [
                    'good faith',
                    'fair dealing',
                    'best efforts',
                    'good faith negotiations',
                    'act in good faith and fair dealing',
                    'parties shall deal fairly',
                    'exercise good faith in performance',
                    'best endeavors to fulfill obligations',
                ],
            },
        }

    def _build_vectorizer(self) -> None:
        """Build the TF-IDF vectorizer and pre-compute pattern vectors.

        Collects all pattern strings, fits the vectorizer, and transforms
        patterns into TF-IDF vectors for later similarity comparison.
        """
        self._pattern_list = []

        for level, categories in self.risk_patterns.items():
            for category, patterns in categories.items():
                for pattern_text in patterns:
                    self._pattern_list.append({
                        'text': pattern_text,
                        'level': level,
                        'category': category,
                    })

        all_texts = [p['text'] for p in self._pattern_list]

        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 3),
            max_features=5000,
            sublinear_tf=True,
        )
        self._pattern_vectors = self._vectorizer.fit_transform(all_texts)

    def _build_classifier(self) -> None:
        """Train a strong linear SVM classifier on the pattern library with data augmentation."""
        if not self._pattern_list:
            self._classifier_pipeline = None
            return

        # Define diverse legal sentence templates to augment the 206 short seed phrases
        templates = [
            "{}",
            "The agreement shall {}",
            "It is understood that both parties {}",
            "Under no circumstances should you {}",
            "We reserve the right to {}",
            "This clause will {}",
            "Please note that we might {}",
            "The contract is set to {}",
            "Nothing in this section shall prevent us to {}",
            "Subject to the terms, it will {}",
            "The company must {}",
            "Either party may request to {}",
            "Failure to {} shall constitute a material breach.",
            "The customer agrees to {}",
            "In case of default, the party shall {}",
        ]

        texts = []
        labels = []

        for entry in self._pattern_list:
            pattern_text = entry['text']
            level = entry['level']
            for temp in templates:
                texts.append(temp.format(pattern_text))
                labels.append(level)

        self._classifier_pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                lowercase=True,
                stop_words='english',
                ngram_range=(1, 2),
                max_features=5000, # Increased max features to accommodate augmented vocabulary
                sublinear_tf=True,
            )),
            ('clf', LinearSVC(class_weight='balanced', random_state=42, C=2.0, loss='hinge', max_iter=5000, dual='auto')),
        ])
        self._classifier_pipeline.fit(texts, labels)

    def analyze(self, clause_text: str) -> Dict[str, Any]:
        """Analyze a single clause for risk.

        Vectorizes the clause text, computes cosine similarity against
        all stored patterns, and returns the risk assessment.

        Args:
            clause_text: The text of the clause to analyze.

        Returns:
            A dict containing:
                - risk_level (str): 'high', 'medium', or 'low'.
                - risk_score (int): 0-100 indicating severity.
                - risk_categories (list[str]): Matched category names.
                - keywords (list[str]): Highlighted keywords found.
                - top_matches (list[dict]): Top pattern matches with
                  'pattern', 'category', 'level', and 'similarity' keys.
        """
        if not clause_text or not clause_text.strip():
            return self._empty_result()

        try:
            clause_vector = self._vectorizer.transform([clause_text.lower()])
        except Exception:
            return self._empty_result()

        similarities = cosine_similarity(clause_vector, self._pattern_vectors).flatten()

        predicted_level = self._predict_level(clause_text)

        # Gather all matches above threshold
        matches: List[Dict[str, Any]] = []
        for idx, sim in enumerate(similarities):
            if sim >= self.SIMILARITY_THRESHOLD:
                p = self._pattern_list[idx]
                matches.append({
                    'pattern': p['text'],
                    'category': p['category'],
                    'level': p['level'],
                    'similarity': round(float(sim), 4),
                })

        # Sort by similarity descending
        matches.sort(key=lambda m: m['similarity'], reverse=True)

        # Determine risk level and score
        risk_level, risk_score = self._compute_risk(matches, similarities, predicted_level)

        # Collect unique categories
        risk_categories = list(dict.fromkeys(m['category'] for m in matches))

        # Extract matched keywords
        keywords = self._extract_keywords(clause_text, matches)

        # Limit top_matches to top 5 for conciseness
        top_matches = matches[:5]

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_categories': risk_categories,
            'keywords': keywords,
            'top_matches': top_matches,
        }

    def analyze_batch(self, clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze multiple clauses efficiently.

        Processes a batch of clause dicts (each must have a 'text' key)
        and returns analysis results in the same order.

        Args:
            clauses: List of clause dicts, each containing at least a 'text' key.

        Returns:
            List of risk analysis result dicts, one per input clause.
        """
        results = []
        for clause in clauses:
            text = clause.get('text', '') if isinstance(clause, dict) else str(clause)
            analysis = self.analyze(text)
            results.append(analysis)
        return results

    def _predict_level(self, clause_text: str) -> Optional[str]:
        """Use the trained classifier to predict a risk level for a clause."""
        if self._classifier_pipeline is None:
            return None

        try:
            return self._classifier_pipeline.predict([clause_text])[0]
        except Exception:
            return None

    def _compute_risk(
        self,
        matches: List[Dict[str, Any]],
        similarities: np.ndarray,
        predicted_level: Optional[str] = None,
    ) -> Tuple[str, int]:
        """Compute the overall risk level and score from pattern matches.

        Scoring logic:
        - If any match has similarity >= threshold with a high-risk pattern -> high risk.
        - If any match has similarity >= threshold with a medium-risk pattern -> medium risk.
        - If only low-risk matches or no matches -> low risk.
        - Score is calibrated from the maximum similarity value.

        Args:
            matches: Filtered list of pattern matches above threshold.
            similarities: Full similarity array for all patterns.

        Returns:
            Tuple of (risk_level, risk_score).
        """
        if not matches:
            # No significant matches — assign a low baseline score
            max_sim = float(np.max(similarities)) if len(similarities) > 0 else 0.0
            baseline = int(self.UNMATCHED_BASELINE[0] + max_sim * (
                self.UNMATCHED_BASELINE[1] - self.UNMATCHED_BASELINE[0]
            ))
            if predicted_level in {'high', 'medium', 'low'}:
                return predicted_level, max(self.UNMATCHED_BASELINE[0], min(self.UNMATCHED_BASELINE[1], baseline))
            return 'low', max(self.UNMATCHED_BASELINE[0], min(self.UNMATCHED_BASELINE[1], baseline))

        max_similarity = matches[0]['similarity']

        # Check if any high-risk pattern matched
        high_matches = [m for m in matches if m['level'] == 'high']
        medium_matches = [m for m in matches if m['level'] == 'medium']

        if high_matches:
            best_high = high_matches[0]['similarity']
            raw_score = min(100, int(best_high * 120))
            score = max(self.HIGH_RISK_FLOOR, raw_score)
            return 'high', score
        elif medium_matches:
            best_medium = medium_matches[0]['similarity']
            raw_score = min(100, int(best_medium * 120))
            score = max(self.MEDIUM_RISK_FLOOR, raw_score)
            return 'medium', score
        else:
            # Only low-risk matches
            raw_score = min(100, int(max_similarity * 120))
            score = max(self.LOW_RISK_FLOOR, min(39, raw_score))
            if predicted_level in {'high', 'medium', 'low'} and predicted_level != 'low':
                return predicted_level, max(self.LOW_RISK_FLOOR, min(100, score + 10))
            return 'low', score

    def _extract_keywords(
        self,
        clause_text: str,
        matches: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract notable keywords from the clause based on matched patterns.

        Looks for individual words and bigrams from matched pattern texts
        that also appear in the clause text.

        Args:
            clause_text: The original clause text.
            matches: List of matched patterns.

        Returns:
            Deduplicated list of keyword strings found in the clause.
        """
        clause_lower = clause_text.lower()
        keywords: List[str] = []
        seen: set = set()

        for match in matches:
            pattern_words = match['pattern'].lower().split()
            # Check individual words (skip very common ones)
            skip_words = {
                'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'for',
                'is', 'are', 'was', 'were', 'be', 'been', 'shall', 'may',
                'will', 'with', 'at', 'by', 'from', 'on', 'not', 'any',
                'all', 'this', 'that', 'it', 'its', 'no', 'has', 'have',
            }
            for word in pattern_words:
                if word not in skip_words and word in clause_lower and word not in seen:
                    seen.add(word)
                    keywords.append(word)

            # Check bigrams from the pattern
            for i in range(len(pattern_words) - 1):
                bigram = f'{pattern_words[i]} {pattern_words[i + 1]}'
                if bigram in clause_lower and bigram not in seen:
                    seen.add(bigram)
                    keywords.append(bigram)

        return keywords

    def _empty_result(self) -> Dict[str, Any]:
        """Return a default empty result for invalid or empty input.

        Returns:
            A risk result dict with low risk and zero score.
        """
        return {
            'risk_level': 'low',
            'risk_score': 0,
            'risk_categories': [],
            'keywords': [],
            'top_matches': [],
        }
