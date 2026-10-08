import json
import os
import re
import concurrent.futures
from typing import Dict, List, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class PlaybookAnalyzer:
    """Analyzes clauses against a standard corporate playbook with rule-based fallback."""
    
    def __init__(self, playbook_path: str, api_key: Optional[str] = None):
        self.playbook_path = playbook_path
        self.api_key = api_key
        self.playbook = self._load_playbook()
        self._configure_llm()

    def _load_playbook(self) -> Dict:
        if os.path.exists(self.playbook_path):
            try:
                with open(self.playbook_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('playbook', {})
            except Exception:
                pass
        return {"rules": []}
        
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

    def _rule_based_check(self, clauses: List[Dict]) -> Dict[str, List[Dict]]:
        """Fast fallback rule-based analyzer when LLM is unavailable or slow."""
        violations = {}
        for c in clauses:
            c_text = c.get('text', '').lower()
            c_id = str(c.get('id', ''))
            c_violations = []

            # PB-001: Payment Terms
            if re.search(r'\b(due upon receipt|net\s*(?:10|15|7))\b', c_text):
                c_violations.append({
                    "rule_id": "PB-001",
                    "category": "Payment Terms",
                    "explanation": "Payment terms are less than Net 30 standard.",
                    "alternative_text": "All undisputed invoices shall be paid within thirty (30) days of receipt."
                })

            # PB-002: Liability Limit
            if re.search(r'\b(unlimited liability|no limitation on liability|liable without limitation)\b', c_text):
                c_violations.append({
                    "rule_id": "PB-002",
                    "category": "Liability Limit",
                    "explanation": "Clause contains uncapped or unlimited liability.",
                    "alternative_text": "In no event shall either party's aggregate liability exceed the total amounts paid under this Agreement in the twelve (12) months preceding the claim."
                })

            # PB-003: Governing Law
            if ('governing law' in c_text or 'jurisdiction' in c_text) and 'delaware' not in c_text and any(state in c_text for state in ['california', 'new york', 'england', 'singapore', 'india', 'texas']):
                c_violations.append({
                    "rule_id": "PB-003",
                    "category": "Governing Law",
                    "explanation": "Governing law specifies a non-Delaware jurisdiction.",
                    "alternative_text": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware."
                })

            # PB-004: Auto-Renewal
            if re.search(r'\b(automatically renew|auto-renew)\b', c_text) and not re.search(r'\b(?:60|90)\s*days\b', c_text):
                c_violations.append({
                    "rule_id": "PB-004",
                    "category": "Auto-Renewal",
                    "explanation": "Contract automatically renews without requiring at least 60 days written notice.",
                    "alternative_text": "This Agreement will not automatically renew. Either party may request renewal by providing written notice at least sixty (60) days prior to the expiration of the current term."
                })

            if c_violations:
                violations[c_id] = c_violations

        return violations

    def analyze_document(self, clauses: List[Dict], user_prompt: str = '') -> Dict[str, List[Dict]]:
        """Check clauses against playbook rules, with fast rule fallback and strict timeout."""
        if not clauses:
            return {}

        rules = self.playbook.get('rules', [])
        if not self.model or not rules:
            return self._rule_based_check(clauses)

        def _call_gemini():
            rules_text = json.dumps(rules, indent=2)
            clauses_context = "\n\n".join([f"Clause ID {c['id']}:\n{c['text']}" for c in clauses[:25]])
            prompt = f"""You are a corporate legal AI. 
Compare the following contract clauses against our corporate playbook rules.
If any clause CLEARLY violates one or more rules, identify them.

Contract Clauses:
{clauses_context[:10000]}

Playbook Rules:
{rules_text}
"""
            if user_prompt:
                prompt += f"\n\nAdditional user instructions:\n{user_prompt}\n"
            prompt += """
Respond strictly in valid JSON format:
{
    "violations": {
        "clause_1": [
            {
                "rule_id": "PB-001",
                "category": "Category Name",
                "explanation": "Why it violates the rule",
                "alternative_text": "Suggested alternative"
            }
        ]
    }
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
            return data.get('violations', {})

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini)
                return future.result(timeout=4)  # 4s max timeout
        except Exception:
            return self._rule_based_check(clauses)
