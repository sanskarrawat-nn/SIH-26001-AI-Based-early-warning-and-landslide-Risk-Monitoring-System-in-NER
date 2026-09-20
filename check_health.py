"""Quick health check utility for NER-LEWS launcher."""
import sys
import time
import urllib.request

def wait_for_url(url: str, timeout_sec: int = 30, interval: float = 0.5) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'NER-LEWS-Launcher'})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(interval)
    return False

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000/health'
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    ready = wait_for_url(target, timeout_sec=timeout)
    sys.exit(0 if ready else 1)
