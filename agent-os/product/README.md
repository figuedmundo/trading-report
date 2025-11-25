# Trading Report Monitor - Product Documentation

This directory contains the complete product definition, planning, and technical documentation for the Trading Report Monitor system.

## Quick Navigation

### 1. **[mission.md](./mission.md)** - Product Vision & Strategy
The north star document that defines:
- Product pitch and user value proposition
- Target users and detailed personas (Jake the day trader, Sarah the portfolio manager, Marcus the retail investor)
- The core problems we solve and quantified impact
- Key differentiators vs. alternatives (N8N alone, manual tools, generic automation)
- Feature list organized by category
- Success criteria for product launch

**Read this if:** You need to understand what we're building and why it matters.

### 2. **[roadmap.md](./roadmap.md)** - Implementation Plan
The execution blueprint with 32 prioritized features across 5 phases:
- **Phase 1 (MVP):** Core email-to-report pipeline (10 items, ~6-8 weeks)
- **Phase 2 (Reliability):** Operational excellence (6 items, ~3-4 weeks)
- **Phase 3 (Intelligence):** Advanced analysis capabilities (5 items, ~4-5 weeks)
- **Phase 4 (Integration):** External API and ecosystem support (6 items, ~5-6 weeks)
- **Phase 5 (Scale):** Performance and ML-driven features (5 items, ~6-8 weeks)

Each item includes:
- Clear feature description (what success looks like)
- Effort estimate (XS to XL)
- Technical dependencies noted

**Read this if:** You're planning sprints, estimating timeline, or tracking progress.

### 3. **[tech-stack.md](./tech-stack.md)** - Technical Reference
Comprehensive documentation of all technology choices:
- Architecture overview (N8N + microservices)
- Backend services (4 Python microservices: webhook, scraper, analyzer, notifier)
- Database design (PostgreSQL 15+ with 8 tables)
- API integrations (Anthropic/Groq, Telegram, SMTP, email webhooks)
- Security practices (credential encryption, secrets management)
- Deployment details (Docker Compose, Traefik, homelab-specific guidance)
- Development setup (pytest, linting, CI/CD)
- Justification for architectural decisions

**Read this if:** You're implementing features, setting up infrastructure, or evaluating tech choices.

---

## Architecture At a Glance

```
Email Inbox
    ↓
[Email Webhook Service] ← FastAPI + Pydantic
    ↓ (N8N Orchestrates)
[Playwright Scraper] ← Python + Playwright
    ↓
[PostgreSQL] ← Persistent storage + audit trail
    ↓
[AI Analyzer] ← Groq or Anthropic API
    ↓
[Notification Service] ← Email + Telegram
    ↓
User (Email + Telegram)
```

**Key Technologies:**
- Container: Docker + Docker Compose
- Backend: Python 3.11+ with FastAPI
- Database: PostgreSQL 15+
- Browser: Playwright (headless Chromium)
- AI: Anthropic Claude or Groq (configurable)
- Notifications: Email (SMTP) + Telegram Bot API
- Orchestration: N8N (visual workflow engine)
- Deployment: Homelab with Traefik reverse proxy

---

## Answering Your Original Questions

### "Should I use N8N or build a custom app?"

**Answer: Use both (hybrid approach).**

**N8N handles:**
- Visual workflow definition and management
- Webhook trigger configuration
- Service-to-service orchestration
- Configuration persistence
- Basic data transformation

**Custom Python services handle:**
- Complex Playwright browser automation
- Report content extraction and parsing
- AI prompt engineering and analysis
- Encrypted credential management
- Custom business logic

**Why not pure N8N?**
- N8N has limited environment control; Playwright and complex dependencies don't fit well
- AI prompt engineering needs flexibility N8N doesn't provide
- Credential encryption requires custom logic

**Why not pure custom app?**
- You'd need to build your own workflow UI and scheduler
- N8N provides battle-tested orchestration and error handling

See **tech-stack.md > "Justification: N8N vs. Custom Application"** for detailed tradeoffs.

### "Agent-based approach vs. custom application?"

**Answer: Custom application with AI integration (not pure agent-based).**

The system is a traditional microservices application with AI components (not autonomous agents). Here's why:

**What makes a pure agent approach harder:**
- Reports need deterministic extraction (Playwright with specific selectors)
- Credentials require secure, encrypted storage
- Notifications must be reliable and auditable
- System needs clear error states and recovery

**What integrates well with AI:**
- AI analysis of extracted content (summarization, signal extraction)
- Future phases (Phase 3+) can add agent-like behavior: trend analysis, consensus detection
- Can later add multi-step AI reasoning for complex report interpretation

If you want true agent behavior, that fits better in Phase 3+ (see roadmap item 21: "Report Comparison & Consensus Analysis").

### "What is the best architectural approach?"

**Answer: Distributed microservices with containerized deployment.**

**Why this design:**
1. **Separation of concerns:** Each service has one job
2. **Scalability:** Can run multiple Playwright instances independently
3. **Reliability:** One service crashing doesn't stop others
4. **Security:** Credentials isolated in container; data never leaves homelab
5. **Testability:** Mock each service independently
6. **Flexibility:** Easy to add new notification channels or AI providers

**Design principles:**
- Data flows left-to-right (Email → Scraper → Database → AI → Notifier)
- Database is single source of truth for reports
- All writes are append-only (audit trail)
- Notifications are idempotent (can retry without duplication)

See **tech-stack.md > "Backend Services"** for detailed service specifications.

---

## Implementation Timeline Estimates

Based on your team and effort estimates in the roadmap:

| Phase | Focus | Duration | Total |
|-------|-------|----------|-------|
| Phase 1 | MVP Email-to-AI Pipeline | 6-8 weeks | 6-8 weeks |
| Phase 2 | Reliability & Monitoring | 3-4 weeks | 9-12 weeks |
| Phase 3 | Intelligence & Analysis | 4-5 weeks | 13-17 weeks |
| Phase 4 | APIs & Integrations | 5-6 weeks | 18-23 weeks |
| Phase 5 | Scale & ML | 6-8 weeks | 24-31 weeks |

**MVP Launch:** Complete Phase 1 (6-8 weeks) for a working system that captures reports, analyzes them, and sends notifications.

**Production Ready:** Complete Phase 2 (additional 3-4 weeks) for reliability, deduplication, and monitoring.

---

## Getting Started

### For Product Managers / Stakeholders
1. Read **mission.md** to understand the product vision
2. Review **roadmap.md** Phase 1 to understand MVP scope
3. Use roadmap for sprint planning and timeline estimates

### For Architects / Tech Leads
1. Review **tech-stack.md** sections 2-4 (services, database, APIs)
2. Evaluate technology choices (Python vs Node, Anthropic vs Groq)
3. Plan infrastructure setup (Docker Compose, TLS configuration)

### For Engineers Implementing Phase 1
1. Study **tech-stack.md** sections:
   - Backend Services (services 1-4)
   - Data Storage & Persistence (PostgreSQL schema)
   - Security & Credential Management
   - Development & Testing
2. Follow the order in **roadmap.md > Phase 1**:
   1. Email webhook service
   2. Credential storage
   3. Playwright browser automation
   4. Content extraction
   5. Database schema
   6. AI integration
   7. Email notifications
   8. Telegram notifications
   9. Webhook security
   10. Health monitoring

---

## Key Decisions Made

### Technology Choices
- **Python 3.11+** for backend services (web scraping ecosystem, LLM integration)
- **PostgreSQL 15+** for database (ACID compliance, audit trail support)
- **Playwright** for browser automation (handles auth, dynamic content)
- **Anthropic Claude 3.5 Sonnet** OR **Groq Mixtral** for AI (user's choice)
- **Docker Compose** for deployment (simplicity, homelab-friendly)
- **N8N** for workflow orchestration (visual UI, battle-tested)

### Architectural Decisions
- **Microservices** (not monolith) - enables independent scaling
- **On-premise only** (not cloud SaaS) - privacy and control
- **Webhook trigger** (not polling) - real-time response, less load
- **Append-only database** - audit trail and compliance
- **Idempotent notifications** - safe to retry without duplication

### Deferred to Later Phases
- Multi-user support (Phase 3)
- ML-based signal prediction (Phase 5)
- Kubernetes deployment (Phase 5)
- Advanced caching (Phase 3+)

---

## Document Maintenance

### When to Update mission.md
- User requests change in product scope
- New target user segment identified
- Feature set expands or contracts
- Success criteria needs revision

### When to Update roadmap.md
- Completing a feature (check it off)
- Discovering dependency on other feature
- Timeline estimate changes
- Business priority shifts

### When to Update tech-stack.md
- Evaluating new technology
- Completing Phase 1 and learning from it
- Adding new AI provider or notification channel
- Security best practices change

---

## Questions?

Refer to these sections for common questions:

**How long will Phase 1 take?** → See roadmap.md items 1-10 with effort estimates

**How do I secure trading credentials?** → See tech-stack.md > "Security & Credential Management"

**How should I structure the database?** → See tech-stack.md > "Primary Database" and the schema components list

**Should I use PostgreSQL or MongoDB?** → See tech-stack.md > "Primary Database" justification

**Can I use Node.js instead of Python?** → Yes, equally viable (see tech-stack.md > "Primary Backend Language")

**What if Playwright doesn't work with our trading portal?** → See tech-stack.md > "Browser Automation Specifics" and "Error Handling"

**How do I handle CAPTCHA on login?** → See tech-stack.md > "Error Handling" section noting manual intervention required

---

## Version History

- **v1.0** (Nov 25, 2025): Initial product documentation created
  - mission.md: Product vision and user personas
  - roadmap.md: 32-item implementation plan across 5 phases
  - tech-stack.md: Comprehensive technical reference
