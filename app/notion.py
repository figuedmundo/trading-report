from notion_client import Client
from .config import NOTION_TOKEN, NOTION_DATABASE_ID
from datetime import datetime

notion = Client(auth=NOTION_TOKEN)

def save_to_notion(title, ai_result, url):
    try:
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Title": {"title": [{"text": {"content": title}}]},
                "Report URL": {"url": url},
                "Date": {"date": {"start": datetime.now().isoformat()}},
                "Summary": {"rich_text": [{"text": {"content": ai_result["summary"][:2000]}}]},
                "Original Language": {"rich_text": [{"text": {"content": ai_result["original_language"]}}]}
            }
        )
        return True
    except Exception as e:
        print("Notion error:", e)
        return False
