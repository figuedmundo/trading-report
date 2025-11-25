from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scraper import scrape_report
import logging

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScrapeRequest(BaseModel):
    url: str
    username: str | None = None
    password: str | None = None

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/scrape")
async def scrape_endpoint(request: ScrapeRequest):
    try:
        logger.info(f"Received scrape request for URL: {request.url}")
        result = await scrape_report(request.url, request.username, request.password)
        return result
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
