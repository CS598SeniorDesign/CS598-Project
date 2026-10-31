# Prototype 3 QA Test Execution & Bug Tracking Log

## Scope

Prototype 3 validates the primary browser journeys on desktop Chromium and an
iPhone 13 emulation profile:

- landing-page navigation
- signup validation and API error presentation
- login failure handling
- catalog search, result rendering, and clearing
- library filtering and empty-state behavior

The suite is deterministic: backend-dependent journeys stub the browser's
`/_allauth` and `/api/v1/games` responses, so failures represent frontend
regressions rather than missing seeded accounts or third-party catalog data.

## Execution record

| ID | Edge case / journey | Severity | Expected result | Status |
| --- | --- | --- | --- | --- |
| QA-001 | Landing page exposes Login and Sign Up entry points | Medium | Both links are visible and target the correct routes | Passed — No defect |
| QA-002 | Signup submitted with an existing email | High | Backend error is shown as an accessible alert; user remains on signup | Passed — No defect |
| QA-003 | Signup button with required fields empty | Medium | Browser validation prevents a request | Passed — No defect |
| QA-004 | Login with invalid credentials | High | A safe, actionable error is shown; password is not exposed | Passed — No defect |
| QA-005 | Catalog search returns one game with no thumbnail | Medium | Result renders with the no-image fallback and rating | Passed — No defect |
| QA-006 | Catalog search is cleared after results load | Low | Query/results reset to the initial prompt | Passed — No defect |
| QA-007 | Library filter matches no games | Low | Empty-state message is visible | Passed — No defect |
| QA-008 | Primary journeys at mobile viewport | High | Same assertions pass under iPhone 13 emulation | Passed — No defect |

## Bug tracking

No unresolved defects were found by the automated cases above. All eight cases
passed on both desktop and mobile projects. The test artifacts are uploaded by
CI as `e2e-test-report` and `e2e-test-log`.

When a pull request body references an issue using a closing keyword such as
`Fixed #<number>` or `Closed #<number>`, the existing CI validation job posts
its generated report to that GitHub Issue. If no closing issue reference is
provided, CI creates one QA tracking issue and posts the report there. Issue
creation is limited to pull-request runs so repeated branch pushes do not
create duplicate issues.

## Reproduction

From `frontend/`:

```bash
npm ci
npx playwright install --with-deps chromium
npm run e2e
```

For a headed local run:

```bash
npm run e2e:headed
```
