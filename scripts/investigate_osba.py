"""
Investigate OSBA (Ontario Scholastic Basketball Association) website structure.

This script inspects the OSBA website to identify:
1. Available pages and navigation structure
2. Stats/players pages
3. HTML table structure
4. Division organization (U17, U19, Prep)
5. Data availability and completeness
"""

import asyncio
import httpx
from bs4 import BeautifulSoup


async def investigate_osba():
    """Investigate OSBA website structure."""
    print("=" * 80)
    print("OSBA (Ontario Scholastic Basketball Association) Investigation")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:

        # Test 1: Main OSBA page
        print("\n[1] Testing main OSBA page...")
        try:
            url = "https://www.osba.ca"
            response = await client.get(url)
            print(f"URL: {url}")
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")
            print(f"Content Length: {len(response.text)} chars")

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract page title
                title = soup.find('title')
                print(f"Page title: {title.string if title else 'N/A'}")

                # Find navigation links
                nav_links = soup.find_all('a', href=True)
                print(f"\nTotal links found: {len(nav_links)}")

                # Look for stats/players/teams related links
                relevant_keywords = ['stats', 'player', 'team', 'schedule', 'leader',
                                      'standings', 'roster', 'division', 'league']
                relevant_links = []
                for link in nav_links:
                    href = link.get('href', '').lower()
                    text = link.get_text(strip=True).lower()
                    for keyword in relevant_keywords:
                        if keyword in href or keyword in text:
                            relevant_links.append({
                                'text': link.get_text(strip=True),
                                'href': link.get('href')
                            })
                            break

                print(f"\nRelevant links found ({len(set([l['href'] for l in relevant_links][:20]))} unique):")
                seen_hrefs = set()
                for link in relevant_links[:20]:
                    if link['href'] not in seen_hrefs:
                        print(f"  - {link['text']}: {link['href']}")
                        seen_hrefs.add(link['href'])

        except Exception as e:
            print(f"Error accessing main page: {e}")

        # Test 2: Try common basketball website patterns
        print("\n[2] Testing common URL patterns...")
        patterns = [
            "/stats",
            "/statistics",
            "/players",
            "/leaders",
            "/teams",
            "/schedule",
            "/standings",
            "/roster",
            "/division/u17",
            "/division/u19",
            "/division/prep",
            "/leagues",
            "/competitions",
        ]

        base_url = "https://www.osba.ca"
        for pattern in patterns:
            try:
                test_url = f"{base_url}{pattern}"
                response = await client.get(test_url)
                print(f"\n{pattern}: Status {response.status_code}", end="")

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    print(f" | Tables: {len(tables)}", end="")

                    # Check for player/stats content
                    if 'player' in response.text.lower() or 'stats' in response.text.lower():
                        print(" | Contains stats/player content", end="")

                    if tables:
                        # Examine first table structure
                        first_table = tables[0]
                        headers = first_table.find_all(['th', 'td'])[:20]
                        header_text = [h.get_text(strip=True) for h in headers if h.get_text(strip=True)]
                        if header_text:
                            print(f"\n    Table headers: {header_text[:10]}")

            except Exception as e:
                print(f"\n{pattern}: Error - {str(e)[:100]}")

        # Test 3: Check robots.txt
        print("\n[3] Checking robots.txt...")
        try:
            robots_url = f"{base_url}/robots.txt"
            response = await client.get(robots_url)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("Content:")
                print(response.text[:500])
        except Exception as e:
            print(f"Error: {e}")

        # Test 4: Search for API endpoints in page source
        print("\n[4] Searching for API endpoints in main page...")
        try:
            response = await client.get(base_url)
            if response.status_code == 200:
                # Look for common API patterns
                api_indicators = ['/api/', '/data/', '/json/', 'ajax', 'graphql']
                found_apis = []
                for indicator in api_indicators:
                    if indicator in response.text.lower():
                        # Try to extract the endpoint
                        import re
                        pattern = rf'["\']([^"\']*{re.escape(indicator)}[^"\']*)["\']'
                        matches = re.findall(pattern, response.text, re.IGNORECASE)
                        found_apis.extend(matches[:5])

                if found_apis:
                    print("Potential API endpoints found:")
                    for api in set(found_apis[:10]):
                        print(f"  - {api}")
                else:
                    print("No obvious API endpoints found in main page")

        except Exception as e:
            print(f"Error: {e}")

        # Test 5: Check if it's a WordPress/Wix/Squarespace site
        print("\n[5] Checking CMS platform...")
        try:
            response = await client.get(base_url)
            if response.status_code == 200:
                content = response.text.lower()
                cms_indicators = {
                    'wordpress': ['wp-content', 'wp-includes', 'wordpress'],
                    'wix': ['wix.com', 'wixsite'],
                    'squarespace': ['squarespace', 'sqsp'],
                    'shopify': ['shopify', 'cdn.shopify'],
                    'custom': []
                }

                found_cms = None
                for cms, indicators in cms_indicators.items():
                    for indicator in indicators:
                        if indicator in content:
                            found_cms = cms
                            break
                    if found_cms:
                        break

                if found_cms:
                    print(f"CMS Platform: {found_cms.upper()}")
                else:
                    print("CMS Platform: Unknown/Custom")

                # Check for React/Vue/Angular
                frameworks = ['react', 'vue', 'angular', 'next.js']
                found_frameworks = [fw for fw in frameworks if fw in content]
                if found_frameworks:
                    print(f"Frontend Framework: {', '.join(found_frameworks)}")

        except Exception as e:
            print(f"Error: {e}")

        # Test 6: Try to find actual division pages
        print("\n[6] Testing division-specific patterns...")
        division_patterns = [
            "/u17",
            "/u19",
            "/prep",
            "/divisions/u17",
            "/divisions/u19",
            "/divisions/prep",
            "/leagues/u17",
            "/leagues/u19",
            "/leagues/prep",
        ]

        for pattern in division_patterns:
            try:
                test_url = f"{base_url}{pattern}"
                response = await client.get(test_url)
                if response.status_code == 200:
                    print(f"{pattern}: SUCCESS (Status 200)")
                    soup = BeautifulSoup(response.text, 'html.parser')
                    tables = soup.find_all('table')
                    if tables:
                        print(f"  Found {len(tables)} tables")
            except Exception as e:
                pass

    print("\n" + "=" * 80)
    print("Investigation complete!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Review the relevant links found above")
    print("2. Manually visit www.osba.ca to confirm structure")
    print("3. Check if stats are available publicly or require login")
    print("4. Identify the correct URL patterns for stats pages")
    print("5. Update the OSBA adapter with actual URLs")


if __name__ == "__main__":
    asyncio.run(investigate_osba())
