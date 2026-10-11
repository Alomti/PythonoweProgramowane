import sys
from pathlib import Path
pp = Path(__file__).resolve().parents[2]
if str(pp) not in sys.path:
    sys.path.insert(0,str(pp))
