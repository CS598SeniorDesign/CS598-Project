# Senior Project 2 Deliverable Instructions & Requirements

> [!NOTE]
> **Disclaimer:** Generative AI was utilized as an instructional design tool to assist in structuring, formatting, and refining these prototype assignment requirements, FAQs, and evaluation criteria.

---

## Deliverable & Grading Structure (Fall Calendar Schedule)

| Milestone | Target Week | Submission & Code Due Date | In-Class Presentation Date | Core Focus & Key Technical Deliverables | Weight |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **Prototype Presentation 1** | **Week 4** | **Thursday, Sep 10 @ 11:59 PM CT** | **Friday, Sep 11 (In-Class)** | **Foundation & Data Layer:** Live demonstration of repository setup, automated CI/CD pipeline, database schemas/migrations, and core API skeletons. | **20%** |
| **Prototype Presentation 2** | **Week 8** | **Thursday, Oct 8 @ 11:59 PM CT** | **Friday, Oct 9 (In-Class)** | **Midterm Alpha Prototype:** Demonstration of working Alpha build, primary user workflows, integrated frontend/backend features, and initial security audits. | **25%** |
| **Prototype Presentation 3** | **Week 12** | **Thursday, Nov 5 @ 11:59 PM CT** | **Friday, Nov 6 (In-Class)** | **Feature-Complete Beta Prototype:** Demonstration of complete Beta functionality, automated E2E test execution, performance optimizations, and bug triage. | **25%** |
| **Prototype Presentation 4** | **Week 16** | **Thursday, Dec 3 @ 11:59 PM CT** | **Friday, Dec 4 (EOH Showcase)** | **Final Production Launch & EOH Showcase:** Public showcase pitch, live production build demo, runnable artifact release, and tagged master repository. | **30%** |
| **Total** | | | | | **100%** |

---

## General Engineering & Pipeline Governance Policies

> [!IMPORTANT]
> ### 1. Repository Integrity & Team Lead Responsibilities
> * **Team Lead Ownership:** The designated **Team Lead** holds primary responsibility for enforcing version control hygiene, ensuring `main` branch integrity, verifying Pull Request (PR) reviews, and confirming that all required technical documentation and AI usage logs are complete and up to date prior to submission deadlines.
> * **Git Issue Tracking & Communication:** Teams **must use GitHub/GitLab Issues** as the primary asynchronous communication channel for tracking bugs, posting automated/manual test execution results, assigning code fixes, and documenting needed system changes. Every bug fix or feature PR must link directly to an open Issue (e.g., `Closes #42`).
> * **Governance & Versioning:** Continuous adherence to Standard Conventional Commits (e.g., `feat:`, `fix:`, `docs:`, `refactor:`). Automated Changelog generation or Semantic Release tagging is required to maintain transparent release histories across prototypes.

> [!WARNING]
> ### 2. Tech Stack & Industry Best Practices (Catch-All Standard)
> * **Industry Standards Expectation:** Students are expected to thoroughly research, understand, and apply industry best practices specific to the programming languages, frameworks, databases, and DevOps tools selected for their project.
> * **Comprehensive Maintenance Obligation:** Even if a specific tool, framework convention, design pattern, or language-specific best practice is not explicitly itemized in these instructions, teams are expected to maintain and enforce the relevant software engineering standards applicable to their chosen tech stack throughout the semester.

---

### Prototype 1: Foundation & Data Layer
* **Code & Submission Due:** Week 4 (Thursday, September 10 @ 11:59 PM CT)
* **In-Class Presentation:** Week 4 (Friday, September 11 In-Class)
* **Grade Weight:** 20%
* **Deliverable Format:** In-Person Live Software Demonstration + Tagged Repository Commit (`v0.1.0-alpha`) + CI/CD & Documentation Package Verification

#### Technical & Engineering Requirements:
1. **Repository, Git Issues & Version Control Hygiene:**
   - [ ] Initialized repository (GitHub/GitLab) with `main` branch protection rules requiring at least one peer Pull Request (PR) approval before merging.
   - [ ] **Team Lead Verification:** The Team Lead must verify clean branch management using clearly labeled feature branches (`feature/*`, `chore/*`).
   - [ ] **Git Issues Integration:** Creation of GitHub/GitLab Issues for all initial implementation tasks.
   - [ ] Standardized commit messages following Conventional Commits to support automated changelog generation.
2. **Environment & Single-Command Local Orchestration:**
   - [ ] **Single-Command Setup:** Inclusion of a `docker-compose.yml` or containerized orchestration script enabling any developer to launch the complete local development stack (database, backend skeleton, frontend) with a single command (`docker compose up`).
   - [ ] Environment variable configuration using sanitized `.env.example` templates.
3. **Data Safety & Migration Scripts:**
   - [ ] Automated, reproducible database migration scripts establishing relational schemas or document structures.
   - [ ] **Down-Migration & Rollback Testing:** Every schema migration script must include a verified, executable rollback (`down`) migration script.
   - [ ] Synthetic test data seeders for populating local instances without real or sensitive data.
4. **Code Quality, Static Analysis & OOP Standards:**
   - [ ] Automated linter and static code analysis rules integrated into the CI/CD pipeline (e.g., ESLint, SonarQube, Ruff) enforcing type safety and formatting.
   - [ ] Clean, modular Object-Oriented Programming (OOP) design with proper class encapsulation and docstrings.
5. **CI/CD Infrastructure & Test Logs:**
   - [ ] Automated CI pipeline executing linting, security secret scanning (e.g., TruffleHog/GitGuardian), and unit tests on every PR.
   - [ ] Exported CI build logs and initial test execution results linked to relevant GitHub/GitLab Issues.
6. **Documentation & AI Usage Log:**
   - [ ] Comprehensive `README.md` containing local setup steps, architecture overview, and environment variables.
   - [ ] Developer onboarding guide detailing system folders and OOP design patterns.
   - [ ] **AI Usage Log (`AI_USAGE_LOG.md`):** Complete log documenting all generative AI prompts, generated code fragments, manual refactoring, and validation steps.
7. **In-Class Live Prototype Demonstration:**
   - [ ] 5–7 minute live team demonstration showcasing local orchestration, passing CI/CD pipelines, database migrations/rollbacks, and working API endpoints.

---

### Prototype 2: Midterm Alpha Prototype
* **Code & Submission Due:** Week 8 (Thursday, October 8 @ 11:59 PM CT)
* **In-Class Presentation:** Week 8 (Friday, October 9 In-Class)
* **Grade Weight:** 25%
* **Deliverable Format:** In-Person Live Software Demonstration + Tagged Repository Release (`v0.5.0-alpha`) + Automated Integration Test & Security Logs

#### Technical & Engineering Requirements:
1. **Working Midterm Alpha Build & Core MVP Integration:**
   - [ ] Implementation and merge of core MVP user stories into `main` via peer-reviewed PRs.
   - [ ] Functional integration connecting frontend UI components to backend business logic and database models.
   - [ ] **Git Issues Communication:** All test results, identified API bugs, and refactoring needs must be logged as Git Issues and linked directly to fixing PRs.
2. **Code Quality Metrics & Supply Chain Security:**
   - [ ] **Static Code Analysis Caps:** Enforcement of cognitive and cyclomatic complexity limits via static analysis tools (e.g., SonarQube/CodeClimate).
   - [ ] **Supply Chain Auditing:** Integration of automated dependency scanning (e.g., Dependabot, Snyk, `npm audit`) in CI/CD to block pull requests containing known CVEs.
3. **Authentication, OWASP Audit & Data Privacy:**
   - [ ] Secure user authentication workflows (JWT, OAuth2, session handling) with secret key encryption.
   - [ ] OWASP Top 10 security audit and vulnerability mitigations.
   - [ ] **Data Privacy Controls:** Implementation of basic PII protection, secure password hashing (Bcrypt/Argon2), and soft-delete mechanics (`deleted_at` timestamps) instead of destructive hard deletes.
4. **Automated Integration Testing & Validation Logs:**
   - [ ] Comprehensive integration test suite verifying end-to-end API response contracts and database transactions.
   - [ ] Detailed test execution logs attached to GitHub/GitLab Issues documenting pass/fail metrics (minimum 60% coverage target).
5. **Environment Toggles & Documentation Package:**
   - [ ] Implementation of environment feature flags/toggles to safely enable or disable incomplete features in staging/production.
   - [ ] Updated `README.md`, visual architecture/UML diagrams, and step-by-step developer setup guides.
   - [ ] **Team Lead Verification & AI Log:** The Team Lead must review and verify that the cumulative `AI_USAGE_LOG.md` includes all Sprint 2–3 prompts and code verification records.
6. **In-Class Live Prototype Demonstration:**
   - [ ] 8–10 minute in-person demonstration showcasing authenticated user workflows, live CRUD functionality, and active database operations.

---

### Prototype 3: Feature-Complete Beta Prototype
* **Code & Submission Due:** Week 12 (Thursday, November 5 @ 11:59 PM CT)
* **In-Class Presentation:** Week 12 (Friday, November 6 In-Class)
* **Grade Weight:** 25%
* **Deliverable Format:** In-Person Live Software Demonstration + Tagged Repository Release (`v0.9.0-beta`) + E2E QA Test Execution Suite & Bug Logs

#### Technical & Engineering Requirements:
1. **Feature-Complete Beta Release & Feature Freeze:**
   - [ ] Complete implementation of all core and secondary user features (strict **Feature Freeze** enforced following this submission).
   - [ ] All QA testing findings, bug reports, and regression fixes communicated and tracked through GitHub/GitLab Issues.
2. **Automated E2E Testing, Quality Assurance & Bug Tracking:**
   - [ ] Automated E2E browser/mobile UI test execution scripts (e.g., Cypress, Playwright, Appium) testing primary user journeys.
   - [ ] Complete QA Test Execution & Bug Tracking Log posted to Git Issues detailing edge cases tested, severity levels, and resolution status.
3. **Operations & Health Probes:**
   - [ ] Implementation of standard HTTP `/health` (liveness) and `/ready` (readiness) operational probes for service health checks.
   - [ ] Structured JSON logging (timestamp, log level, request ID, user ID) across backend services.
4. **Performance Benchmarking & Accessibility Audit:**
   - [ ] Load and stress test execution logs (e.g., k6, JMeter) recording API response latencies and server throughput under load.
   - [ ] Web Content Accessibility Guidelines (WCAG 2.1 AA) compliance audit log covering color contrast, keyboard navigation, and screen reader support.
5. **Code Maintainability & Documentation Package:**
   - [ ] **Quality OOP Code & Comments:** Industry-standard OOP formatting with comprehensive method-level annotations, parameter descriptions, and clean error handling.
   - [ ] **Developer & Maintenance Manual:** Detailed technical documentation covering system architecture, database ERD diagrams, third-party service dependencies, and guides for future developers.
   - [ ] **Team Lead Audit & AI Log:** Team Lead verification of repository cleanliness, issue closure status, and append of all Beta phase generative AI prompts in `AI_USAGE_LOG.md`.
6. **In-Class Live Prototype Demonstration:**
   - [ ] 8–10 minute live feature walkthrough demonstrating complete system resilience, edge-case handling, and end-to-end user workflows.

---

### Prototype 4: Final Production Launch & EOH Showcase
* **Final Code, Artifact & Repo Tag Due:** Week 16 (Thursday, December 3 @ 11:59 PM CT)
* **Public Showcase Event:** Week 16 (Friday, December 4 Engineering Open House Event)
* **Grade Weight:** 30%
* **Deliverable Format:** Public Showcase Presentation (2–3 Minute Elevator Pitch + Interactive Booth Demo) + Live Production Application URL + Compiled Standalone Runnable Artifact + Archived Master Release Tag (`v1.0.0-RELEASE`)

#### Technical & Engineering Requirements:
1. **Live Production Launch & Operational Observability:**
   - [ ] Application fully deployed to a live, publicly accessible production environment with custom domain and valid SSL/TLS certificates.
   - [ ] Configured liveness/readiness health probes and active production monitoring (e.g., Sentry, Datadog).
2. **Mandatory Compiled Runnable Artifact:**
   - [ ] Self-contained runnable release artifact:
     - Mobile Application package (Android `.apk`, iOS `.ipa`/TestFlight bundle).
     - Standalone Desktop binary or Containerized environment (`Docker container`, runnable executable).
3. **Repository Archival, Governance & Team Lead Certification:**
   - [ ] Final production release tagged `v1.0.0-RELEASE` on `main`.
   - [ ] **Team Lead Final Sign-Off:** The Team Lead must certify that all Git Issues have been closed or triaged, all feature branches are cleanly merged or pruned, repository integrity is maintained, and all documentation is complete.
4. **Master Documentation & Best Practices Audit:**
   - [ ] **Production README.md:** Professional documentation containing badges, live production URL, artifact download instructions, build/run steps, and user guide.
   - [ ] **Developer Maintenance Manual:** Publication-ready technical manual covering software architecture, OOP component structures, database ERD diagrams, API specifications, and contributor guidelines.
   - [ ] **Final Master AI Log:** Complete, audited `AI_USAGE_LOG.md` documenting every prompt, AI tool version, generated code segment, human refactoring, and validation test across Senior Project 2.
   - [ ] **Validation Log Archive:** Master test report compiling unit, integration, E2E, performance, security, and accessibility test results proving system reliability.
5. **Engineering Open House (EOH) Public Presentation & Defense:**
   - [ ] Delivery of an in-person public demonstration at the EOH event featuring a sharp **2–3 minute elevator pitch** covering problem space, architecture, technical innovation, and live application walkthrough for industry judges and faculty.

---

### Frequently Asked Questions & Clarifications
* **Q: Who is responsible if documentation or repo hygiene is incomplete at the deadline?**
  * *A:* The **Team Lead** is directly responsible for coordinating team submissions, verifying Git repository hygiene, and ensuring all documentation, test logs, and AI logs are fully completed before each submission deadline.
* **Q: How should test results and bug fixes be communicated within the team?**
  * *A:* All test execution failures, bug reports, and required code changes **must be logged as GitHub/GitLab Issues**. Team members must link their fixing PRs directly to those Issues for transparent tracking.
* **Q: What if our chosen framework or language has specific design patterns not mentioned here?**
  * *A:* Per the General Engineering Policy, students are expected to know and maintain the idiomatic standards and best practices of their tech stack (e.g., PEP 8 for Python, Go idiomatic error handling, React hook rules), even if not explicitly listed in these instructions.
* **Q: Do we need a complete user interface for Prototype 1?**
  * *A:* No. Prototype 1 evaluates system foundations. A skeleton UI connected to API endpoints or verified API calls demonstrated via Postman/API client alongside code verification is expected.
* **Q: How do we submit our code for the Thursday deadline?**
  * *A:* Create the corresponding release tag (e.g., `v0.1.0-alpha`) in your GitHub/GitLab main branch before Thursday at 11:59 PM CT and submit your repository link and CI/CD build run URL on Blackboard.

---

## Example AI Usage Log Template (`AI_USAGE_LOG.md`)

All teams are required to maintain a file named `AI_USAGE_LOG.md` in the root of their repository. Below is an example format that teams must follow:

```markdown
# AI Usage & Verification Log

**Project Name:** TaskFlow Capstone System
**Team Name:** DevCraft Studio
**Team Lead:** Alex Mercer (`@alexmercer`)

---

## Overview & AI Policy Compliance Statement
This repository utilizes Generative AI tools (e.g., ChatGPT, Claude, GitHub Copilot) in compliance with course AI guidelines. AI tools are used for code scaffolding, SQL migration generation, test suite generation, and documentation drafting. All AI-generated code is reviewed, refactored for Object-Oriented Programming (OOP) design standards, and verified via automated test suites prior to PR approval.

---

## Entry 1: Prototype 1 — Database Migration & Rollback Scripting
* **Date:** September 2, 2026
* **Team Member:** Jane Doe (`@janedoe`)
* **Tool Used:** Claude 3.5 Sonnet
* **Associated Git Issue:** Closes `#12` (Setup Initial PostgreSQL Schema)
* **Associated Feature Branch:** `feature/database-migrations`

### Exact Prompt Submitted:
> "Write a Knex.js SQL migration file for a PostgreSQL database. I need a 'users' table with columns for id (uuid primary key), email (unique), password_hash, role (enum: admin, user), created_at, updated_at, and a soft-delete column 'deleted_at'. Also include a corresponding down migration script to drop the table and enum type cleanly."

### AI Output Summary & Code Generated:
AI generated a Knex migration file containing `exports.up` and `exports.down` functions with table schema creation and drop statements.

### Human Review, Refactoring & Modifications Made:
* **Security & Formatting:** Added explicit check constraints on `email` format.
* **Data Safety:** Modified `deleted_at` column to default to `NULL` and added a database index on `deleted_at` to optimize soft-delete queries.
* **OOP Encapsulation:** Wrapped query builders inside a `UserRepository` data access class.

### Verification & Testing Method:
* Executed `npx knex migrate:latest` -> Table created successfully.
* Executed `npx knex migrate:rollback` -> Rollback executed without residual enum type locks.
* Passing automated unit tests logged in CI build run `#45`.

---

## Entry 2: Prototype 2 — JWT Authentication Middleware
* **Date:** September 28, 2026
* **Team Member:** John Smith (`@johnsmith`)
* **Tool Used:** GitHub Copilot & ChatGPT-4o
* **Associated Git Issue:** Closes `#28` (Implement JWT Bearer Authentication)
* **Associated Feature Branch:** `feature/jwt-auth`

### Exact Prompt Submitted:
> "Write an Express.js middleware class in TypeScript to authenticate incoming requests via JWT in the Authorization header. Extract the bearer token, verify it using process.env.JWT_SECRET, and attach the decoded user payload to request.user. If missing or invalid, return a structured JSON 401 error."

### AI Output Summary & Code Generated:
Copilot suggested a functional Express middleware function with `jsonwebtoken` verification logic.

### Human Review, Refactoring & Modifications Made:
* **Architecture Refactoring:** Converted function into a class-based `AuthMiddleware` implementing an `IMiddleware` interface following OOP principles.
* **Error Handling:** Added structured JSON error logging following the system's standard observability schema (`{ error: string, code: string, timestamp: string }`).
* **Secret Hygiene:** Ensured `JWT_SECRET` throws an explicit startup configuration error if undefined in `.env`.

### Verification & Testing Method:
* Added unit test cases testing valid tokens, expired tokens, malformed headers, and missing secrets.
* Ran Integration test suite via Jest (`npm run test:integration`) -> 100% path coverage achieved on authentication routes.

---

## Audit Certification
I certify as Team Lead that all entries above accurately represent AI usage within this project phase, all prompts have been recorded, and all code has been validated by human review and automated testing.

**Team Lead Signature:** *Alex Mercer* — **Date:** October 8, 2026