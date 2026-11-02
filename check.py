#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import date, datetime
from pypdf import PdfReader
from itertools import zip_longest

PERIODS = (1, 3, 6, 12, 24)
METRIC_DEFINITIONS = [
   f"Chex inquiries in the last {period} month{'s' if period > 1 else ''}"
   for period in PERIODS
]


def generate_stats(inquiries: List[Tuple[str, str]]) -> Dict[int, int]:
   counts = {period: 0 for period in PERIODS}
   today = date.today()

   for _, inquiry_date in inquiries:
       inquiry_date = datetime.strptime(inquiry_date, "%m/%d/%Y").date()
       months = (today - inquiry_date).days/30
    #    months = math.ceil(months)
       period = next((p for p in counts if months < p), None)
       if period:
           counts[period] += 1

   # each inquiry lands in exactly one bucket, so roll them up to make the periods inclusive
   running = 0
   for period in counts:
       running += counts[period]
       counts[period] = running

   return counts


def parse_inquiries(text: str) -> List[Tuple[str, str]]:
   start = re.search(r"Inquiries\s+Viewed\s+By\s+Others", text, re.IGNORECASE)
   if not start:
       raise ValueError("Could not find the 'Inquiries Viewed By Others' section.")
   end = re.search(r"Inquiries\s+Viewed\s+Only\s+By\s+You", text[start.end():], re.IGNORECASE)
   if not end:
       raise ValueError("Could not find the end of the bank inquiry section.")

   section = text[start.end():start.end() + end.start()]
   entries = re.split(r"\bInquirer\s*:\s*", section, flags=re.IGNORECASE)[1:]
   inquiries = []
   for entry in entries:
       name_match = re.match(r"\s*([^;]+);", entry)
       date_match = re.search(r"\bInquiry\s+Date\s*:\s*(\d{1,2}/\d{1,2}/\d{4})", entry, re.IGNORECASE)
       if not name_match or not date_match:
           raise ValueError("Could not parse a bank inquiry; no CSV was written.")
       inquiries.append((name_match.group(1).title(), date_match.group(1)))
   if not inquiries:
       raise ValueError("No bank inquiries found; no CSV was written.")
   return inquiries


def main() -> None:
   parser = argparse.ArgumentParser(description=__doc__)
   parser.add_argument("pdf", nargs="?", type=Path, default=Path("document-1.pdf"))
   parser.add_argument("csv", nargs="?", type=Path, default=Path("chexsystems_inquiries.csv"))
   args = parser.parse_args()

   try:
       reader = PdfReader(args.pdf)
       text = "\n".join(page.extract_text() or "" for page in reader.pages)
       inquiries = parse_inquiries(text)
       stats = generate_stats(inquiries)

       stat_rows = [
           (f"X/{period}", count, definition)
           for (period, count), definition in zip(stats.items(), METRIC_DEFINITIONS)
       ]

       forum_easy_line_to_paste = " ".join([f"{count}/{period}" for period, count in stats.items()])

       # blank rows for readability
       stat_rows.append(("", "", ""))
       stat_rows.append(("Easy line to copy paste to forums", "", forum_easy_line_to_paste))

       with args.csv.open("w", encoding="utf-8", newline="") as output:
               writer = csv.writer(output)
               writer.writerow(("Bank name", "Date pulled","", "Metric", "Count", "Explination"))
               for inquiry, stat in zip_longest(inquiries, stat_rows, fillvalue=("", "")):
                   writer.writerow(inquiry + ("",) + stat)

   except (OSError, ValueError) as error:
       parser.exit(1, f"Error: {error}\n")
   print(f"Wrote {len(inquiries)} inquiries to {args.csv}")


if __name__ == "__main__":
   main()

