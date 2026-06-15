import re
import subprocess
import sys
import tempfile
from pathlib import Path

from config import settings


def run_sherlock(username: str) -> dict:
  """Sherlock CLI ile kullanıcı adı taraması."""
  try:
    with tempfile.TemporaryDirectory() as tmpdir:
      output_file = Path(tmpdir) / "sherlock_out.txt"
      result = subprocess.run(
        [
          sys.executable,
          "-m",
          "sherlock",
          username,
          "--output",
          str(output_file),
          "--timeout",
          "15",
          "--print-found",
        ],
        capture_output=True,
        text=True,
        timeout=settings.sherlock_timeout,
      )
      stdout = result.stdout or ""
      stderr = result.stderr or ""
      if output_file.exists():
        stdout += "\n" + output_file.read_text(encoding="utf-8", errors="ignore")
      parsed = parse_sherlock_output(stdout)
      parsed["source"] = "sherlock"
      if result.returncode != 0 and not parsed["found"] and stderr:
        parsed["warning"] = stderr.strip()[:200]
      return parsed
  except subprocess.TimeoutExpired:
    return {"error": "Sherlock zaman aşımına uğradı", "found": [], "source": "sherlock"}
  except Exception as e:
    return {"error": str(e), "found": [], "source": "sherlock"}


def parse_sherlock_output(raw: str) -> dict:
  found = []
  not_found = []
  seen_urls = set()

  for line in raw.split("\n"):
    if "[+]" in line:
      url_match = re.search(r"https?://\S+", line)
      if url_match:
        url = url_match.group().rstrip(")")
        if url not in seen_urls:
          seen_urls.add(url)
          platform = line.split("[+]")[-1].strip().split(":")[0].strip()
          found.append({"platform": platform, "url": url, "source": "sherlock"})
    elif "[-]" in line:
      platform = line.split("[-]")[-1].strip()
      if platform:
        not_found.append(platform)

  return {
    "found": found,
    "found_count": len(found),
    "not_found_count": len(not_found),
    "total_checked": len(found) + len(not_found),
  }
