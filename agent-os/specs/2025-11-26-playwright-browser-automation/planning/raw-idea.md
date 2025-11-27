# Raw Idea: Playwright Browser Automation

## Feature Name
Playwright Browser Automation

## Description from Roadmap
Build Playwright automation to handle trading portal login, navigate to provided URL, and maintain session state across multiple page interactions.

## Size Estimate
M (Medium)

## Context

### Roadmap Position
- **Roadmap Item**: #3 from Phase 1: MVP - Core Email-to-Report Pipeline
- **Project**: Trading Report Automation System
- **Dependencies**:
  - Item #2 (Secure Credential Storage & Management) - COMPLETED
  - Item #5 (PostgreSQL Schema) - COMPLETED

### Existing Reference Code Analysis

#### What Exists
1. **refs/scraper.py**: Working login logic with hardcoded credentials
2. **refs/playwright-service/scraper.py**: Generic login selectors
3. **refs/playwright-service/main.py**: Integration with credential service

#### What Works
- Login handling
- Page navigation
- HTML/text content extraction

#### Critical Finding - What Needs Fixing
- **Image extraction logic in refs/scraper.py (_get_images method using BeautifulSoup) was identified as NOT working**
- Image extraction for charts and TradingView embeds is broken
- **Recommendation**: Implement screenshot-based approach as fallback for image/chart extraction

## Success Criteria
Handle trading portal login, navigate to provided URL, and maintain session state across multiple page interactions.

## Technical Notes
- Must integrate with completed credential service
- Must use PostgreSQL schema for storing extracted content
- Should improve upon existing reference implementations
- Critical path: Fix image extraction using alternative approach (screenshots)
