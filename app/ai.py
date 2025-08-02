# from groq import Groq
# from .config import GROQ_API_KEY
# import json

# client = Groq(api_key=GROQ_API_KEY)

# async def ai_translate_and_summarize(content):
#     prompt = f"""
# Translate this market report to English if necessary, and summarize it with:
# - Key insights
# - Metrics
# - Market outlook
# - Risk factors

# Respond in JSON with keys:
# original_language, translated_content, summary, key_metrics, market_outlook, risk_factors

# Content:
# {content}
# """
#     try:
#         response = client.chat.completions.create(
#             model="moonshotai/kimi-k2-instruct",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.6,
#             max_completion_tokens=4096,
#             top_p=1,
#             stream=False,
#             response_format={"type": "json_object"},
#             stop=None,
#         )
#         raw = response.choices[0].message.content
#         return json.loads(raw)
#     except Exception as e:
#         print("Groq AI error:", e)
#         return {
#             "original_language": "unknown",
#             "translated_content": content,
#             "summary": content[:500],
#             "key_metrics": "",
#             "market_outlook": "",
#             "risk_factors": ""
#         }

from groq import Groq
from app.config import Config
import json
import logging
from typing import Dict, Any

class AIProcessor:
    def __init__(self):
        self.client = Groq(api_key=Config.GROQ_API_KEY)
        self.model = Config.AI_MODEL
        self.logger = logging.getLogger(__name__)
    
    async def process_content(self, content: str, source_language: str = "auto") -> Dict[str, Any]:
        """
        Process content with AI: translation, summarization, and analysis
        """
        try:
            # Limit content length to avoid token limits
            limited_content = content[:Config.MAX_CONTENT_LENGTH]
            
            prompt = self._create_analysis_prompt(limited_content)
            
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst and translator. Always respond with valid JSON format."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.2,
                max_tokens=3000,
                top_p=1,
                stream=False
            )
            
            result_text = response.choices[0].message.content
            self.logger.info(f"AI processing completed. Model: {self.model}")
            
            # Parse JSON response
            try:
                result = json.loads(result_text)
                return self._validate_and_enhance_result(result, content)
            except json.JSONDecodeError:
                self.logger.warning("AI returned non-JSON response, attempting to parse")
                return self._parse_non_json_response(result_text, content)
                
        except Exception as e:
            self.logger.error(f"AI processing error: {str(e)}")
            return self._create_fallback_result(content, str(e))
    
    def _create_analysis_prompt(self, content: str) -> str:
        """Create a comprehensive analysis prompt for the AI"""
        return f"""
Analyze this financial market report and provide a comprehensive analysis in JSON format.

Please provide:
1. **Language Detection**: Identify the original language
2. **Translation**: If not in English, translate to English preserving all financial terms and numbers
3. **Content Analysis**: Extract and analyze the key information
4. **Markdown Formatting**: Create a well-formatted markdown version that preserves the structure and visual hierarchy of the original report

Response format (must be valid JSON):
{{
    "original_language": "detected language or 'English'",
    "translated_content_markdown": "Full content translated to English in markdown format with proper headers, lists, tables, and emphasis",
    "executive_summary": "Comprehensive 3-4 paragraph summary highlighting the most critical insights",
    "key_insights": [
        "List of 5-7 most important insights from the report",
        "Each insight should be actionable and specific"
    ],
    "financial_metrics": {{
        "prices": "Key price movements and levels mentioned",
        "percentages": "Important percentage changes and ratios",
        "volumes": "Trading volumes or market size data",
        "forecasts": "Numerical predictions and targets"
    }},
    "market_outlook": {{
        "short_term": "Next 1-3 months outlook",
        "medium_term": "3-12 months outlook", 
        "long_term": "Beyond 12 months outlook"
    }},
    "risk_assessment": {{
        "high_risk_factors": ["List of major risks identified"],
        "medium_risk_factors": ["List of moderate risks"],
        "risk_mitigation": "Suggested risk management approaches"
    }},
    "actionable_recommendations": [
        "Specific, actionable recommendations for investors/traders",
        "Each recommendation should be concrete and implementable"
    ],
    "confidence_level": "High/Medium/Low - based on data quality and analysis certainty"
}}

Content to analyze:
{content}
"""
    
    def _validate_and_enhance_result(self, result: Dict[str, Any], original_content: str) -> Dict[str, Any]:
        """Validate and enhance the AI result"""
        
        # Ensure all required keys exist
        required_keys = [
            'original_language', 'translated_content_markdown', 'executive_summary',
            'key_insights', 'financial_metrics', 'market_outlook', 'risk_assessment',
            'actionable_recommendations', 'confidence_level'
        ]
        
        for key in required_keys:
            if key not in result:
                result[key] = f"Not available - {key}"
        
        # Add metadata
        result['processing_metadata'] = {
            'model_used': self.model,
            'content_length': len(original_content),
            'truncated': len(original_content) > Config.MAX_CONTENT_LENGTH
        }
        
        return result
    
    def _parse_non_json_response(self, response_text: str, content: str) -> Dict[str, Any]:
        """Parse non-JSON response as fallback"""
        return {
            'original_language': 'Unknown',
            'translated_content_markdown': f"# Market Report Analysis\n\n{response_text}",
            'executive_summary': response_text[:500] + "...",
            'key_insights': ['AI processing completed with non-standard format'],
            'financial_metrics': {'note': 'Unable to extract structured metrics'},
            'market_outlook': {'note': 'Please review full analysis'},
            'risk_assessment': {'note': 'Please review full analysis'},
            'actionable_recommendations': ['Review full analysis for insights'],
            'confidence_level': 'Low',
            'processing_metadata': {
                'model_used': self.model,
                'content_length': len(content),
                'parsing_issue': True
            }
        }
    
    def _create_fallback_result(self, content: str, error: str) -> Dict[str, Any]:
        """Create fallback result when AI processing fails"""
        return {
            'original_language': 'Unknown',
            'translated_content_markdown': f"# Market Report\n\n{content[:1000]}...",
            'executive_summary': f"Processing failed: {error}. Original content preview: {content[:300]}...",
            'key_insights': ['AI processing failed - manual review required'],
            'financial_metrics': {'error': error},
            'market_outlook': {'error': 'Processing failed'},
            'risk_assessment': {'error': 'Processing failed'},
            'actionable_recommendations': ['Manual review required due to processing error'],
            'confidence_level': 'Error',
            'processing_metadata': {
                'model_used': self.model,
                'error': error,
                'content_length': len(content)
            }
        }

# Global instance
ai_processor = AIProcessor()