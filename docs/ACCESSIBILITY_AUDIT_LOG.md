# WCAG 2.1 AA Accessibility Audit Log

## Scope

The audit covers the primary browser journeys on desktop Chromium and the
mobile viewport project:

- landing page
- signup
- login
- catalog search
- library filtering

Automated checks use axe-core through the Playwright accessibility suite.
Keyboard and screen-reader checks require human verification because automated
DOM checks cannot confirm the quality of spoken announcements.

## Audit matrix

| ID | WCAG area | Test method | Result | Follow-up |
| --- | --- | --- | --- | --- |
| A11Y-001 | Color contrast (1.4.3) | axe contrast rules on primary pages | Automated pass — no serious/critical violations | Review any future color changes |
| A11Y-002 | Keyboard navigation (2.1.1) | Playwright tab-order smoke test; manual journey review pending | Automated pass — manual review pending | Confirm visible focus and logical order |
| A11Y-003 | Focus visibility (2.4.7) | Keyboard-only browser review | Pending manual review | Record any hidden focus indicator |
| A11Y-004 | Labels and names (1.3.1, 4.1.2) | axe labels/names rules | Automated pass — no serious/critical violations | Fix any future unlabeled controls |
| A11Y-005 | Screen-reader structure (1.3.1) | Manual NVDA/VoiceOver pass | Pending manual review | Verify headings, landmarks, alerts, and link names |
| A11Y-006 | Error/status announcements (4.1.3) | Manual screen-reader review of login/signup errors | Pending manual review | Confirm errors are announced once and in context |

## Execution commands

From `frontend/`:

```bash
npx playwright test e2e/accessibility.spec.ts
```

The generated HTML report is written to `frontend/playwright-report/`.

Latest automated execution: **12/12 checks passed** across desktop Chromium and
iPhone 13 Chromium emulation. Manual keyboard and screen-reader review remains
pending.

## Exit criteria

The audit is complete when:

1. Automated axe checks have no serious or critical violations.
2. Keyboard navigation reaches every interactive control in a logical order.
3. Focus remains visible at every step.
4. A screen reader announces page headings, navigation landmarks, form labels,
   validation errors, and dynamic status messages.
5. Any exception has an owner, severity, reproduction steps, and resolution
   status recorded in this log or a linked GitHub Issue.
