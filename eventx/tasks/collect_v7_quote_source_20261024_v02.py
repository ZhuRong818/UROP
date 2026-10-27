"""New bounded source run for the separately versioned quote forecast service."""
import asyncio
import signal
from eventx.tasks import collect_v7_expansion_pilot_20261024 as expansion
from eventx.tasks import collect_v7_direct_pilot_20261022_v03 as transport
from eventx.tasks import audit_v7_direct_pilot_20261022_v03 as auditor
from eventx.tasks.prepare_v7_quote_source_20261024_v02 import BASE,RELEASE

transport.BASE=auditor.BASE=BASE
transport.RELEASE=auditor.RELEASE=RELEASE

def main():
    c=expansion.Capture()
    def stop(*_):c.stopping=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    asyncio.run(c.run())

if __name__=='__main__':main()
