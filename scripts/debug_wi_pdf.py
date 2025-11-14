"""
Debug script to inspect Wisconsin WIAA Halftime PDF structure.

This script downloads and analyzes a sample PDF to understand its structure
and determine the best parsing approach.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def inspect_pdf():
    """Inspect a sample Wisconsin PDF."""
    import pdfplumber
    from src.datasources.us.wisconsin_wiaa import WisconsinWIAADataSource

    # Initialize adapter
    adapter = WisconsinWIAADataSource()

    # Test PDF URL - Division 1, Sections 1-2
    pdf_url = "https://halftime.wiaawi.org/CustomApps/Tournaments/Brackets/PDF/2024_Basketball_Boys_Div1_Sec1_2.pdf"

    print(f"Fetching PDF: {pdf_url}")

    # Fetch PDF
    try:
        status, content, headers = await adapter.http_get(pdf_url, timeout=30.0)

        if status != 200:
            print(f"Failed to fetch PDF: HTTP {status}")
            return

        print(f"Downloaded PDF: {len(content)} bytes")
        print(f"Headers: {dict(headers)}")

        # Save PDF for inspection
        debug_dir = project_root / "data" / "debug" / "pdfs"
        debug_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = debug_dir / "wi_sample.pdf"
        with open(pdf_path, "wb") as f:
            f.write(content)
        print(f"Saved PDF to: {pdf_path}")

        # Inspect with pdfplumber
        print("\n" + "="*80)
        print("PDF STRUCTURE ANALYSIS")
        print("="*80)

        import io
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            print(f"PDF metadata: {pdf.metadata}")

            # Inspect first page
            if pdf.pages:
                page = pdf.pages[0]
                print(f"\nPage 1 dimensions: {page.width} x {page.height}")

                # Try text extraction
                text = page.extract_text()
                if text:
                    print(f"\nExtracted text ({len(text)} chars):")
                    print("First 500 chars:")
                    print(text[:500])
                else:
                    print("\nNo text extracted - checking for images...")

                # Check for images
                if hasattr(page, 'images'):
                    print(f"Images found: {len(page.images)}")

                # Check for other objects
                if hasattr(page, 'chars'):
                    print(f"Characters found: {len(page.chars)}")
                if hasattr(page, 'rects'):
                    print(f"Rectangles found: {len(page.rects)}")
                if hasattr(page, 'lines'):
                    print(f"Lines found: {len(page.lines)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(inspect_pdf())
