import json
import logging
from groq import Groq
from typing import Dict, Any
from .config import Config

logger = logging.getLogger(__name__)

class GroqAIProcessor:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
    
    def translate_and_analyze(self, content: str) -> Dict[str, Any]:
        """
        Translate content to English and perform comprehensive analysis
        """

        try:
            prompt = self._create_analysis_prompt(content[:8000]) # the Limit of 8000 is to do not over pass the tokens limit

            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst with deep knowledge of global markets, trading, and investment strategies."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=1,
                max_completion_tokens=8192,
                top_p=1,
                reasoning_effort="high",
                stream=False,
                response_format={"type": "json_object"},
                stop=None,
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info("Successfully processed content with Groq AI")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return self._fallback_analysis(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Groq AI processing failed: {e}")
            return self._fallback_analysis(response.choices[0].message.content)
    
    def _fallback_analysis(self, content: str) -> Dict[str, Any]:
        """Fallback analysis when AI processing fails"""
        return {
            "translated_content": content,
            "summary": "Market report analysis temporarily unavailable. Please review original content.",
            "key_insights": ["AI analysis temporarily unavailable"],
            "market_metrics": {
                "mentioned_stocks": [],
                "sectors": [],
                "market_sentiment": "null"
            },
            "outlook": "Please review original report for outlook",
            "risk_factors": ["Manual review required"],
            "action_items": ["Review original report manually"],
            "confidence_level": ["Not Available"]
        }
    
        
    def _create_analysis_prompt(self, content: str) -> str:
        """Create a comprehensive analysis prompt for the AI"""
        return f"""
Analyze this financial market report and provide a comprehensive analysis in JSON format.

Please provide:
1. **Language Detection**: Identify the original language
2. **Translation**: If not in English, translate to English preserving all financial terms and numbers
3. **Content Analysis**: Extract and analyze the key information

Ensure the translation maintains financial terminology accuracy and the analysis focuses on actionable market intelligence.

Response format (must be valid JSON):

{{
    "translated_content": "Full content translated to English",
    "summary": "Comprehensive 3-4 paragraph summary highlighting the most critical insights",
    "key_insights": [
        "List of 5-7 most important insights from the report",
        "Each insight should be actionable and specific"
    ],
    "market_metrics": {{
        "mentioned_stocks": ["List of stocks/companies mentioned"],
        "sectors": ["List of sectors discussed"],
        "market_sentiment": "positive/negative/neutral"
    }},
    "outlook": "Brief outlook or predictions mentioned",
    "risk_factors": ["List of risks or concerns mentioned"],
    "action_items":  [
        "Specific, actionable recommendations for investors/traders",
        "Each recommendation should be concrete and implementable"
    ],
    "confidence_level": "High/Medium/Low - based on data quality and analysis certainty"
}}

Content to analyze:
{content}
"""
    


# Analyze this financial market report and provide a comprehensive analysis

# Please provide:
# 1. **Translation**: If not in English, translate to English preserving all financial terms and numbers
# 2. **Content Analysis**: Extract and analyze the key information

# Ensure the translation maintains financial terminology accuracy and the analysis focuses on actionable market intelligence.

# I need the below points
#     - "translation": "Full content translated to English",
#     - "summary": "Comprehensive needed paragraphs summary highlighting the most critical insights",
#     - "key insights": 
#         "List of 5-7 most important insights from the report",
#         "Each insight should be actionable and specific"
#     - "market metrics": 
#         "mentioned_stocks": ["List of stocks/companies mentioned"],
#         "sectors": ["List of sectors discussed"],
#         "market_sentiment": "positive/negative/neutral"
    
#     - "outlook": "Brief outlook or predictions mentioned",
#     - "risk_factors": "List of risks or concerns mentioned",
#     - "action items":  
#         "Specific, actionable recommendations for investors/traders",
#         "Each recommendation should be concrete and implementable"
  
#     - "confidence level": "High/Medium/Low - based on data quality and analysis certainty"


# Content to analyze:
# {content}
# # """
    