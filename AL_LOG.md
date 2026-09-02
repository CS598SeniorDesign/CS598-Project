# AI Usage & Verification Log

**Project Name:** QuestLog
**Team Name:** The Meeples
**Team Lead:** N/A

---

## Overview & AI Policy Compliance Statement

This repository utilizes Generative AI tools (e.g., ChatGPT, Claude, GitHub Copilot) in compliance with course AI guidelines. AI tools are used for code scaffolding, SQL migration generation, test suite generation, and documentation drafting. All AI-generated code is reviewed, refactored for Object-Oriented Programming (OOP) design standards, and verified via automated test suites prior to PR approval.

---

## Entry Template (copy for new entries)

## Entry N: [Prototype #] — [Short Feature Description]

* **Date:**
* **Team Member:** (`@handle`)
* **Tool Used:** [Tool]
* **Associated Git Issue:** Closes `#`
* **Associated Feature Branch:** `feature/...`

### Exact Prompt Submitted:

> "..."

### AI Output Summary & Code Generated:


### Human Review, Refactoring & Modifications Made:

*
*

### Verification & Testing Method:

*
*

---

## Audit Certification

I certify as Team Lead that all entries above accurately represent AI usage within this project phase, all prompts have been recorded, and all code has been validated by human review and automated testing.

**Team Lead Signature:** *[Team Lead]* — **Date:** [Date]

---
## Entry 42000: Example

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