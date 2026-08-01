import json
import os
from typing import Dict, List, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class PlaybookAnalyzer:
    """Analyzes clauses against a standard corporate playbook."""
    
    def __init__(self, playbook_path: str, api_key: Optional[str] = None):
        self.playbook_path = playbook_path
        self.api_key = api_key
        self.playbook = self._load_playbook()
        self._configure_llm()

    def _load_playbook(self) -> Dict:
        if os.path.exists(self.playbook_path):
            try:
                with open(self.playbook_path, 'r') as f:
                    return json.load(f).get('playbook', {})
            except Exception:
                pass
        return {"rules": []}
        
    def _configure_llm(self):
        if self.api_key and genai:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            
    def configure(self, api_key: str):
        """Update API key and reconfigure."""
        self.api_key = api_key
        self._configure_llm()

    def analyze_document(self, clauses: List[Dict], user_prompt: str = '') -> Dict[str, List[Dict]]:
        """Check all clauses against the playbook rules."""
        if not self.model or not self.playbook.get('rules') or not clauses:
            return {}
            
        rules = self.playbook['rules']
        rules_text = json.dumps(rules, indent=2)
        
        # Prepare clauses text for the prompt
        clauses_context = "\n\n".join([f"Clause ID {c['id']}:\n{c['text']}" for c in clauses])
        
        prompt = f"""You are a corporate legal AI. 
Compare the following contract clauses against our corporate playbook rules.
If any clause CLEARLY violates one or more rules, identify them.

Contract Clauses:
{clauses_context[:20000]}

Playbook Rules:
{rules_text}
"""
        if user_prompt:
            prompt += f"\n\nAdditional user instructions:\n{user_prompt}\n"
            
        prompt += """
Respond strictly in valid JSON format with the following structure. If there are no violations, return an empty object for violations. Do not include markdown formatting like ```json.
{
    "violations": {
        "clause_id_1": [
            {
                "rule_id": "PB-001",
                "category": "Category Name",
                "explanation": "Why it violates the rule",
                "alternative_text": "The suggested alternative text from the rule"
            }
        ]
    }
}
"""
        try:
            response = self.model.generate_content(prompt)
            # Clean up response if it has markdown formatting
            text = response.text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
                
            result = json.loads(text.strip())
            return result.get('violations', {})
        except Exception as e:
            print(f"Playbook Analysis Error: {e}")
            return {}
