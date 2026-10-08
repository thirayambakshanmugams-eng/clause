import json
import re
import concurrent.futures
from typing import Dict, List, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class ObligationExtractor:
    """Extracts actionable obligations and deadlines with rule-based regex fallback and strict timeout."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._configure_llm()

    def _configure_llm(self):
        if self.api_key and genai:
            try:
                genai.configure(api_key=self.api_key)
                try:
                    self.model = genai.GenerativeModel('gemini-2.0-flash')
                except Exception:
                    self.model = genai.GenerativeModel('gemini-1.5-flash')
            except Exception:
                self.model = None
        else:
            self.model = None

    def configure(self, api_key: str):
        """Update API key and reconfigure."""
        self.api_key = api_key
        self._configure_llm()

    def _rule_based_extract(self, document_text: str) -> List[Dict]:
        """Fast regex-based extraction of key contract obligations."""
        obligations = []
        seen_titles = set()

        patterns = [
            (
                r'(?:payment|invoice|fees?|charges?)[^.\n]{0,80}\b(?:within\s+(\d+\s*(?:days?|business days?|calendar days?))|net\s*(\d+)|on or before\s*([^.\n,;]+))',
                "Payment Due",
                "Settlement of outstanding invoices or fees",
                "Client / Buyer"
            ),
            (
                r'(?:written\s+notice|terminate|cancellation)[^.\n]{0,80}\b(?:at least|within|prior to)?\s*(\d+\s*(?:days?|months?))\b[^.\n]{0,50}(?:written notice|prior notice)',
                "Notice of Termination",
                "Advance written notification required prior to agreement termination",
                "Either Party"
            ),
            (
                r'(?:confidential|non-disclosure)[^.\n]{0,80}\b(?:for a period of|survive for)\s*(\d+\s*(?:years?|months?))\b',
                "Confidentiality Term",
                "Obligation to maintain confidential information protected",
                "Both Parties"
            ),
            (
                r'(?:deliver|provide|furnish|complete)[^.\n]{0,80}\b(?:within\s+(\d+\s*(?:days?|weeks?))|no later than\s*([^.\n,;]+))',
                "Service Deliverable",
                "Delivery of agreed project milestones or services",
                "Service Provider"
            ),
            (
                r'(?:indemnif|hold harmless)[^.\n]{0,100}\b(?:promptly|within\s+(\d+\s*days?)|upon notice)',
                "Indemnification Claim Notice",
                "Notice of legal claim requiring defense and indemnification",
                "Indemnified Party"
            ),
        ]

        for regex, title, desc, party in patterns:
            match = re.search(regex, document_text, re.IGNORECASE)
            if match and title not in seen_titles:
                timeline = [g for g in match.groups() if g]
                timeline_str = timeline[0].strip() if timeline else "As specified"
                obligations.append({
                    "title": title,
                    "description": desc,
                    "timeline": timeline_str,
                    "responsible_party": party
                })
                seen_titles.add(title)

        return obligations

    def extract(self, document_text: str, user_prompt: str = '') -> List[Dict]:
        """Scan document text for obligations and deadlines with 4s timeout and rule fallback."""
        if not document_text:
            return []

        if not self.model:
            return self._rule_based_extract(document_text)

        def _call_gemini():
            prompt = f"""You are an expert contract management AI.
Read the following contract text and extract all actionable obligations, tasks, deadlines, notice periods, and payment timelines.

Contract Text:
{document_text[:10000]}

Convert these passive clauses into actionable timeline events.
"""
            if user_prompt:
                prompt += f"\n\nAdditional user instructions:\n{user_prompt}\n"

            prompt += """
Respond strictly in valid JSON format:
{
    "obligations": [
        {
            "title": "Short title (e.g. Payment Due, Notice of Termination)",
            "description": "Brief description of what must be done",
            "timeline": "Extracted timeline (e.g. Net 30 days, within 15 days of breach)",
            "responsible_party": "Who needs to do this (e.g. Client, Vendor, Both)"
        }
    ]
}
"""
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            data = json.loads(text.strip())
            return data.get('obligations', [])

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                res = future.result(timeout=4)  # 4s max timeout
                if res:
                    return res
                return self._rule_based_extract(document_text)
        except Exception:
            return self._rule_based_extract(document_text)
