
## Project Overview
You need an **automated trading report monitoring and analysis system** that:
- Monitors incoming emails for trading reports
- Extracts and follows links from those emails
- Logs into a web portal automatically
- Scrapes the report content (including TradingView images)
- Analyzes the content using AI
- Sends summarized reports via Email and Telegram

## Deployment Instructions

### 1. Prerequisites
- Docker and Docker Compose installed on your machine.
- A valid domain if you plan to expose this to the internet (optional, for webhooks).

### 2. Configuration
The `docker-compose.yml` is pre-configured with default credentials for N8N and PostgreSQL.
- **N8N**: `http://localhost:5678`
- **Playwright Service**: `http://localhost:3000`
- **PostgreSQL**: `localhost:5432` (user: `n8n`, password: `n8n_password`, db: `trading_reports`)

### 3. Start the Stack
Run the following command in the project root:
```bash
docker-compose up -d --build
```

### 4. N8N Setup
1. Open `http://localhost:5678` in your browser.
2. Set up your admin account.
3. Create a new workflow.

#### Workflow Setup Guide
**Step 1: Email Trigger**
- Use the **Email Trigger (IMAP)** node to monitor your inbox for trading reports.
- OR use a **Webhook** node if you are forwarding emails to a service that calls your N8N instance.

**Step 2: Scrape Report**
- Add an **HTTP Request** node.
- **Method**: POST
- **URL**: `http://playwright-service:3000/scrape`
- **Body**: JSON
  ```json
  {
    "url": "{{ $json.body.url }}",  // Extract URL from email first
    "username": "your_portal_username",
    "password": "your_portal_password"
  }
  ```

**Step 3: Save Raw Data**
- Add a **Postgres** node.
- **Operation**: Insert
- **Table**: `reports`
- Map the fields from the scraper output.

**Step 4: AI Analysis**
- Add an **HTTP Request** node to call Groq or Anthropic API.
- Send the `text_content` from the scraper.

**Step 5: Save Analysis**
- Add another **Postgres** node to save the AI result to `analyses` table.

**Step 6: Notifications**
- Add **Telegram** and **Email** nodes to send the final summary.

### 5. API Endpoints (Playwright Service)
- `POST /scrape`: Scrapes a given URL.
  - Body: `{"url": "...", "username": "...", "password": "..."}`
- `GET /health`: Health check.