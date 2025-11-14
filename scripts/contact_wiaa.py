#!/usr/bin/env python
"""
WIAA Contact Helper

Assists with contacting WIAA to request official data access. Pre-fills
the email template from WIAA_DATA_REQUEST_TEMPLATE.md with project details
and provides guidance on where to send the request.

Usage:
    # Show contact information and email preview
    python scripts/contact_wiaa.py

    # Generate email text (copy to clipboard ready)
    python scripts/contact_wiaa.py --generate

    # Show full template with instructions
    python scripts/contact_wiaa.py --full-template

Benefits:
    - Pre-filled email template ready to send
    - Contact information guidance
    - Follow-up strategy included
    - Path to Phase 14.7 (API integration) if approved
"""

import argparse
import sys
from pathlib import Path

# Paths
TEMPLATE_PATH = Path("docs/WIAA_DATA_REQUEST_TEMPLATE.md")
PROJECT_ROOT = Path(__file__).parent.parent


def get_project_info() -> dict:
    """Get project information for template."""
    # Try to detect git remote URL
    import subprocess
    try:
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            git_url = result.stdout.strip()
            # Convert git URL to GitHub web URL
            if "github.com" in git_url:
                repo_url = git_url.replace("git@github.com:", "https://github.com/")
                repo_url = repo_url.replace(".git", "")
            else:
                repo_url = git_url
        else:
            repo_url = "[YOUR GITHUB URL]"
    except:
        repo_url = "[YOUR GITHUB URL]"

    return {
        "project_name": "High School Basketball Players MCP",
        "repo_url": repo_url,
        "project_description": "Open-source basketball analytics aggregating multi-state HS data"
    }


def show_contact_info():
    """Display WIAA contact information and guidance."""
    print("\n" + "="*80)
    print("WIAA CONTACT INFORMATION")
    print("="*80 + "\n")

    print("Where to find WIAA contacts:")
    print()
    print("1. WIAA Website: https://www.wiaawi.org/")
    print("   Look for:")
    print("   - 'Contact Us' page")
    print("   - 'Media Relations' or 'Communications' department")
    print("   - 'Statistics' or 'IT/Web Services' contacts")
    print()
    print("2. Likely email patterns:")
    print("   - media@wiaawi.org")
    print("   - stats@wiaawi.org")
    print("   - info@wiaawi.org")
    print()
    print("3. Phone contact:")
    print("   - Call main office and ask for appropriate department")
    print("   - Mention: 'Data access for non-commercial research project'")
    print()
    print("4. Best departments to contact:")
    print("   - Communications/Media Relations (for data sharing policy)")
    print("   - IT/Technology (for technical implementation)")
    print("   - Statistics/Records (for historical data)")
    print()


def generate_email():
    """Generate pre-filled email text."""
    info = get_project_info()

    print("\n" + "="*80)
    print("EMAIL TEMPLATE (Copy and customize below)")
    print("="*80 + "\n")

    email = f"""Subject: Request for Basketball Tournament Bracket Data Access

Dear WIAA Team,

I am writing to request access to historical and ongoing Wisconsin high school
basketball tournament bracket data for an open-source analytics project.

**Project Overview:**
I am developing open-source tools to aggregate and analyze high school basketball
data from multiple states and data sources. The goal is to provide researchers,
journalists, and basketball enthusiasts with comprehensive historical statistics
and trend analysis.

The project repository is publicly available at: {info['repo_url']}

**Current Approach:**
I am currently manually downloading HTML bracket files from your public website
at halftime.wiaawi.org. However, I want to ensure I'm respecting your terms of
service and not creating unnecessary load on your servers through repeated manual
downloads.

**What I'm Requesting:**
I would greatly appreciate if WIAA could provide any of the following:

1. **Historical data dump** (preferred):
   - All WIAA basketball tournament brackets for 2015-present in CSV/JSON/XML
   - Data fields: Game date, teams, scores, division, round, location

2. **API access** (if available):
   - Simple HTTP endpoint to fetch bracket data by year/division
   - Can be limited to authenticated access with rate limiting
   - Example: GET /api/basketball/brackets/2024/division/1

3. **Scheduled data exports**:
   - Weekly or monthly CSV/JSON exports during tournament season
   - Delivered via email, FTP, or public URL
   - Historical backfill for 2015-present

4. **Permission for programmatic access**:
   - If the above aren't feasible, explicit permission to make scripted HTTP requests
   - I would implement rate limiting (e.g., 1 request per 10 seconds)
   - Downloads would only occur once per tournament season

**My Commitments:**
- **Attribution**: I will clearly credit WIAA as the data source in all outputs
- **Non-commercial**: This is a research/educational project with no commercial use
- **Respect terms**: I will abide by any usage constraints or licensing requirements
- **Data caching**: I will cache data locally to minimize repeat requests
- **Transparency**: The project is open-source, so data usage is fully auditable

**Benefits to WIAA:**
- Increased visibility for Wisconsin high school basketball
- Proper attribution in analytics and research
- Reduced server load (one structured export vs. multiple browser sessions)
- Partnership with open-source community

**Technical Details:**
- Coverage goal: 10 years × 2 genders × 4 divisions = 80 tournament brackets
- Update frequency: Once per year (during/after tournament season)
- Data retention: Historical archive for trend analysis

I am happy to discuss technical implementation, data formats, or any restrictions
you'd like to place on the data usage. I can also provide progress reports or
demonstrations of the analytics tools being built.

Thank you for considering this request. I look forward to hearing from you and
potentially partnering with WIAA to make Wisconsin high school basketball data
more accessible for research and analysis.

Best regards,

[YOUR NAME]
[YOUR EMAIL]
[YOUR PHONE - optional]
[GITHUB PROFILE - optional]
"""

    print(email)
    print()
    print("="*80)
    print("NEXT STEPS:")
    print("="*80)
    print()
    print("1. Copy the email text above")
    print("2. Customize with your contact information")
    print("3. Find appropriate WIAA contact (see --contact-info)")
    print("4. Send the email")
    print("5. If approved → Run Phase 14.7 to integrate API")
    print()


def show_full_template():
    """Display full template from markdown file."""
    if not TEMPLATE_PATH.exists():
        print(f"❌ Template not found: {TEMPLATE_PATH}")
        print("   Make sure you're running from the repository root")
        return

    print("\n" + "="*80)
    print(f"FULL TEMPLATE: {TEMPLATE_PATH}")
    print("="*80 + "\n")

    with TEMPLATE_PATH.open("r", encoding="utf-8") as f:
        content = f.read()
        print(content)


def main():
    parser = argparse.ArgumentParser(
        description="WIAA Contact Helper - Assist with requesting official data access",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show contact information
  python scripts/contact_wiaa.py --contact-info

  # Generate email template
  python scripts/contact_wiaa.py --generate

  # Show full template with integration plan
  python scripts/contact_wiaa.py --full-template

  # All information
  python scripts/contact_wiaa.py --contact-info --generate

Workflow:
  1. Run --contact-info to find where to send email
  2. Run --generate to get pre-filled email text
  3. Customize email with your details
  4. Send to appropriate WIAA contact
  5. If approved, integration plan is in docs/WIAA_DATA_REQUEST_TEMPLATE.md
        """
    )

    parser.add_argument(
        "--contact-info",
        action="store_true",
        help="Show WIAA contact information and guidance"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate pre-filled email text"
    )
    parser.add_argument(
        "--full-template",
        action="store_true",
        help="Show complete template from WIAA_DATA_REQUEST_TEMPLATE.md"
    )

    args = parser.parse_args()

    # Default: show everything
    if not any([args.contact_info, args.generate, args.full_template]):
        args.contact_info = True
        args.generate = True

    if args.contact_info:
        show_contact_info()

    if args.generate:
        generate_email()

    if args.full_template:
        show_full_template()


if __name__ == "__main__":
    main()
