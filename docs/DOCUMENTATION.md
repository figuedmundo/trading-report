# Trading Report System - Documentation Index

This document provides a centralized index to all documentation for the Trading Report system. Use this as your starting point to find the information you need.

## Quick Start

- **First time setup?** → Start with [`docs/config-examples/SETUP_GUIDE.md`](docs/config-examples/SETUP_GUIDE.md)
- **Already configured?** → Go to [`USERS_MANUAL.md`](USERS_MANUAL.md)
- **Troubleshooting an issue?** → Check [`HEALTH_MONITORING.md`](HEALTH_MONITORING.md) or section below
- **Setting up N8N workflows?** → See [`docs/n8n-workflows/README.md`](docs/n8n-workflows/README.md)

## Documentation Hierarchy

### 1. User-Facing Documentation

#### [`USERS_MANUAL.md`](USERS_MANUAL.md) - Main User Guide
- **Purpose**: Complete guide for end users who want to use the system
- **Audience**: Non-technical users, system operators
- **Covers**:
  - System overview and architecture
  - How to configure the system
  - How to use N8N workflows
  - How to monitor and manage the system
  - Common tasks and operations
  - Frequently asked questions
- **When to use**: You're a user trying to understand and operate the system

#### [`HEALTH_MONITORING.md`](HEALTH_MONITORING.md) - Operations & Monitoring Manual
- **Purpose**: Detailed operational guide for running the system in production
- **Audience**: System operators, DevOps engineers
- **Covers**:
  - Health monitoring system architecture
  - Error logging and alerting
  - Service health checks
  - Alert configuration and management
  - Troubleshooting failing services
  - Debugging workflow issues
  - Performance metrics and optimization
- **When to use**: Something is not working or you need to monitor system health

#### [`README.md`](README.md) - Project Overview
- **Purpose**: High-level project summary
- **Audience**: Developers, project stakeholders
- **Covers**:
  - Project goals and features
  - Quick start commands
  - Technology stack
  - Contributing guidelines
- **When to use**: Getting a bird's-eye view of the project

### 2. Configuration & Setup Documentation

Located in: [`docs/config-examples/`](docs/config-examples/)

#### [`SETUP_GUIDE.md`](docs/config-examples/SETUP_GUIDE.md) - Complete Setup Instructions
- **Purpose**: Step-by-step guide to configure all services for first time
- **Sections**:
  1. AI Provider Setup (Anthropic Claude or Groq)
  2. Database Configuration
  3. Email/SMTP Setup (Gmail, Outlook, custom)
  4. Telegram Bot Configuration
  5. Webhook Security Setup
  6. Network & Domain Configuration
  7. Trading Portal Credentials
  8. Configuration Verification
  9. Service Startup
  10. N8N Workflow Setup
  11. Configuration Checklist
  12. Troubleshooting
- **When to use**: Setting up the system for the first time

#### [`.env.production`](.env.production) - Production Configuration Template
- **Purpose**: Annotated example of all environment variables
- **Covers**:
  - AI Provider configuration
  - Database credentials
  - Email/SMTP settings
  - Telegram configuration
  - Security settings
  - Health monitoring parameters
  - Service ports and URLs
  - Timezone and logging
- **When to use**: Creating your `.env` file (copy and customize)

#### [`docker-compose.override.example.yml`](docs/config-examples/docker-compose.override.example.yml) - Docker Compose Overrides
- **Purpose**: Examples of overriding Docker Compose settings for different scenarios
- **Includes**:
  1. Development environment (debug logging, hot reload)
  2. Production environment (increased resources)
  3. Minimal footprint (low-spec hardware)
  4. Custom ports setup
  5. External database integration
  6. Testing environment
  7. Container registry configuration
  8. Traefik reverse proxy
  9. Custom health checks
  10. N8N persistence
- **When to use**: Need to customize Docker Compose for your environment

#### [`UBUNTU_HOMELAB_DEPLOYMENT.md`](docs/config-examples/UBUNTU_HOMELAB_DEPLOYMENT.md) - Ubuntu Home Lab Deployment
- **Purpose**: Step-by-step guide for deploying on a fresh Ubuntu Server
- **Covers**:
  - Server preparation (Docker, Firewall)
  - Installation and Configuration
  - Production deployment
  - Secure external access (Cloudflare Tunnel/Nginx)
- **When to use**: Deploying to a dedicated server or VM in a home lab environment

#### [`CONFIGURATION_CHECKLIST.md`](docs/config-examples/CONFIGURATION_CHECKLIST.md) - Complete Verification Checklist
- **Purpose**: 18-phase comprehensive checklist to verify system is production-ready
- **Covers**:
  1. Initial setup
  2. AI provider configuration
  3. Database setup
  4. Email/SMTP configuration
  5. Telegram setup
  6. Webhook security
  7. Network configuration
  8. Trading portal credentials
  9. Service port configuration
  10. Health check configuration
  11. Docker configuration
  12. N8N workflow setup
  13. System integration test
  14. Security hardening
  15. Backup and recovery
  16. Monitoring and logging
  17. Documentation
  18. Final verification and sign-off
- **When to use**: Before launching to production, to ensure nothing is missed

### 3. Workflow & Automation Documentation

Located in: [`docs/n8n-workflows/`](docs/n8n-workflows/)

#### [`README.md`](docs/n8n-workflows/README.md) - N8N Workflow Guide
- **Purpose**: Complete guide to N8N workflow system and templates
- **Covers**:
  - Available workflow templates
  - How to import workflows
  - How to configure workflows
  - How to customize workflows
  - Testing workflows
  - Monitoring workflow execution
  - Troubleshooting workflow issues
  - Best practices
- **When to use**: Working with N8N workflows

#### [`01-email-report-processing.json`](docs/n8n-workflows/01-email-report-processing.json) - Email Report Processing Workflow
- **Purpose**: Main N8N workflow for processing email reports
- **Workflow steps**:
  1. Webhook trigger from email service
  2. Extract report URL from email
  3. Scrape content from trading portal
  4. Analyze with AI
  5. Check analysis success
  6. Send email notification
  7. Send Telegram notification
  8. Log to audit trail
- **When to use**: Processing email reports through N8N

### 4. Product & Architecture Documentation

Located in: [`agent-os/product/`](agent-os/product/) and [`agent-os/specs/`](agent-os/specs/)

#### [`agent-os/product/mission.md`](agent-os/product/mission.md) - Product Mission
- **Purpose**: Project mission, vision, and goals
- **When to use**: Understanding project strategy and direction

#### [`agent-os/product/roadmap.md`](agent-os/product/roadmap.md) - Product Roadmap
- **Purpose**: Planned features and phases
- **When to use**: Seeing what's planned next

#### [`agent-os/product/tech-stack.md`](agent-os/product/tech-stack.md) - Technology Stack
- **Purpose**: Detailed tech stack decisions and rationale
- **When to use**: Understanding technology choices

#### [`agent-os/specs/`](agent-os/specs/) - Technical Specifications
- **Purpose**: Detailed implementation specifications for completed phases
- **When to use**: Deep dive into specific component architecture

### 5. Code Standards & Best Practices

Located in: [`agent-os/standards/`](agent-os/standards/)

#### `backend/api.md` - REST API Standards
- **Purpose**: API endpoint design patterns
- **When to use**: Adding new API endpoints

#### `backend/models.md` - Database Model Standards
- **Purpose**: Database model structure and patterns
- **When to use**: Adding new database models

#### `global/coding-style.md` - Coding Standards
- **Purpose**: Code style and formatting guidelines
- **When to use**: Writing code

#### `testing/test-writing.md` - Testing Standards
- **Purpose**: Unit and integration testing patterns
- **When to use**: Writing tests

## Common Scenarios & Where to Find Help

### Setting Up the System for the First Time
1. Read: [`USERS_MANUAL.md`](USERS_MANUAL.md) - Introduction section
2. Follow: [`docs/config-examples/SETUP_GUIDE.md`](docs/config-examples/SETUP_GUIDE.md)
3. Verify: [`docs/config-examples/CONFIGURATION_CHECKLIST.md`](docs/config-examples/CONFIGURATION_CHECKLIST.md)
4. Refer: [`docs/config-examples/.env.production`](docs/config-examples/.env.production) - for environment variables

### Using the System
1. Read: [`USERS_MANUAL.md`](USERS_MANUAL.md) - System Configuration and Using the System sections
2. Reference: [`docs/n8n-workflows/README.md`](docs/n8n-workflows/README.md) - if working with N8N

### Troubleshooting Issues
1. Check: [`HEALTH_MONITORING.md`](HEALTH_MONITORING.md) - Troubleshooting section
2. Check: [`USERS_MANUAL.md`](USERS_MANUAL.md) - FAQ and Common Issues
3. Check: [`docs/n8n-workflows/README.md`](docs/n8n-workflows/README.md) - if issue is workflow-related
4. Check: Service logs:
   ```bash
   docker-compose logs -f service-name
   ```

### Configuring N8N Workflows
1. Read: [`docs/n8n-workflows/README.md`](docs/n8n-workflows/README.md)
2. Import: [`docs/n8n-workflows/01-email-report-processing.json`](docs/n8n-workflows/01-email-report-processing.json)
3. Customize: Using examples in [`docs/n8n-workflows/README.md`](docs/n8n-workflows/README.md) - Customization section

### Setting Up For Production
1. Complete: [`docs/config-examples/SETUP_GUIDE.md`](docs/config-examples/SETUP_GUIDE.md)
2. Verify: [`docs/config-examples/CONFIGURATION_CHECKLIST.md`](docs/config-examples/CONFIGURATION_CHECKLIST.md) - all 18 phases
3. Configure: [`docs/config-examples/docker-compose.override.example.yml`](docs/config-examples/docker-compose.override.example.yml) - production section
4. Test: Run health checks: `curl http://localhost:8003/api/v1/health/status`

### Deploying to a New Environment
1. Copy: All configuration templates
2. Customize: `.env` file with your values
3. Follow: [`docs/config-examples/SETUP_GUIDE.md`](docs/config-examples/SETUP_GUIDE.md)
4. Test: Using health monitoring endpoints
5. Backup: Export N8N workflows and database

### Adding New Features
1. Check: [`agent-os/specs/`](agent-os/specs/) - for architecture patterns
2. Review: [`agent-os/standards/`](agent-os/standards/) - for coding guidelines
3. Test: Following [`agent-os/standards/testing/test-writing.md`](agent-os/standards/testing/test-writing.md)
4. Document: Update relevant documentation

### Debugging Services
1. Check logs: `docker-compose logs -f service-name`
2. Check health: `curl http://localhost:8003/api/v1/health/status`
3. Check database: `make db-shell`
4. Read: [`HEALTH_MONITORING.md`](HEALTH_MONITORING.md) - Troubleshooting section
5. Check: Service-specific documentation if available

## File Structure Overview

```
trading-report/
├── DOCUMENTATION.md                              # This file - documentation index
├── USERS_MANUAL.md                               # Main user guide
├── HEALTH_MONITORING.md                          # Operations manual
├── README.md                                     # Project overview
├── CLAUDE.md                                     # AI assistant instructions
│
├── docs/
│   ├── config-examples/
│   │   ├── SETUP_GUIDE.md                       # Step-by-step setup
│   │   ├── CONFIGURATION_CHECKLIST.md           # Verification checklist
│   │   ├── .env.production                      # Environment template
│   │   └── docker-compose.override.example.yml  # Docker Compose examples
│   │
│   └── n8n-workflows/
│       ├── README.md                            # Workflow guide
│       └── 01-email-report-processing.json      # Main workflow template
│
├── agent-os/
│   ├── product/
│   │   ├── mission.md                           # Product mission
│   │   ├── roadmap.md                           # Roadmap
│   │   └── tech-stack.md                        # Technology decisions
│   │
│   └── standards/
│       ├── global/
│       │   ├── coding-style.md
│       │   └── conventions.md
│       ├── backend/
│       │   ├── api.md
│       │   ├── models.md
│       │   └── queries.md
│       └── testing/
│           └── test-writing.md
│
├── services/
│   ├── email-webhook/
│   ├── playwright-scraper/
│   ├── ai-analyzer/
│   ├── notification-service/
│   └── health-monitoring/
│
├── database/
│   └── migrations/
│
└── docker-compose.yml
```

## Documentation Status & Maintenance

### Documents in This Index

| Document | Status | Last Updated | Maintained By |
|----------|--------|--------------|---------------|
| USERS_MANUAL.md | Complete | Dec 2025 | Project Team |
| HEALTH_MONITORING.md | Complete | Dec 2025 | Project Team |
| README.md | Complete | Dec 2025 | Project Team |
| SETUP_GUIDE.md | Complete | Dec 2025 | Project Team |
| CONFIGURATION_CHECKLIST.md | Complete | Dec 2025 | Project Team |
| .env.production | Complete | Dec 2025 | Project Team |
| docker-compose.override.example.yml | Complete | Dec 2025 | Project Team |
| N8N Workflows | Complete | Dec 2025 | Project Team |
| agent-os/specs | Complete | Dec 2025 | Project Team |
| agent-os/standards | Complete | Dec 2025 | Project Team |

## How to Update Documentation

When updating documentation:

1. **Update the relevant document** directly
2. **Update this index** (DOCUMENTATION.md) if structure changes
3. **Update USERS_MANUAL.md** if user-facing behavior changes
4. **Update HEALTH_MONITORING.md** if operational procedures change
5. **Commit to git** with descriptive message:
   ```bash
   git add docs/
   git commit -m "docs: Update SETUP_GUIDE with new configuration options"
   ```

## Documentation Conventions

- All file paths are relative to project root
- Configuration examples use environment variables (${VAR_NAME})
- Code examples show command-line usage where applicable
- Links use markdown relative paths `[text](path/to/file.md)`
- Critical information is highlighted with **bold** text
- Commands are in code blocks with language specification

## Support & Contributing

For documentation improvements:
1. Check existing documentation to avoid duplication
2. Follow the structure of this index
3. Add cross-references to related topics
4. Keep technical content accurate
5. Update this DOCUMENTATION.md index if adding new files
6. Submit pull request with clear description

For questions about the system:
1. Search documentation first
2. Check [`HEALTH_MONITORING.md`](HEALTH_MONITORING.md) troubleshooting
3. Review service logs: `docker-compose logs service-name`
4. Check health status: `curl http://localhost:8003/api/v1/health/status`

---

**Last Updated**: December 3, 2025

**Documentation Version**: 1.0

**Related**: See [`CLAUDE.md`](CLAUDE.md) for project-specific AI assistance instructions