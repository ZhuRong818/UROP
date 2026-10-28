"""V02b source: the frozen V02 collector in prospective mode, with the V02b run directory and window installed."""
import sys

from eventx.v7 import forecast_runtime_20261026_v02b  # noqa: F401  installs the V02b overrides
from eventx.tasks import collect_v7_forecast_runtime_20261026_v02 as frozen

if __name__ == '__main__':
    sys.argv = [sys.argv[0], '--prospective']
    frozen.main()
