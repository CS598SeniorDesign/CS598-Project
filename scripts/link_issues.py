#!/usr/bin/env python3
"""
GitHub Issue Linking Utility

This script helps manage linking CI test results to GitHub Issues.
It provides utilities for:
1. Creating issues from test failures
2. Linking PRs to existing issues
3. Generating issue templates with CI results
"""

import json
import os
import sys
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: requests library not found. Install with: pip install requests")
    sys.exit(1)


class GitHubIssueLinkManager:
    """Manage linking CI test results to GitHub Issues."""

    def __init__(self, repo_owner: str, repo_name: str, token: Optional[str] = None):
        """
        Initialize the manager.

        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            token: GitHub API token (defaults to GITHUB_TOKEN env var)
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}" if self.token else "",
        }

    def create_test_failure_issue(
        self,
        test_name: str,
        error_message: str,
        run_id: str,
        labels: list[str] = None,
        assignee: Optional[str] = None,
    ) -> dict:
        """
        Create a GitHub issue for a test failure.

        Args:
            test_name: Name of the failed test
            error_message: Error message from the test
            run_id: GitHub Actions run ID
            labels: List of labels to add
            assignee: GitHub username to assign

        Returns:
            Issue data from GitHub API
        """
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

        labels = labels or ["bug", "test-failure"]
        run_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}"

        issue_data = {
            "title": f"Test Failure: {test_name}",
            "body": f"""## Test Failure Report

**Test Name**: `{test_name}`

**Error Message**:
```
{error_message}
```

**CI Run**: [View Details]({run_url})

**Date**: {datetime.now().isoformat()}

---
*This issue was automatically created by the CI/CD pipeline.*
""",
            "labels": labels,
        }

        if assignee:
            issue_data["assignee"] = assignee

        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues"
        response = requests.post(url, json=issue_data, headers=self.headers)

        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(
                f"Failed to create issue: {response.status_code} - {response.text}"
            )

    def link_pr_to_issue(
        self, pr_number: int, issue_number: int
    ) -> dict:
        """
        Link a PR to an issue using 'Fixes #' syntax.

        Args:
            pr_number: Pull request number
            issue_number: Issue number to link

        Returns:
            Updated PR data
        """
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls/{pr_number}"
        response = requests.get(url, headers=self.headers)
        pr_data = response.json()

        # Update body to include Fixes syntax if not already present
        current_body = pr_data.get("body", "")
        fixes_text = f"Fixes #{issue_number}"

        if f"Fixes #{issue_number}" not in current_body:
            updated_body = f"{current_body}\n\n{fixes_text}".strip()
            update_data = {"body": updated_body}

            response = requests.patch(url, json=update_data, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(
                    f"Failed to update PR: {response.status_code} - {response.text}"
                )

        return pr_data

    def generate_issue_template(
        self,
        test_name: str,
        error_message: str,
        run_id: str,
        test_output: Optional[str] = None,
    ) -> str:
        """
        Generate an issue template for manual creation.

        Args:
            test_name: Name of the failed test
            error_message: Error message from the test
            run_id: GitHub Actions run ID
            test_output: Full test output

        Returns:
            Markdown formatted issue template
        """
        run_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}"

        template = f"""## Test Failure Report

**Test Name**: `{test_name}`

**Status**: ❌ Failed

**Error Message**:
```
{error_message}
```

**CI Run**: [View Details]({run_url})

**Date**: {datetime.now().isoformat()}
"""

        if test_output:
            template += f"""

**Full Test Output**:
```
{test_output}
```
"""

        template += """

## Action Items
- [ ] Reproduce failure locally
- [ ] Fix the bug
- [ ] Add regression test
- [ ] Link PR with `Fixes #{issue_number}`

---
*This issue was generated from CI test results.*
"""
        return template

    def get_issue_details(self, issue_number: int) -> dict:
        """
        Get details of a specific issue.

        Args:
            issue_number: Issue number to retrieve

        Returns:
            Issue data from GitHub API
        """
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to get issue: {response.status_code} - {response.text}"
            )

    def list_linked_prs(self, issue_number: int) -> list[dict]:
        """
        List all PRs linked to an issue.

        Args:
            issue_number: Issue number to check

        Returns:
            List of linked PR data
        """
        issue = self.get_issue_details(issue_number)

        # Get timeline events to find PR references
        url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/timeline"
        response = requests.get(
            url,
            headers={
                **self.headers,
                "Accept": "application/vnd.github.v3.raw+json",
            },
        )

        if response.status_code == 200:
            events = response.json()
            pr_events = [e for e in events if e.get("event") == "cross-referenced"]
            return pr_events
        else:
            return []


def main():
    """CLI interface for the issue linker."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage linking CI test results to GitHub Issues"
    )
    parser.add_argument("--repo-owner", required=True, help="GitHub repository owner")
    parser.add_argument("--repo-name", required=True, help="GitHub repository name")
    parser.add_argument(
        "--test-name", help="Name of the failed test (for --create-issue)"
    )
    parser.add_argument(
        "--error-message", help="Error message from test (for --create-issue)"
    )
    parser.add_argument(
        "--run-id", help="GitHub Actions run ID (for issue creation/templates)"
    )
    parser.add_argument(
        "--pr-number", type=int, help="PR number to link (for --link-pr)"
    )
    parser.add_argument("--issue-number", type=int, help="Issue number to link to")
    parser.add_argument(
        "--assignee", help="GitHub username to assign issue to (optional)"
    )
    parser.add_argument("--labels", nargs="+", help="Labels to add to issue")
    parser.add_argument(
        "--create-issue",
        action="store_true",
        help="Create issue from test failure",
    )
    parser.add_argument(
        "--link-pr",
        action="store_true",
        help="Link PR to issue",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Generate issue template",
    )
    parser.add_argument(
        "--get-issue",
        action="store_true",
        help="Get issue details",
    )
    parser.add_argument(
        "--list-prs",
        action="store_true",
        help="List PRs linked to issue",
    )

    args = parser.parse_args()

    manager = GitHubIssueLinkManager(args.repo_owner, args.repo_name)

    try:
        if args.create_issue:
            if not args.test_name or not args.error_message or not args.run_id:
                parser.error(
                    "--create-issue requires --test-name, --error-message, and --run-id"
                )
            result = manager.create_test_failure_issue(
                args.test_name, args.error_message, args.run_id, args.labels, args.assignee
            )
            print(json.dumps(result, indent=2))
            print(f"\n✅ Issue created: #{result['number']}")

        elif args.link_pr:
            if not args.pr_number or not args.issue_number:
                parser.error("--link-pr requires --pr-number and --issue-number")
            result = manager.link_pr_to_issue(args.pr_number, args.issue_number)
            print(f"✅ PR #{args.pr_number} linked to Issue #{args.issue_number}")

        elif args.template:
            if not args.test_name or not args.error_message or not args.run_id:
                parser.error(
                    "--template requires --test-name, --error-message, and --run-id"
                )
            template = manager.generate_issue_template(
                args.test_name, args.error_message, args.run_id
            )
            print(template)

        elif args.get_issue:
            if not args.issue_number:
                parser.error("--get-issue requires --issue-number")
            issue = manager.get_issue_details(args.issue_number)
            print(json.dumps(issue, indent=2))

        elif args.list_prs:
            if not args.issue_number:
                parser.error("--list-prs requires --issue-number")
            prs = manager.list_linked_prs(args.issue_number)
            if prs:
                print(f"Found {len(prs)} linked PR(s)")
                for pr in prs:
                    print(f"  - {pr}")
            else:
                print("No linked PRs found")

        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
