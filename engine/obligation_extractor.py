import json
from typing import Dict, List, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

class ObligationExtractor:
    """Extracts actionable obligations and deadlines from document text."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._configure_llm()

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

    def extract(self, document_text: str, user_prompt: str = '') -> List[Dict]:
        """Scan document text for obligations and deadlines."""
        if not self.model:
            return []
            
        prompt = f"""You are an expert contract management AI.
Read the following contract text and extract all actionable obligations, tasks, deadlines, notice periods, and payment timelines.

Contract Text:
{document_text[:15000]}  # limit text length for processing speed

Convert these passive clauses into actionable timeline events.
"""
        if user_prompt:
            prompt += f"\n\nAdditional user instructions:\n{user_prompt}\n"

        prompt += """
Respond strictly in valid JSON format with the following structure. Do not include markdown formatting like ```json.
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
            return result.get('obligations', [])
        except Exception as e:
            print(f"Obligation Extraction Error: {e}")
            return []
