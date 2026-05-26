import xml.etree.ElementTree as ET
import re
from pathlib import Path

NS = {'page': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15'}
ET.register_namespace('', NS['page'])

xml_file = Path("Anonymous - 1695 - Reasons humbly offer'd, why a duty should not be laid on sugars_page_2.xml")
tree = ET.parse(xml_file)
root = tree.getroot()

print("Checking for hyphenated words...")
count = 0

for text_region in root.findall('.//page:TextRegion', NS):
    text_lines = text_region.findall('.//page:TextLine', NS)
    print(f"\nFound {len(text_lines)} text lines in region")

    for i in range(len(text_lines) - 1):
        current_line = text_lines[i]
        next_line = text_lines[i + 1]

        current_unicode = current_line.find('.//page:Unicode', NS)
        next_unicode = next_line.find('.//page:Unicode', NS)

        if current_unicode is None or next_unicode is None:
            continue

        current_text = current_unicode.text or ''
        next_text = next_unicode.text or ''

        # Check for hyphen at end
        if match := re.search(r'(\S+)-\s*$', current_text):
            word_fragment = match.group(1)
            if next_match := re.match(r'^(\S+)', next_text):
                continuation = next_match.group(1)
                count += 1
                print(f"\n  Line {i}: '{current_text[-30:]}'")
                print(f"  Line {i+1}: '{next_text[:30]}'")
                print(f"  Found: {word_fragment}- {continuation}")

print(f"\n\nTotal hyphenated words found: {count}")
