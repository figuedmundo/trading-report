I need you help me to create a good description and/or BRD , of a tool I need to build, so far just help me to understand what I need to build, no code, I get trading reports to my email, once in a while, no schedule , I just get emails , but many times I cant see them or I miss them, I want create a tool, agent, hook, app, I dont know, but I need be able to identify when one of this emails arrive, get the email, in the email there is a link, the link open a webpage where I need to login, and after the page is open, get all the document report from the webpage, make it read with an AI, and send me a report, with the summary of the market, trades, or whatever the report says, and with a proper AI analisis, , and this report I should get in the emai , and in telegram so I dont miss it , please analise and understand how we can do that, 1. Best option: A service that triggers a webhook the moment an email arrives 2. the report always have some words, but always 1 url, link that is the one we need to login 3. Playwright 4. after login, we need to navigate to the url send in the email report and inside is a blog like page with pictures/inages from tradingview 5. use groq or antropoc api 6. only email and telegram for now 7. I prefer in the homelab can be in postgress , I think is better than files, right ? 8. I want deploy in my homelab, and I can expose a subdomain for the hook, stack: I am good with python or node as backend, please analise, and tell me what I need to build, if I can use the new n8n ? or agents? or make app ? what I need to do ?


## Project Overview
I need an **automated trading report monitoring and analysis system** that:
- Monitors incoming emails for trading reports
- Extracts and follows links from those emails
- Logs into a web portal automatically
- Scrapes the report content (including TradingView images)
- Analyzes the content using AI
- Sends summarized reports via Email and Telegram

---
**Optional** N8N Workflow 


  Recommended starting sequence:
  - #5 (PostgreSQL Schema) - Build the foundation first
  - #1 (Email Webhook) - Then create the entry point
  - #2 (Credential Storage) - Critical for security before scraping
  - #3 & #4 (Playwright & Scraping) - Core data extraction
  - #6 (AI Analysis) - Intelligence layer
  - #7 & #8 (Notifications) - User-facing output
  - #9 & #10 (Security & Monitoring) - Production hardening


-----

