"""V02b run: the frozen V02 run task, run with the V02b run directory and window installed."""

from eventx.v7 import forecast_runtime_20261026_v02b  # noqa: F401  installs the V02b overrides
from eventx.tasks import run_v7_forecast_runtime_20261026_v02 as frozen

if __name__ == '__main__':
    frozen.main()
