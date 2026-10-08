"""
LLM Explainer Module for ClauseGuard Engine.

Provides the LLMExplainer class:
  - explain()         → Groq + Llama 3.3 70B  (free, best plain-English output)
  - answer_question() → Google Gemini 2.0 Flash (large context window for full docs)

Falls back to template explanations when no API key is configured.
"""

import json
import re
from typing import Dict, List, Optional, Any

# Groq (for explain feature — Llama 3.3 70B)
try:
    from groq import Groq as GroqClient
except ImportError:
    GroqClient = None

# Gemini (for document Q&A — needs 1M token context)
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
                'You agree to cover all legal costs, damages, and settlements if the other party gets sued because of your work or breach.'
            ),
            'why_risky': (
                'You could owe large sums of money for legal fees and damages, even for issues outside your control.'
            ),
            'what_to_do': (
                'Request mutual indemnification and cap your maximum financial liability to the total contract value.'
            ),
        },
        'Unlimited Liability': {
            'what_it_means': (
                'There is no dollar cap on how much money you could be required to pay if a dispute or breach occurs.'
            ),
            'why_risky': (
                'A single breach or lawsuit could expose your business or personal finances to unlimited financial claims.'
            ),
            'what_to_do': (
                'Insist on inserting a strict monetary liability cap equal to the fees paid under the contract.'
            ),
        },
        'Auto Renewal': {
            'what_it_means': (
                'The agreement automatically renews for another full term unless you submit written cancellation before the notice deadline.'
            ),
            'why_risky': (
                'If you miss the specific cancellation window, you are locked into paying for another full contract term.'
            ),
            'what_to_do': (
                'Set a calendar reminder 60 days before renewal, or require explicit manual consent for renewal.'
            ),
        },
        'Non-Compete': {
            'what_it_means': (
                'You are prohibited from offering similar services or working with competing businesses during and after this contract.'
            ),
            'why_risky': (
                'It restricts your ability to gain new clients, take jobs, or earn income in your core industry.'
            ),
            'what_to_do': (
                'Narrow the restriction to specific named competitors and shorten the post-termination timeframe.'
            ),
        },
        'IP Assignment': {
            'what_it_means': (
                'All work product, inventions, and ideas created during the contract belong exclusively to the other party.'
            ),
            'why_risky': (
                'You may inadvertently transfer ownership of your pre-existing tools, code, or independent inventions.'
            ),
            'what_to_do': (
                'Explicitly exclude pre-existing intellectual property and limit assignment strictly to paid deliverables.'
            ),
        },
        'Unilateral Termination': {
            'what_it_means': (
                'The other party can terminate the agreement at any time without providing a reason.'
            ),
            'why_risky': (
                'You could suddenly lose expected revenue and ongoing business without adequate notice.'
            ),
            'what_to_do': (
                'Require mutual termination rights with a mandatory 30-day or 60-day written notice period.'
            ),
        },
        'Rights Waiver': {
            'what_it_means': (
                'You give up specific legal protections, such as the right to file claims or join class-action lawsuits.'
            ),
            'why_risky': (
                'If the other party breaches the contract or acts unfairly, your legal options to recover damages are severely restricted.'
            ),
            'what_to_do': (
                'Remove broad waivers so you maintain standard legal rights and statutory protections.'
            ),
        },
        'Penalty Clauses': {
            'what_it_means': (
                'Fixed financial fines are imposed automatically if you miss deadlines or break contract rules.'
            ),
            'why_risky': (
                'Penalties may be disproportionately large compared to any actual financial harm caused.'
            ),
            'what_to_do': (
                'Replace fixed penalty amounts with actual proven damages and include a cure period before fines apply.'
            ),
        },
        'Perpetual Terms': {
            'what_it_means': (
                'Specific contractual obligations continue indefinitely even after the project or contract ends.'
            ),
            'why_risky': (
                'You remain legally bound by restrictions forever with no expiration date.'
            ),
            'what_to_do': (
                'Add reasonable time limits (such as 1 to 2 years) to all post-termination obligations.'
            ),
        },
        'Data Rights': {
            'what_it_means': (
                'The other party receives broad permission to collect, analyze, share, or monetize your data.'
            ),
            'why_risky': (
                'Your confidential business data or user information could be shared with third parties without control.'
            ),
            'what_to_do': (
                'Restrict data usage strictly to contract performance and require complete data deletion upon termination.'
            ),
        },
        # ── Medium Risk Categories ────────────────────────────────────
        'Liability Caps': {
            'what_it_means': (
                'Specifies the maximum total financial payout one party can claim if a dispute arises.'
            ),
            'why_risky': (
                'If the cap set for the other party is too low, you cannot recover full losses if they cause major damage.'
            ),
            'what_to_do': (
                'Ensure the liability cap is balanced and proportional to the potential financial risk.'
            ),
        },
        'Confidentiality': {
            'what_it_means': (
                'Requires both parties to keep proprietary business information and trade secrets private.'
            ),
            'why_risky': (
                'Overly broad definitions can make standard business operations or sharing info with advisors a technical breach.'
            ),
            'what_to_do': (
                'Ensure confidentiality obligations are mutual and include standard legal exceptions.'
            ),
        },
        'Data Usage': {
            'what_it_means': (
                'Defines how your personal or corporate data is stored, processed, and maintained.'
            ),
            'why_risky': (
                'Unclear retention rules could lead to indefinite data storage or unauthorized secondary usage.'
            ),
            'what_to_do': (
                'Specify strict security standards, clear usage limits, and mandatory data return or destruction.'
            ),
        },
        'Jurisdiction': {
            'what_it_means': (
                'Establishes which specific state or country laws govern the agreement and where lawsuits must be filed.'
            ),
            'why_risky': (
                'If legal disputes must be resolved in a distant location, defending your rights becomes costly and inconvenient.'
            ),
            'what_to_do': (
                'Negotiate to use your local jurisdiction or a mutually agreed neutral location.'
            ),
        },
        'Force Majeure': {
            'what_it_means': (
                'Excuses contract performance when unforeseeable extreme events like natural disasters occur.'
            ),
            'why_risky': (
                'Broadly worded clauses could allow the other party to delay work or payments for minor disruptions.'
            ),
            'what_to_do': (
                'Ensure the definition covers only genuine uncontrollable catastrophes and requires prompt notice.'
            ),
        },
        'Assignment': {
            'what_it_means': (
                'Controls whether a party can transfer its rights or obligations under the contract to another entity.'
            ),
            'why_risky': (
                'Without restrictions, the contract could be reassigned to an unfamiliar or unvetted third party.'
            ),
            'what_to_do': (
                'Require prior written consent before any transfer or assignment of the agreement.'
            ),
        },
        'Warranty': {
            'what_it_means': (
                'Defines performance standards, fitness guarantees, and quality commitments for deliverables.'
            ),
            'why_risky': (
                'Disclaiming all warranties leaves you with no recourse if services or products fail to perform.'
            ),
            'what_to_do': (
                'Request express warranties for workmanship, compliance, and non-infringement.'
            ),
        },
        'Notice': {
            'what_it_means': (
                'Sets requirements for delivering official legal communications such as breaches or terminations.'
            ),
            'why_risky': (
                'Failing to follow strict notice channels (like physical mail only) can render official communications invalid.'
            ),
            'what_to_do': (
                'Include email as an approved method for delivering written notices.'
            ),
        },
        'Payment Terms': {
            'what_it_means': (
                'Outlines payment schedules, invoicing requirements, interest rates, and late fee penalties.'
            ),
            'why_risky': (
                'Extended payment windows (like Net 90) or steep late penalties can disrupt financial cash flow.'
            ),
            'what_to_do': (
                'Establish clear Net 30 payment terms and cap late interest charges at reasonable rates.'
            ),
        },
        'Scope Changes': {
            'what_it_means': (
                'Defines procedures for altering project specifications, deliverables, or timelines.'
            ),
            'why_risky': (
                'Informal changes can lead to scope creep and unpaid extra work.'
            ),
            'what_to_do': (
                'Require signed written change orders before initiating any modified work.'
            ),
        },
        # ── Low Risk Categories ───────────────────────────────────────
        'Mutual Terms': {
            'what_it_means': (
                'Applies equal rights and obligations to both parties to ensure fair terms.'
            ),
            'why_risky': (
                'Low risk when obligations are genuinely balanced.'
            ),
            'what_to_do': (
                'Verify that rights and remedies are truly reciprocal.'
            ),
        },
        'Reasonable Standards': {
            'what_it_means': (
                'Uses objective benchmarks like "commercially reasonable efforts" for performance expectations.'
            ),
            'why_risky': (
                'Subjective standards can occasionally lead to differing interpretations.'
            ),
            'what_to_do': (
                'Define clear measurable targets where possible.'
            ),
        },
        'Standard Boilerplate': {
            'what_it_means': (
                'Includes standard administrative terms regarding contract interpretation and enforcement.'
            ),
            'why_risky': (
                'Generally low risk standard legal language.'
            ),
            'what_to_do': (
                'Review briefly to confirm standard terms.'
            ),
        },
        'Written Consent': {
            'what_it_means': (
                'Requires official changes or waivers to be executed in writing.'
            ),
            'why_risky': (
                'Prevents unverified verbal modifications.'
            ),
            'what_to_do': (
                'Maintain this protective requirement.'
            ),
        },
        'Good Faith': {
            'what_it_means': (
                'Obligates both parties to act honestly and fairly in performing the contract.'
            ),
            'why_risky': (
                'Standard protective business principle.'
            ),
            'what_to_do': (
                'Retain as written.'
            ),
        },
    }

    # Default templates for when no specific category matches
    _DEFAULT_TEMPLATES: Dict[str, Dict[str, str]] = {
        'high': {
            'what_it_means': (
                'This section contains strict legal obligations that create significant financial or operational risk.'
            ),
            'why_risky': (
                'It could lead to unexpected financial exposure or loss of important legal rights.'
            ),
            'what_to_do': (
                'Have legal counsel review this provision and negotiate risk-limiting caps.'
            ),
        },
        'medium': {
            'what_it_means': (
                'This section outlines operational rules and standards governing performance and compliance.'
            ),
            'why_risky': (
                'Could cause disputes if obligations or timelines are not fully aligned.'
            ),
            'what_to_do': (
                'Review carefully to ensure all terms match your operational expectations.'
            ),
        },
        'low': {
            'what_it_means': (
                'Standard administrative provisions establishing basic contractual terms.'
            ),
            'why_risky': (
                'Low risk and standard across commercial agreements.'
            ),
            'what_to_do': (
                'Acceptable as written after standard review.'
            ),
        },
    }

    def __init__(
        self,
        api_key: Optional[str] = None,        # Gemini key (for Q&A chat)
        groq_api_key: Optional[str] = None,   # Groq key  (for plain-English explain)
    ) -> None:
        """Initialize the explainer."""
        self.api_key: Optional[str] = api_key
        self.groq_api_key: Optional[str] = groq_api_key

        self.model: Optional[Any] = None
        self._groq_client: Optional[Any] = None

        if api_key:
            self.configure(api_key)
        if groq_api_key:
            self.configure_groq(groq_api_key)

    def configure(self, api_key: str) -> None:
        """Configure Google Gemini for document Q&A."""
        if genai is None:
            raise RuntimeError('google-generativeai package is required.')
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def configure_groq(self, groq_api_key: str) -> None:
        """Configure Groq for plain-English clause explanations."""
        if GroqClient is None:
            raise RuntimeError('groq package is required. Install with: pip install groq')
        self.groq_api_key = groq_api_key
        self._groq_client = GroqClient(api_key=groq_api_key)

    def is_available(self) -> bool:
        """True if either Groq or Gemini is configured."""
        return self._groq_client is not None or self.model is not None

    def explain_available(self) -> bool:
        """True if Groq is configured."""
        return self._groq_client is not None

    def chat_available(self) -> bool:
        """True if Gemini is configured."""
        return self.model is not None

    def explain(
        self,
        clause_text: str,
        risk_level: str = 'low',
        risk_categories: Optional[List[str]] = None,
        lang: str = 'en',
    ) -> Dict[str, str]:
        """Generate an explanation of a contract clause in English or vernacular Indian languages (Hindi, Tamil, Telugu).

        Args:
            clause_text: Clause text.
            risk_level: Risk level string.
            risk_categories: Matched categories.
            lang: Language code ('en', 'hi', 'ta', 'te').

        Returns:
            Dict with what_it_means, why_risky, what_to_do, source.
        """
        if risk_categories is None:
            risk_categories = []

        # ── Try Groq first (fast, high quality) ─────────────────────────
        if self._groq_client is not None:
            try:
                return self._explain_with_groq(clause_text, risk_level, risk_categories, lang=lang)
            except Exception:
                pass  # fall through to Gemini or template

        # ── Try Gemini fallback ────────────────────────────────────────
        if self.model is not None:
            try:
                return self._explain_with_gemini(clause_text, risk_level, risk_categories, lang=lang)
            except Exception:
                pass

        # ── Template fallback (includes vernacular templates) ──────────
        return self._fallback_explanation(clause_text, risk_level, risk_categories, lang=lang)

    def _explain_with_groq(
        self,
        clause_text: str,
        risk_level: str,
        risk_categories: List[str],
        lang: str = 'en',
    ) -> Dict[str, str]:
        """Use Groq to generate a concise explanation in the target language."""
        prompt = self._build_prompt(clause_text, risk_level, risk_categories, lang=lang)
        lang_target_names = {
            'en': 'simple everyday English',
            'hi': 'Hindi (हिन्दी) in Devanagari script',
            'ta': 'Tamil (தமிழ்) in Tamil script',
            'te': 'Telugu (తెలుగు) in Telugu script',
        }
        target_name = lang_target_names.get(lang, 'simple everyday English')

        response = self._groq_client.chat.completions.create(
            model='groq/compound-mini',
            messages=[
                {
                    'role': 'system',
                    'content': (
                        f'You translate legal contract jargon into {target_name}. '
                        'RULES:\n'
                        '1. Write CONCISELY: exactly 2 short sentences per field (3-4 lines maximum per field).\n'
                        f'2. Translate legal jargon into everyday words in {target_name}.\n'
                        '3. Do NOT use real-life examples, analogies, or hypothetical stories.\n'
                        '4. State the direct legal obligations, risks, and negotiation steps clearly.\n'
                        'Respond ONLY with valid JSON — no markdown fences.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            temperature=0.2,
            max_tokens=500,
            response_format={'type': 'json_object'},
        )
        text = response.choices[0].message.content.strip()
        text = self._extract_json_payload(text)
        result = json.loads(text)

        required_keys = {'what_it_means', 'why_risky', 'what_to_do'}
        if not required_keys.issubset(result.keys()):
            raise ValueError('Groq response missing required keys')
        result['source'] = 'groq'
        return result

    def _explain_with_gemini(
        self,
        clause_text: str,
        risk_level: str,
        risk_categories: List[str],
        lang: str = 'en',
    ) -> Dict[str, str]:
        """Use Gemini to explain a clause in the target language."""
        prompt = self._build_prompt(clause_text, risk_level, risk_categories, lang=lang)
        response = self.model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            text = text.rsplit('```', 1)[0].strip()
        text = self._extract_json_payload(text)
        result = json.loads(text)
        required_keys = {'what_it_means', 'why_risky', 'what_to_do'}
        if not required_keys.issubset(result.keys()):
            raise ValueError('Gemini response missing required keys')
        if lang == 'en':
            for key in required_keys:
                if not self._is_english_text(result.get(key, '')):
                    raise ValueError(f'Non-English response for: {key}')
        result['source'] = 'llm'
        return result

    def explain_batch(
        self,
        clauses: List[Dict[str, Any]],
        lang: str = 'en',
    ) -> List[Dict[str, str]]:
        """Generate explanations for multiple clauses."""
        results = []
        for clause in clauses:
            explanation = self.explain(
                clause_text=clause.get('text', ''),
                risk_level=clause.get('risk_level', 'low'),
                risk_categories=clause.get('risk_categories', []),
                lang=lang,
            )
            results.append(explanation)
        return results

    def _build_prompt(
        self,
        clause_text: str,
        risk_level: str,
        risk_categories: List[str],
        lang: str = 'en',
    ) -> str:
        """Build the prompt for the LLM supporting Indic vernacular languages."""
        categories_str = ', '.join(risk_categories) if risk_categories else 'General'

        lang_instructions = {
            'en': 'plain English',
            'hi': 'plain vernacular Hindi (हिन्दी) in Devanagari script',
            'ta': 'plain vernacular Tamil (தமிழ்) in Tamil script',
            'te': 'plain vernacular Telugu (తెలుగు) in Telugu script',
        }
        lang_target = lang_instructions.get(lang, 'plain English')

        return f"""Read this contract clause and explain it in {lang_target}.
Constraints:
- Exactly 2 short sentences per field (3-4 lines total per field).
- Do NOT use real-life examples, analogies, or stories.
- Explain the legal meaning directly and simply in {lang_target}.

Contract Clause: \"{clause_text}\"
Risk Level: {risk_level}
Risk Type: {categories_str}

Respond in this exact JSON format:
{{
    "what_it_means": "2 short sentences explaining the clause directly in {lang_target}.",
    "why_risky": "2 short sentences explaining why this is dangerous and what financial harm it causes in {lang_target}.",
    "what_to_do": "2 short sentences listing specific negotiation changes in {lang_target}."
}}

Respond ONLY with the JSON."""

    def _extract_json_payload(self, text: str) -> str:
        """Extract the JSON payload from an LLM response that may contain extra text."""
        if not text or text.strip().startswith('{'):
            return text.strip()

        # Find the first and last JSON object delimiters
        first = text.find('{')
        last = text.rfind('}')
        if first == -1 or last == -1 or first >= last:
            raise ValueError('Could not find JSON payload in LLM response')
        return text[first:last+1]

    _COMMON_ENGLISH_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her',
        'she', 'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there',
        'their', 'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get',
        'which', 'go', 'me', 'when', 'make', 'can', 'like', 'time', 'no',
        'just', 'him', 'know', 'take', 'people', 'into', 'year', 'your',
        'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then',
        'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
        'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well',
        'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give',
        'day', 'most', 'us', 'are', 'is', 'was', 'were', 'been', 'has',
        'had', 'did', 'does', 'said', 'may', 'might', 'should', 'would',
        'could', 'must', 'shall', 'over', 'under', 'between', 'within',
        'without', 'per', 'however', 'because', 'while', 'than', 'through',
        'against', 'among', 'here', 'there', 'still', 'even', 'only',
        'every', 'each', 'both', 'these', 'those', 'more', 'most', 'many',
        'few', 'other', 'such', 'same', 'same', 'again', 'also', 'still',
        'yet', 'never', 'always', 'often', 'usually', 'rather', 'quite',
        'really', 'very', 'help', 'need', 'want', 'should', 'could', 'also'
    }

    _CONNECTOR_WORDS = {
        'the', 'and', 'or', 'because', 'if', 'but', 'so', 'for', 'with',
        'that', 'this', 'then', 'when', 'where', 'while', 'after', 'before',
        'although', 'however', 'unless'
    }

    def _is_english_text(self, text: str) -> bool:
        """Heuristic check whether the text appears to be English."""
        if not text or not text.strip():
            return False

        normalized = text.strip()
        ascii_chars = sum(1 for ch in normalized if ord(ch) < 128)
        if ascii_chars / max(1, len(normalized)) < 0.90:
            return False

        words = re.findall(r"[a-zA-Z']+", normalized)
        if len(words) < 4:
            return False

        clean_words = [w.lower().strip("'") for w in words if w.strip("'")]
        if not clean_words:
            return False

        common_word_count = sum(1 for w in clean_words if w in self._COMMON_ENGLISH_WORDS)
        if common_word_count < 2:
            return False

        if common_word_count / len(clean_words) < 0.30:
            return False

        if not any(w in self._CONNECTOR_WORDS for w in clean_words):
            return False

        vowel_word_ratio = sum(1 for w in clean_words if len(w) > 1 and re.search(r'[aeiou]', w)) / len(clean_words)
        if vowel_word_ratio < 0.55:
            return False

        gibberish_words = sum(
            1 for w in clean_words
            if re.search(r'(.)\1{2,}', w)
            or re.search(r'[bcdfghjklmnpqrstvwxyz]{4,}', w)
            or (len(w) > 4 and sum(1 for ch in w if ch in 'aeiou') < 2)
        )
        if gibberish_words / len(clean_words) > 0.25:
            return False

        return True


    def _fallback_explanation(
        self,
        clause_text: str,
        risk_level: str,
        risk_categories: List[str],
        lang: str = 'en',
    ) -> Dict[str, str]:
        """Generate a template-based explanation in English or vernacular Indian languages."""
        vernacular_categories = {
            'hi': {
                'Indemnification': {
                    'what_it_means': 'आप इस बात पर सहमत हैं कि यदि आपके काम या उल्लंघन के कारण दूसरे पक्ष पर मुकदमा होता है तो आप सभी कानूनी खर्च और नुकसान की भरपाई करेंगे।',
                    'why_risky': 'आपके नियंत्रण से बाहर के मुद्दों के लिए भी आपको कानूनी शुल्क और हर्जाने के रूप में बड़ी रकम चुकानी पड़ सकती है।',
                    'what_to_do': 'आपसी क्षतिपूर्ति (Mutual Indemnification) का अनुरोध करें और अपने वित्तीय दायित्व को अनुबंध मूल्य तक सीमित रखें।',
                },
                'Unlimited Liability': {
                    'what_it_means': 'विवाद या उल्लंघन होने पर आपको कितनी राशि का भुगतान करना पड़ सकता है, इसकी कोई अधिकतम सीमा नहीं है।',
                    'why_risky': 'एक भी विवाद आपके व्यवसाय या व्यक्तिगत वित्त को असीमित वित्तीय दावों के खतरे में डाल सकता है।',
                    'what_to_do': 'अनुबंध के तहत प्राप्त शुल्क के बराबर एक सख्त मौद्रिक देयता सीमा (Liability Cap) तय करने का आग्रह करें।',
                },
                'Auto Renewal': {
                    'what_it_means': 'यह अनुबंध स्वचालित रूप से अगले पूर्ण कार्यकाल के लिए नवीनीकृत हो जाता है जब तक कि आप समय सीमा से पहले लिखित रद्दीकरण न भेजें।',
                    'why_risky': 'यदि आप समय सीमा चूक जाते हैं, तो आप एक और पूर्ण अवधि के लिए भुगतान करने के लिए बाध्य हो जाएंगे।',
                    'what_to_do': 'नवीनीकरण से 60 दिन पहले अनुस्मारक सेट करें या स्पष्ट सहमति को अनिवार्य बनाएं।',
                },
                'Non-Compete': {
                    'what_it_means': 'इस अनुबंध के दौरान और बाद में आपको प्रतिस्पर्धी व्यवसायों के साथ काम करने या समान सेवाएं प्रदान करने से प्रतिबंधित किया गया है।',
                    'why_risky': 'यह आपके नए ग्राहक प्राप्त करने या उद्योग में आय अर्जित करने की क्षमता को गंभीर रूप से सीमित करता है।',
                    'what_to_do': 'इस प्रतिबंध को केवल विशिष्ट नामित प्रतिस्पर्धियों तक सीमित करें और समय अवधि को छोटा करें।',
                },
                'Unilateral Termination': {
                    'what_it_means': 'दूसरा पक्ष बिना कोई कारण बताए किसी भी समय अनुबंध को समाप्त कर सकता है।',
                    'why_risky': 'बिना पर्याप्त नोटिस के आप अचानक अपना अपेक्षित राजस्व खो सकते हैं।',
                    'what_to_do': '30 या 60 दिनों की अनिवार्य लिखित नोटिस अवधि के साथ पारस्परिक समाप्ति अधिकारों का अनुरोध करें।',
                },
            },
            'ta': {
                'Indemnification': {
                    'what_it_means': 'உங்கள் வேலை அல்லது விதிமீறல் காரணமாக மறுதரப்பு மீது வழக்கு தொடரப்பட்டால், அனைத்து சட்டச் செலவுகள் மற்றும் இழப்புகளையும் நீங்கள் ஏற்க ஒப்புக்கொள்கிறீர்கள்.',
                    'why_risky': 'உங்கள் கட்டுப்பாட்டிற்கு அப்பாற்பட்ட சிக்கல்களுக்கும் கூட நீங்கள் அதிக தொகையை இழப்பீடாக செலுத்த வேண்டியிருக்கும்.',
                    'what_to_do': 'இருதரப்பு இழப்பீட்டைக் கோருங்கள் மற்றும் உங்கள் அதிகபட்ச பொறுப்பை ஒப்பந்த மதிப்புக்கு கட்டுப்படுத்துங்கள்.',
                },
                'Unlimited Liability': {
                    'what_it_means': 'சர்ச்சை ஏற்பட்டால் நீங்கள் செலுத்த வேண்டிய பணத்திற்கு உச்ச வரம்பு எதுவும் இல்லை.',
                    'why_risky': 'ஒரு சிறிய சிக்கல் கூட உங்கள் வணிகம் அல்லது தனிப்பட்ட நிதியை வரம்பற்ற இழப்பீட்டு கோரிக்கைகளுக்கு ஆளாக்கும்.',
                    'what_to_do': 'ஒப்பந்தத்தின் கீழ் பெறப்பட்ட கட்டணத்திற்கு சமமான கடுமையான பொறுப்பு வரம்பை வலியுறுத்துங்கள்.',
                },
                'Auto Renewal': {
                    'what_it_means': 'காலக்கெடுவுக்கு முன் ரத்து செய்யாவிட்டால், இந்த ஒப்பந்தம் தானாகவே அடுத்த முழு காலத்திற்கும் புதுப்பிக்கப்படும்.',
                    'why_risky': 'குறிப்பிட்ட அறிவிப்பு காலக்கெடுவை தவறவிட்டால், நீங்கள் மற்றொரு முழு காலத்திற்கு கட்டணம் செலுத்த வேண்டியிருக்கும்.',
                    'what_to_do': 'புதுப்பித்தலுக்கு 60 நாட்களுக்கு முன் நினைவூட்டல் அமைக்கவும் அல்லது வெளிப்படையான ஒப்புதலைக் கோரவும்.',
                },
                'Non-Compete': {
                    'what_it_means': 'இந்த ஒப்பந்தத்தின் போதும் பின்னரும் இதே போன்ற சேவைகளை வழங்கவோ அல்லது போட்டியாளர்களுடன் பணியாற்றவோ தடை விதிக்கப்படுகிறது.',
                    'why_risky': 'இது உங்கள் தொழில் துறையில் புதிய வாடிக்கையாளர்களைப் பெறுவதையோ அல்லது வருமானம் ஈட்டுவதையோ தடுக்கிறது.',
                    'what_to_do': 'குறிப்பிட்ட போட்டியாளர்களுக்கு மட்டுமே இந்த தடையை கட்டுப்படுத்துங்கள் மற்றும் கால அளவைக் குறைக்கவும்.',
                },
                'Unilateral Termination': {
                    'what_it_means': 'எந்த காரணமும் கூறாமல் மறுதரப்பு எந்த நேரத்திலும் இந்த ஒப்பந்தத்தை ரத்து செய்யலாம்.',
                    'why_risky': 'போதுமான முன்னறிவிப்பு இல்லாமல் நீங்கள் எதிர்பார்க்கும் வருவாயை திடீரென இழக்க நேரிடும்.',
                    'what_to_do': '30 முதல் 60 நாட்கள் வரையிலான எழுத்துப்பூர்வ அறிவிப்பு காலத்துடன் கூடிய இருதரப்பு ரத்து உரிமையைக் கோருங்கள்.',
                },
            },
            'te': {
                'Indemnification': {
                    'what_it_means': 'మీ పని లేదా ఉల్లంఘన కారణంగా ఇతర పక్షంపై దావా వేయబడితే, అన్ని చట్టపరమైన ఖర్చులు మరియు నష్టాలను మీరు భరించడానికి అంగీకరిస్తున్నారు.',
                    'why_risky': 'మీ నియంత్రణలో లేని సమస్యలకు కూడా మీరు పెద్ద మొత్తంలో చట్టపరమైన రుసుములు మరియు నష్టపరిహారం చెల్లించాల్సి రావచ్చు.',
                    'what_to_do': 'పరస్పర నష్టపరిహారాన్ని అడగండి మరియు మీ గరిష్ట ఆర్థిక బాధ్యతను కాంట్రాక్ట్ విలువకు పరిమితం చేయండి.',
                },
                'Unlimited Liability': {
                    'what_it_means': 'వివాదం సంభవించినప్పుడు మీరు చెల్లించాల్సిన నష్టపరిహారానికి ఎటువంటి పరిమితి లేదా గరిష్ట పరిమితి లేదు.',
                    'why_risky': 'ఒక్క వివాదం మీ వ్యాపారాన్ని లేదా వ్యక్తిగత ఆర్థిక స్థితిని అపరిమిత దావాలకు గురిచేయవచ్చు.',
                    'what_to_do': 'చెల్లించిన ఫీజుకు సమానమైన బాధ్యత పరిమితిని (Liability Cap) చేర్చాలని పట్టుబట్టండి.',
                },
                'Auto Renewal': {
                    'what_it_means': 'గడువుకు ముందు రద్దు నోటీసు ఇవ్వకపోతే, ఒప్పందం స్వయంచాలకంగా మరొక పూర్తి కాలానికి పునరుద్ధరించబడుతుంది.',
                    'why_risky': 'నోటీసు విండోను మీరు మిస్ అయితే, మీరు మరొక పూర్తి కాలానికి చెల్లించాల్సి ఉంటుంది.',
                    'what_to_do': 'పునరుద్ధరణకు 60 రోజుల ముందు రిమైండర్‌ను సెట్ చేయండి లేదా మాన్యువల్ సమ్మతిని తప్పనిసరి చేయండి.',
                },
                'Non-Compete': {
                    'what_it_means': 'ఈ ఒప్పందం సమయంలో మరియు తరువాత పోటీ వ్యాపారాలతో కలిసి పనిచేయడం లేదా సేవలందించడం నిషేధించబడింది.',
                    'why_risky': 'ఇది మీ రంగంలో కొత్త క్లయింట్లను పొందడం లేదా ఆదాయాన్ని సంపాదించే సామర్థ్యాన్ని పరిమితం చేస్తుంది.',
                    'what_to_do': 'నిర్దిష్ట పోటీదారులకు మాత్రమే నిబంధనను పరిమితం చేయండి మరియు వ్యవధిని తగ్గించండి.',
                },
                'Unilateral Termination': {
                    'what_it_means': 'ఎటువంటి కారణం చెప్పకుండా ఇతర పక్షం ఎప్పుడైనా ఒప్పందాన్ని రద్దు చేయవచ్చు.',
                    'why_risky': 'సరైన నోటీసు లేకుండా మీరు ఆశించిన ఆదాయాన్ని అకస్మాత్తుగా కోల్పోవచ్చు.',
                    'what_to_do': '30 లేదా 60 రోజుల వ్రాతపూర్వక నోటీసు వ్యవధితో పరస్పర రద్దు హక్కులను అడగండి.',
                },
            },
        }

        vernacular_defaults = {
            'hi': {
                'high': {'what_it_means': 'इस खंड में आपके अधिकारों और दायित्वों पर महत्वपूर्ण कानूनी जोखिम शामिल हैं।', 'why_risky': 'यह आपके व्यवसाय को भारी वित्तीय हानि या कानूनी विवादों के जोखिम में डाल सकता है।', 'what_to_do': 'हस्ताक्षर करने से पहले खंड की समीक्षा करें और संशोधन का अनुरोध करें।'},
                'medium': {'what_it_means': 'इस खंड में मध्यम कानूनी दायित्व शामिल हैं जिन पर ध्यान देने की आवश्यकता है।', 'why_risky': 'अस्पष्ट शर्तें भविष्य में विवाद का कारण बन सकती हैं।', 'what_to_do': 'शर्तों को स्पष्ट करें और उचित समय सीमा निर्धारित करें।'},
                'low': {'what_it_means': 'यह एक मानक कानूनी खंड है जो सामान्य अनुबंध प्रथाओं का पालन करता है।', 'why_risky': 'न्यूनतम जोखिम, बशर्ते दायित्व पारस्परिक हों।', 'what_to_do': 'मानक शर्तों की पुष्टि करें।'}
            },
            'ta': {
                'high': {'what_it_means': 'இந்த பிரிவு குறிப்பிடத்தக்க சட்ட மற்றும் நிதி அபாயங்களை உள்ளடக்கியது.', 'why_risky': 'இது உங்கள் வணிகத்திற்கு நிதி இழப்பு அல்லது கடுமையான சட்ட நடவடிக்கைகளுக்கு வழிவகுக்கும்.', 'what_to_do': 'கையெழுத்திடுவதற்கு முன் விதிமுறைகளை மறுபரிசீலனை செய்து திருத்தம் கோருங்கள்.'},
                'medium': {'what_it_means': 'இந்த பிரிவில் கவனிக்கப்பட வேண்டிய நடுத்தர சட்டக் கடமைகள் உள்ளன.', 'why_risky': 'தெளிவற்ற விதிமுறைகள் எதிர்காலத்தில் சர்ச்சை ஏற்பட வழிவகுக்கும்.', 'what_to_do': 'விதிமுறைகளை தெளிவுபடுத்தி நியாயமான காலக்கெடுவை நிர்ணயிக்கவும்.'},
                'low': {'what_it_means': 'இது நிலையான ஒப்பந்த நடைமுறைகளைப் பின்பற்றும் பொதுவான விதிமுறையாகும்.', 'why_risky': 'குறைந்த ஆபத்து, கடமைகள் இருதரப்பிற்கும் பொதுவானதாக இருக்க வேண்டும்.', 'what_to_do': 'நிலையான விதிமுறைகளை உறுதிப்படுத்தவும்.'}
            },
            'te': {
                'high': {'what_it_means': 'ఈ నిబంధన గణనీయమైన చట్టపరమైన మరియు ఆర్థిక ప్రమాదాలను కలిగి ఉంది.', 'why_risky': 'ఇది మీ వ్యాపారాన్ని తీవ్రమైన నష్టాలు లేదా వివాదాలకు గురిచేయవచ్చు.', 'what_to_do': 'సంతకం చేయడానికి ముందు మార్పులను అడగండి.'},
                'medium': {'what_it_means': 'ఈ నిబంధనలో శ్రద్ధ వహించాల్సిన మధ్యస్థ చట్టపరమైన బాధ్యతలు ఉన్నాయి.', 'why_risky': 'అస్పష్టమైన నిబంధనలు భవిష్యత్తులో వివాదాలకు దారితీయవచ్చు.', 'what_to_do': 'నిబంధనలను స్పష్టం చేసి సహేతుకమైన గడువులను నిర్ణయించండి.'},
                'low': {'what_it_means': 'ఇది ప్రామాణిక కాంట్రాక్ట్ విధానాలను అనుసరించే సాధారణ నిబంధన.', 'why_risky': 'కనీస ప్రమాదం, నిబంధనలు పరస్పరం ఉండాలి.', 'what_to_do': 'ప్రామాణిక నిబంధనలను నిర్ధారించండి.'}
            }
        }

        # Check vernacular custom category
        if lang in vernacular_categories:
            for category in risk_categories:
                if category in vernacular_categories[lang]:
                    tpl = vernacular_categories[lang][category]
                    return {'what_it_means': tpl['what_it_means'], 'why_risky': tpl['why_risky'], 'what_to_do': tpl['what_to_do'], 'source': 'fallback'}
            lvl = risk_level.lower() if risk_level.lower() in ('high', 'medium', 'low') else 'low'
            tpl = vernacular_defaults[lang][lvl]
            return {'what_it_means': tpl['what_it_means'], 'why_risky': tpl['why_risky'], 'what_to_do': tpl['what_to_do'], 'source': 'fallback'}

        # English templates
        for category in risk_categories:
            if category in self.FALLBACK_TEMPLATES:
                template = self.FALLBACK_TEMPLATES[category]
                return {
                    'what_it_means': template['what_it_means'],
                    'why_risky': template['why_risky'],
                    'what_to_do': template['what_to_do'],
                    'source': 'fallback',
                }

        level_key = risk_level.lower() if risk_level.lower() in self._DEFAULT_TEMPLATES else 'low'
        template = self._DEFAULT_TEMPLATES[level_key]
        return {
            'what_it_means': template['what_it_means'],
            'why_risky': template['why_risky'],
            'what_to_do': template['what_to_do'],
            'source': 'fallback',
        }

    def answer_question(self, document_text: str, question: str, lang: str = 'en') -> str:
        """Answer a user question about the document in English or vernacular Indian languages."""
        if not self.chat_available() and self._groq_client is None:
            return (
                'Document Q&A requires an API key. '
                'Add a free Groq key (console.groq.com) or Gemini key (ai.google.dev) in Settings.'
            )

        lang_instructions = {
            'en': 'simple, plain English',
            'hi': 'simple, everyday Hindi (हिन्दी) in Devanagari script',
            'ta': 'simple, everyday Tamil (தமிழ்) in Tamil script',
            'te': 'simple, everyday Telugu (తెలుగు) in Telugu script',
        }
        target_lang = lang_instructions.get(lang, 'simple, plain English')

        GROQ_CHAR_LIMIT   = 100_000
        GEMINI_CHAR_LIMIT = 150_000

        # ── Try Groq first ─────────────────────────────────────────────
        if self._groq_client is not None and len(document_text) <= GROQ_CHAR_LIMIT:
            try:
                doc_slice = document_text[:GROQ_CHAR_LIMIT]
                response = self._groq_client.chat.completions.create(
                    model='groq/compound-mini',
                    messages=[
                        {
                            'role': 'system',
                            'content': (
                                f'You are a helpful legal document assistant answering in {target_lang}. '
                                'Answer the user\'s question using ONLY the document provided. '
                                'If the answer is not in the document, say so clearly. '
                                f'Be concise, friendly, and use {target_lang}. '
                                'Use bullet points when listing multiple items.'
                            ),
                        },
                        {
                            'role': 'user',
                            'content': f'DOCUMENT:\n"""\n{doc_slice}\n"""\n\nQUESTION: {question}\n\nANSWER in {target_lang}:',
                        },
                    ],
                    temperature=0.3,
                    max_tokens=800,
                )
                return response.choices[0].message.content.strip()
            except Exception:
                pass  # fall through to Gemini

        # ── Gemini fallback ───────────────────────────────────────────
        if self.model is not None:
            doc_slice = document_text[:GEMINI_CHAR_LIMIT]
            if len(document_text) > GEMINI_CHAR_LIMIT:
                doc_slice += '\n...[Document Truncated]...'
            prompt = f"""You are a helpful legal document assistant.
Answer the user's question using ONLY the document below.
If the answer is not in the document, say so clearly.
Answer in {target_lang}. Be concise, friendly, and accurate.

DOCUMENT:
\"\"\"
{doc_slice}
\"\"\"

QUESTION: {question}

ANSWER in {target_lang}:"""
            try:
                response = self.model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                return f'Sorry, something went wrong: {str(e)}'

        return (
            'No AI model available. Please add a Groq or Gemini API key in Settings.'
        )

