"""
LLM Explainer Module for ClauseGuard Engine.

Provides the LLMExplainer class that uses Google Gemini API to generate
plain-English explanations of contract clauses. Includes a comprehensive
template-based fallback for when the API is unavailable.
"""

import json
from typing import Dict, List, Optional, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class LLMExplainer:
    """Explains contract clauses in plain English using Google Gemini API.

    When the Gemini API is configured and available, sends prompts to
    the LLM for context-aware explanations. Falls back to comprehensive
    template-based explanations when the API is unavailable or errors occur.

    Attributes:
        FALLBACK_TEMPLATES: Dict mapping risk categories to template explanations.
    """

    FALLBACK_TEMPLATES: Dict[str, Dict[str, str]] = {
        # ── High Risk Categories ──────────────────────────────────────
        'Indemnification': {
            'what_it_means': (
                'This clause requires you to cover all costs and losses if something '
                'goes wrong, even if it\'s not entirely your fault.'
            ),
            'why_risky': (
                'You could be on the hook for expensive legal fees, damages, and '
                'other costs that could far exceed the value of the contract.'
            ),
            'what_to_do': (
                'Try to negotiate mutual indemnification (both parties share the risk) '
                'and cap the maximum amount you could owe.'
            ),
        },
        'Unlimited Liability': {
            'what_it_means': (
                'This clause means there is no cap on what you could be required '
                'to pay if something goes wrong under this contract.'
            ),
            'why_risky': (
                'Without a liability limit, a single issue could result in financial '
                'exposure that far exceeds the contract\'s value or your ability to pay.'
            ),
            'what_to_do': (
                'Negotiate a liability cap, ideally tied to the total fees paid under '
                'the contract, and exclude consequential or indirect damages.'
            ),
        },
        'Auto Renewal': {
            'what_it_means': (
                'This clause allows the contract to renew itself automatically unless '
                'you take specific action to cancel it before a deadline.'
            ),
            'why_risky': (
                'You could be locked into another term and continued payments if '
                'you miss the cancellation window, which is easy to overlook.'
            ),
            'what_to_do': (
                'Set a calendar reminder well before the renewal deadline, and '
                'negotiate a shorter notice period or a switch to manual renewal.'
            ),
        },
        'Non-Compete': {
            'what_it_means': (
                'This clause restricts you from working in a similar business or '
                'with competitors for a certain period and/or within a geographic area.'
            ),
            'why_risky': (
                'It could limit your career options and ability to earn a living, '
                'especially if the scope, duration, or geography is too broad.'
            ),
            'what_to_do': (
                'Narrow the scope to specific competitors, shorten the duration, '
                'limit the geographic area, and ensure compensation during the restricted period.'
            ),
        },
        'IP Assignment': {
            'what_it_means': (
                'This clause transfers ownership of intellectual property you create '
                'to the other party, potentially including work outside the project scope.'
            ),
            'why_risky': (
                'You could lose rights to your own creations, inventions, or work '
                'product, including things developed on your own time.'
            ),
            'what_to_do': (
                'Limit the assignment to work specifically created for this contract, '
                'exclude pre-existing IP, and retain a license to use the work.'
            ),
        },
        'Unilateral Termination': {
            'what_it_means': (
                'This clause gives one party the right to end the contract at any time '
                'without needing a reason or providing much notice.'
            ),
            'why_risky': (
                'You could lose the contract unexpectedly, leaving you without revenue '
                'or resources you were counting on.'
            ),
            'what_to_do': (
                'Negotiate for mutual termination rights, require a reasonable notice '
                'period (e.g., 30-90 days), and include compensation for early termination.'
            ),
        },
        'Rights Waiver': {
            'what_it_means': (
                'This clause asks you to give up your legal rights, such as the right '
                'to sue or make claims against the other party.'
            ),
            'why_risky': (
                'Once you waive your rights, you may have no legal recourse if the '
                'other party acts unfairly or causes you harm.'
            ),
            'what_to_do': (
                'Resist blanket waivers. If a waiver is necessary, limit it to specific '
                'claims and ensure it doesn\'t cover fraud, negligence, or bad faith.'
            ),
        },
        'Penalty Clauses': {
            'what_it_means': (
                'This clause imposes financial penalties if you fail to meet certain '
                'obligations, sometimes exceeding the actual damages caused.'
            ),
            'why_risky': (
                'Penalties can be disproportionately large compared to the actual harm, '
                'creating significant financial exposure for minor breaches.'
            ),
            'what_to_do': (
                'Ensure penalties are proportionate to actual damages, negotiate caps on '
                'penalty amounts, and include cure periods to fix issues before penalties apply.'
            ),
        },
        'Perpetual Terms': {
            'what_it_means': (
                'This clause creates obligations or grants rights that last forever, '
                'even after the contract ends.'
            ),
            'why_risky': (
                'You could be bound by obligations indefinitely with no way to exit, '
                'or permanently lose rights you granted during the contract.'
            ),
            'what_to_do': (
                'Set reasonable time limits on post-termination obligations, and ensure '
                'perpetual rights are limited in scope and mutually beneficial.'
            ),
        },
        'Data Rights': {
            'what_it_means': (
                'This clause grants the other party broad rights to collect, use, '
                'share, or sell your data, possibly without your explicit consent.'
            ),
            'why_risky': (
                'Your personal or business data could be monetized, shared with '
                'unknown third parties, or used in ways you didn\'t anticipate.'
            ),
            'what_to_do': (
                'Require explicit consent for data sharing, limit data use to the '
                'contract\'s purpose, and demand data deletion upon termination.'
            ),
        },
        # ── Medium Risk Categories ────────────────────────────────────
        'Liability Caps': {
            'what_it_means': (
                'This clause sets a maximum limit on how much one party can be held '
                'financially responsible for under the contract.'
            ),
            'why_risky': (
                'If the cap is too low, you may not be fully compensated for damages. '
                'If too high, you could face excessive exposure.'
            ),
            'what_to_do': (
                'Ensure the cap is proportional to the contract value and that it '
                'doesn\'t exclude important damage types like data breaches.'
            ),
        },
        'Confidentiality': {
            'what_it_means': (
                'This clause requires you to keep certain information private and not '
                'share it with outsiders.'
            ),
            'why_risky': (
                'Overly broad confidentiality terms can restrict what you share even '
                'with your own advisors, and violations can trigger penalties.'
            ),
            'what_to_do': (
                'Ensure confidentiality is mutual, clearly define what\'s confidential, '
                'set a reasonable time limit, and include standard exceptions.'
            ),
        },
        'Data Usage': {
            'what_it_means': (
                'This clause describes how the other party collects, stores, and '
                'processes your personal or business data.'
            ),
            'why_risky': (
                'Your data may be retained longer than necessary, shared with partners, '
                'or used in ways that could affect your privacy.'
            ),
            'what_to_do': (
                'Request clear data retention limits, opt-out mechanisms, and '
                'ensure compliance with relevant privacy regulations.'
            ),
        },
        'Jurisdiction': {
            'what_it_means': (
                'This clause determines which location\'s laws apply and where any '
                'legal disputes must be resolved.'
            ),
            'why_risky': (
                'If the jurisdiction is far away or in an unfamiliar legal system, '
                'resolving disputes becomes more expensive and complicated.'
            ),
            'what_to_do': (
                'Negotiate for a neutral or convenient jurisdiction, and consider '
                'whether arbitration might be more practical than court litigation.'
            ),
        },
        'Force Majeure': {
            'what_it_means': (
                'This clause excuses one or both parties from obligations when '
                'extraordinary events (like natural disasters) prevent performance.'
            ),
            'why_risky': (
                'If the clause is too broad, the other party could use minor disruptions '
                'to avoid their responsibilities under the contract.'
            ),
            'what_to_do': (
                'Define specific triggering events, set time limits on force majeure '
                'claims, and include termination rights if delays are excessive.'
            ),
        },
        'Assignment': {
            'what_it_means': (
                'This clause allows one party to transfer the contract or its '
                'obligations to another entity.'
            ),
            'why_risky': (
                'You could end up working with a completely different (and possibly '
                'less reliable) party than the one you originally agreed to.'
            ),
            'what_to_do': (
                'Require written consent before any assignment, and include the right '
                'to terminate if the contract is assigned to an unacceptable party.'
            ),
        },
        'Warranty': {
            'what_it_means': (
                'This clause disclaims guarantees about the quality, performance, '
                'or fitness of the product or service being provided.'
            ),
            'why_risky': (
                'Without warranties, you have limited recourse if the product or '
                'service doesn\'t work as expected or causes problems.'
            ),
            'what_to_do': (
                'Push for basic warranties covering functionality and performance, '
                'and negotiate a warranty period with clear remedies for defects.'
            ),
        },
        'Notice': {
            'what_it_means': (
                'This clause specifies how and when parties must communicate important '
                'changes, like termination or breach notifications.'
            ),
            'why_risky': (
                'Strict notice requirements could mean you lose rights if you notify '
                'even slightly late or using the wrong method.'
            ),
            'what_to_do': (
                'Ensure notice periods are reasonable, allow multiple delivery methods '
                '(email plus mail), and clarify when notice is considered received.'
            ),
        },
        'Payment Terms': {
            'what_it_means': (
                'This clause defines when and how payments are due, and what happens '
                'if payments are late.'
            ),
            'why_risky': (
                'Tight payment deadlines and high late fees can create cash flow '
                'problems, especially if invoicing or approval processes are slow.'
            ),
            'what_to_do': (
                'Negotiate reasonable payment windows (net 30 or 45), cap late fees, '
                'and ensure invoicing triggers are clear and fair.'
            ),
        },
        'Scope Changes': {
            'what_it_means': (
                'This clause allows one party to modify the terms or scope of the '
                'agreement, sometimes without the other party\'s approval.'
            ),
            'why_risky': (
                'The other party could change prices, deliverables, or obligations '
                'in ways that disadvantage you, with little recourse.'
            ),
            'what_to_do': (
                'Require mutual written consent for all changes, include a right '
                'to terminate if changes are unacceptable, and set change-order procedures.'
            ),
        },
        # ── Low Risk Categories ───────────────────────────────────────
        'Mutual Terms': {
            'what_it_means': (
                'This clause establishes obligations or benefits that apply equally '
                'to both parties, creating a balanced arrangement.'
            ),
            'why_risky': (
                'Generally low risk, but verify that "mutual" truly means equal '
                'obligations and that one side isn\'t subtly favored.'
            ),
            'what_to_do': (
                'Review the details to confirm both parties have genuinely equal '
                'rights and obligations under this provision.'
            ),
        },
        'Reasonable Standards': {
            'what_it_means': (
                'This clause uses flexible language like "reasonable efforts" to set '
                'expectations without requiring absolute guarantees.'
            ),
            'why_risky': (
                'The term "reasonable" can be subjective and lead to disagreements '
                'about whether obligations were properly met.'
            ),
            'what_to_do': (
                'Consider defining specific metrics or benchmarks for what constitutes '
                '"reasonable" performance in your particular context.'
            ),
        },
        'Standard Boilerplate': {
            'what_it_means': (
                'This is standard contract language covering administrative matters like '
                'how the agreement is structured and interpreted.'
            ),
            'why_risky': (
                'While generally harmless, boilerplate can occasionally contain clauses '
                'that limit your rights if not read carefully.'
            ),
            'what_to_do': (
                'Still worth reading through, but these clauses are typically low risk '
                'and standard across most contracts.'
            ),
        },
        'Written Consent': {
            'what_it_means': (
                'This clause requires changes or actions to be approved in writing, '
                'which protects both parties from unauthorized modifications.'
            ),
            'why_risky': (
                'Written consent requirements are generally protective, but they can '
                'slow down decision-making if applied too broadly.'
            ),
            'what_to_do': (
                'This is generally a positive provision. Ensure it applies to important '
                'decisions and that the approval process is practical.'
            ),
        },
        'Good Faith': {
            'what_it_means': (
                'This clause requires both parties to act honestly and fairly in '
                'their dealings with each other.'
            ),
            'why_risky': (
                'Good faith is a positive principle, but it\'s subjective and can be '
                'difficult to enforce if a dispute arises.'
            ),
            'what_to_do': (
                'This is a positive provision. Consider supplementing it with specific '
                'performance metrics or dispute resolution procedures.'
            ),
        },
    }

    # Default templates for when no specific category matches
    _DEFAULT_TEMPLATES: Dict[str, Dict[str, str]] = {
        'high': {
            'what_it_means': (
                'This clause contains language that could create significant '
                'obligations or risks for you.'
            ),
            'why_risky': (
                'High-risk clauses can lead to unexpected financial exposure, '
                'loss of rights, or binding commitments that are hard to exit.'
            ),
            'what_to_do': (
                'Have a lawyer review this clause carefully before signing. '
                'Consider negotiating more favorable terms or adding protections.'
            ),
        },
        'medium': {
            'what_it_means': (
                'This clause contains terms that deserve attention but are '
                'commonly found in contracts of this type.'
            ),
            'why_risky': (
                'While not immediately dangerous, these terms could become '
                'problematic depending on how they\'re enforced or interpreted.'
            ),
            'what_to_do': (
                'Review the specific terms and consider whether they align with '
                'your expectations. Clarify any ambiguous language.'
            ),
        },
        'low': {
            'what_it_means': (
                'This clause contains standard contract language that establishes '
                'basic terms of the agreement.'
            ),
            'why_risky': (
                'Low-risk clauses are generally balanced and fair, posing minimal '
                'concern in most situations.'
            ),
            'what_to_do': (
                'Read through for completeness, but this clause is generally '
                'acceptable as written.'
            ),
        },
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize the explainer, optionally configuring the Gemini API.

        Args:
            api_key: Google Gemini API key. If provided, the API is configured
                     immediately. If None, only fallback explanations are available.
        """
        self.api_key: Optional[str] = api_key
        self.model: Optional[Any] = None
        if api_key:
            self.configure(api_key)

    def configure(self, api_key: str) -> None:
        """Configure the Google Gemini API with the provided key.

        Args:
            api_key: A valid Google Gemini API key.

        Raises:
            RuntimeError: If the google-generativeai package is not installed.
        """
        if genai is None:
            raise RuntimeError(
                'google-generativeai package is required for LLM explanations. '
                'Install it with: pip install google-generativeai'
            )
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def is_available(self) -> bool:
        """Check whether the LLM model is configured and ready.

        Returns:
            True if the Gemini model is available, False otherwise.
        """
        return self.model is not None

    def explain(
        self,
        clause_text: str,
        risk_level: str,
        risk_categories: List[str],
    ) -> Dict[str, str]:
        """Generate a plain-English explanation of a contract clause.

        Uses the Gemini API if available, otherwise falls back to
        template-based explanations.

        Args:
            clause_text: The text of the clause to explain.
            risk_level: The risk level ('high', 'medium', or 'low').
            risk_categories: List of matched risk category names.

        Returns:
            A dict with keys:
                - what_it_means (str): Plain English explanation.
                - why_risky (str): Why it could be problematic.
                - what_to_do (str): Actionable suggestion.
                - source (str): 'llm' or 'fallback'.
        """
        if not self.is_available():
            return self._fallback_explanation(clause_text, risk_level, risk_categories)

        prompt = self._build_prompt(clause_text, risk_level, risk_categories)

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Strip markdown code fences if present
            if text.startswith('```'):
                text = text.split('\n', 1)[1]
                text = text.rsplit('```', 1)[0].strip()

            result = json.loads(text)

            # Validate expected keys
            required_keys = {'what_it_means', 'why_risky', 'what_to_do'}
            if not required_keys.issubset(result.keys()):
                raise ValueError('LLM response missing required keys')

            result['source'] = 'llm'
            return result

        except Exception:
            return self._fallback_explanation(clause_text, risk_level, risk_categories)

    def explain_batch(
        self,
        clauses: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Generate explanations for multiple clauses.

        Each clause dict should have 'text', 'risk_level', and
        'risk_categories' keys.

        Args:
            clauses: List of clause dicts to explain.

        Returns:
            List of explanation dicts, one per input clause.
        """
        results = []
        for clause in clauses:
            explanation = self.explain(
                clause_text=clause.get('text', ''),
                risk_level=clause.get('risk_level', 'low'),
                risk_categories=clause.get('risk_categories', []),
            )
            results.append(explanation)
        return results

    def _build_prompt(
        self,
        clause_text: str,
        risk_level: str,
        risk_categories: List[str],
    ) -> str:
        """Build the prompt for the Gemini API.

        Args:
            clause_text: The clause text.
            risk_level: The risk level string.
            risk_categories: List of category names.

        Returns:
            The formatted prompt string.
        """
        categories_str = ', '.join(risk_categories) if risk_categories else 'General'

        return f"""You are a legal document analyst helping a non-lawyer understand contract clauses.

Analyze this clause and explain it in simple, everyday English. Be concise and clear.

Clause: \"{clause_text}\"

Risk Level: {risk_level}
Risk Categories: {categories_str}

Provide your response in this exact JSON format:
{{
    "what_it_means": "A 1-2 sentence plain English explanation of what this clause means.",
    "why_risky": "A 1-2 sentence explanation of why this could be problematic for you.",
    "what_to_do": "A 1-2 sentence actionable suggestion on what to negotiate or watch out for."
}}

Respond ONLY with the JSON, no other text."""

    def _fallback_explanation(
        self,
        clause_text: str,
        risk_level: str,
        risk_categories: List[str],
    ) -> Dict[str, str]:
        """Generate a template-based explanation when the LLM is unavailable.

        Looks up the first matching category in FALLBACK_TEMPLATES. If no
        category matches, uses the default template for the given risk level.

        Args:
            clause_text: The clause text (used for context but not in templates).
            risk_level: The risk level string.
            risk_categories: List of matched category names.

        Returns:
            A dict with what_it_means, why_risky, what_to_do, and source keys.
        """
        # Try to find a template for the first matching category
        for category in risk_categories:
            if category in self.FALLBACK_TEMPLATES:
                template = self.FALLBACK_TEMPLATES[category]
                return {
                    'what_it_means': template['what_it_means'],
                    'why_risky': template['why_risky'],
                    'what_to_do': template['what_to_do'],
                    'source': 'fallback',
                }

        # Use default template for the risk level
        level_key = risk_level.lower() if risk_level.lower() in self._DEFAULT_TEMPLATES else 'low'
        template = self._DEFAULT_TEMPLATES[level_key]
        return {
            'what_it_means': template['what_it_means'],
            'why_risky': template['why_risky'],
            'what_to_do': template['what_to_do'],
            'source': 'fallback',
        }

    def answer_question(self, document_text: str, question: str) -> str:
        """Answer a user's question based on the document context.
        
        Args:
            document_text: The full text of the uploaded document.
            question: The user's query.
            
        Returns:
            The LLM's response as a plain text string.
        """
        if not self.is_available():
            return "An API key is required to use the Document Q&A feature. Please configure your Gemini API Key in the Settings."
            
        # Truncate document text if it's too long (rough token protection for Gemini 2.0 Flash)
        # 1 char ~ 0.25 tokens. 100k chars ~ 25k tokens (well within 1M context limit)
        max_chars = 150000 
        if len(document_text) > max_chars:
            document_text = document_text[:max_chars] + "\n...[Document Truncated]..."
            
        prompt = f"""You are a highly capable legal document assistant. 
Your task is to answer the user's question accurately based ONLY on the provided document text. 
If the answer is not in the document, explicitly state that you cannot find it in the provided text.
Do not invent information. Be concise, clear, and professional.

DOCUMENT TEXT:
\"\"\"
{document_text}
\"\"\"

USER QUESTION: {question}

ANSWER:"""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Sorry, I encountered an error while answering your question: {str(e)}"
