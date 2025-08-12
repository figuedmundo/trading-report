import logging
import html2text
from datetime import datetime
from typing import Dict, List, Any
import requests
from .config import Config



logger = logging.getLogger(__name__)

class NotionClient:
    def __init__(self):
        self.api_key = Config.NOTION_API_KEY
        self.database_id = Config.NOTION_DATABASE_ID
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def create_report_page(self, analysis: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Create a new page in Notion database for the market report"""
        try:
            # Prepare the page properties
            properties = self._build_page_properties(analysis, source_url)
            
            # Prepare the page content (blocks)
            children = self._build_page_content(analysis)
            
            # Create the page
            payload = {
                "parent": {"database_id": self.database_id},
                "properties": properties,
                "children": children
            }
            
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully created Notion page: {result['id']}")
                return {
                    "success": True,
                    "page_id": result['id'],
                    "page_url": result['url']
                }
            else:
                logger.error(f"Notion API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Failed to create Notion page: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_page_properties(self, full_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Build the properties for the Notion page"""

        metadata = full_data.get('metadata', {})
        analysis = full_data.get('analysis', {})
        metrics = analysis.get('market_metrics', {})
        
        properties = {
            "Title": {
                "title": [
                    {
                        "text": {
                            "content": metadata.get('title', 'Market Report')[:100]  # Notion title limit
                        }
                    }
                ]
            },
            "Source URL": {
                "url": source_url
            },
            "Date": {
                "date": {
                    "start": datetime.now().isoformat()
                }
            },
            "Status": {
                "select": {
                    "name": "New"
                }
            },
            "Market Sentiment": {
                "select": {
                    "name": metrics.get('market_sentiment', 'neutral').title()
                }
            },
            "Word Count": {
                "number": metadata.get('word_count', 0)
            },
            "Confidence Level": {
                "select": {
                    "name": analysis.get('confidence_level')
                }
            }
        }
        
        # Add sectors and stocks as multi-select if available
        if metrics.get('sectors'):
            sector_values = []
            for sector in metrics['sectors'][:10]:
                sector_values.extend(self._split_multi_select(sector))
            properties["Sectors"] = {
                "multi_select": sector_values
            }

        if metrics.get('mentioned_stocks'):
            stock_values = []
            for stock in metrics['mentioned_stocks'][:10]:
                stock_values.extend(self._split_multi_select(stock))
            properties["Stocks"] = {
                "multi_select": stock_values
            }
        
        return properties
    
    def _build_page_content(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build the content blocks for the Notion page"""
        blocks = []
        analysis = report_data.get('analysis', {})
        content = report_data.get('content', {})
        
        try:
            # Summary section
            if analysis.get('summary'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📊 Summary"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": analysis['summary']}}]
                        }
                    }
                ])
            
            # Key Insights
            if analysis.get('key_insights'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "💡 Key Insights"}}]
                    }
                })
                
                for insight in analysis['key_insights']:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": insight}}]
                        }
                    })
            
            # Market Metrics
            metrics = analysis.get('market_metrics', {})
            if any(metrics.values()):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "📈 Market Metrics"}}]
                    }
                })
                
                if metrics.get('mentioned_stocks'):
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "**Mentioned Stocks:** "}, "annotations": {"bold": True}},
                                {"type": "text", "text": {"content": ", ".join(metrics['mentioned_stocks'][:10])}}
                            ]
                        }
                    })
                
                if metrics.get('sectors'):
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": "**Sectors:** "}, "annotations": {"bold": True}},
                                {"type": "text", "text": {"content": ", ".join(metrics['sectors'])}}
                            ]
                        }
                    })
            
            # Outlook
            if analysis.get('outlook'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "🔮 Market Outlook"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": analysis['outlook']}}]
                        }
                    }
                ])
            
            # Risk Factors
            if analysis.get('risk_factors'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "⚠️ Risk Factors"}}]
                    }
                })
                
                for risk in analysis['risk_factors']:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": risk}}]
                        }
                    })
            
            # Action Items
            if analysis.get('action_items'):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": "✅ Action Items"}}]
                    }
                })
                
                for item in analysis['action_items']:
                    blocks.append({
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [{"type": "text", "text": {"content": item}}],
                            "checked": False
                        }
                    })
            
            # Images
            if content.get("report_images"):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "📷 Gallery"}
                            }
                        ]
                    }
                })

                for img_url in content.get("report_images"):
                    if img_url.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
                        # Use image block for direct image URLs
                        blocks.append({
                            "object": "block",
                            "type": "image",
                            "image": {
                                "type": "external",
                                "external": {
                                    "url": img_url
                                }
                            }
                        })
                    else:
                        # Use bookmark block for non-direct image URLs (like TradingView)
                        blocks.append({
                            "object": "block",
                            "type": "bookmark",
                            "bookmark": {
                                "url": img_url
                            }
                        })
            
            # # Full Translated Content (collapsible)
            # if content.get('translated_content'):
            #     blocks.extend([
            #         {
            #             "object": "block",
            #             "type": "heading_2",
            #             "heading_2": {
            #                 "rich_text": [{"type": "text", "text": {"content": "📄 Full Report (Translated)"}}]
            #             }
            #         },
            #         {
            #             "object": "block",
            #             "type": "toggle",
            #             "toggle": {
            #                 "rich_text": [{"type": "text", "text": {"content": "Click to expand full content"}}],
            #                 "children": [
            #                     {
            #                         "object": "block",
            #                         "type": "paragraph",
            #                         "paragraph": {
            #                             "rich_text": [{"type": "text", "text": {"content": content['translated_content'][:2000]}}]
            #                         }
            #                     }
            #                 ]
            #             }
            #         }
            #     ])
        
            # Original Report
            # Convert HTML to plain text with markdown formatting preserved
            html_converter = html2text.HTML2Text()
            html_converter.ignore_links = False  # Keep links if present
            html_converter.body_width = 0  # Prevent word wrapping
            if content.get('original_html'):
                blocks.extend([
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [{"type": "text", "text": {"content": "📄 Original Report"}}]
                        }
                    },
                    {
                        "object": "block",
                        "type": "toggle",
                        "toggle": {
                            "rich_text": [{"type": "text", "text": {"content": "Click to expand full content"}}],
                            "children": [
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [{"type": "text", "text": {"content": html_converter.handle(content.get("original_html", "")[:2000])}}]
                                    }
                                }
                            ]
                        }
                    }
                ])
        
        except Exception as e:
            logger.error(f"Error building Notion content blocks: {e}")
            # Fallback basic content
            blocks = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": "Report processed successfully. Error in detailed formatting."}}]
                    }
                }
            ]
        
        return blocks
    
    def update_page_status(self, page_id: str, status: str) -> bool:
        """Update the status of a Notion page"""
        try:
            payload = {
                "properties": {
                    "Status": {
                        "select": {
                            "name": status
                        }
                    }
                }
            }
            
            response = requests.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json=payload,
                timeout=15
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to update Notion page status: {e}")
            return False
        
    def _split_multi_select(self, value):
        # Remove parentheses, split by comma, strip spaces
        if "(" in value and ")" in value:
            category, items = value.split("(", 1)
            category = category.strip()
            items = items.strip(")").split(",")
            return [{"name": category}] + [{"name": item.strip()} for item in items]
        return [{"name": value.strip()}]
