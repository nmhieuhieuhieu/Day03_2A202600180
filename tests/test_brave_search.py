# tests/test_bug3.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

# ===== Test Lớp 2: Code sanitize =====
print("=== Test Lớp 2: Code sanitize ===")

cases = [
    ('"thời tiết Đà Nẵng tháng 4"',    'thời tiết Đà Nẵng tháng 4'),
    ("'giá vé xe Sài Gòn Đà Lạt'",      'giá vé xe Sài Gòn Đà Lạt'),
    ('thời tiết Hà Nội',                 'thời tiết Hà Nội'),         # không có quotes → không đổi
    ('"khách sạn Đà Lạt "budget""',      'khách sạn Đà Lạt budget'),  # escaped quotes bên trong
]

all_pass = True
for raw, expected in cases:
    result = raw.strip().strip('"\'').replace('"', '').replace("'", '')
    status = "PASS" if result == expected else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  [{status}] Input: {raw!r}")
    print(f"         Expected: {expected!r}")
    print(f"         Got:      {result!r}")

print(f"\nLớp 2: {'✅ Tất cả PASS' if all_pass else '❌ Có FAIL'}")

# ===== Test Lớp 1: Brave Search thực tế =====
print("\n=== Test Lớp 1: Brave Search thực tế ===")
from src.tools.tools import web_search

# Query có quotes → expect "No results found." (BUG chưa fix ở prompt)
q_bad  = '"thời tiết Đà Nẵng tháng 4 2026"'
# Query không có quotes → expect kết quả thực
q_good = 'thời tiết Đà Nẵng tháng 4 2026'

r_bad  = web_search(q_bad)
r_good = web_search(q_good)

print(f"\n[Query có quotes]: {q_bad!r}")
print(f"  Kết quả: {r_bad[:80]}...")

print(f"\n[Query không quotes]: {q_good!r}")
print(f"  Kết quả: {r_good[:80]}...")

if r_bad == "No results found." and r_good != "No results found.":
    print("\n✅ Confirmed Bug #3: Quoted query fails, plain text query works")
elif r_bad != "No results found.":
    print("\n⚠️  Brave đã handle được quoted query (hoặc API trả về kết quả khác)")
