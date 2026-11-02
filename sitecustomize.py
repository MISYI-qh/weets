import os, sys
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_applibs")
if _p not in sys.path:
    sys.path.append(_p)
