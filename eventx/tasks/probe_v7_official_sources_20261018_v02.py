"""Probe the official BEA feed and DOL-hosted original BLS release copies."""
from eventx.tasks import probe_v7_official_sources_20261018 as probe
probe.URLS = [
 'https://apps.bea.gov/rss/rss.xml',
 'https://www.dol.gov/newsroom/economicdata/cpi_10142026.pdf',
 'https://www.dol.gov/newsroom/economicdata/ppi_10152026.pdf',
 'https://www.dol.gov/newsroom/economicdata/empsit_10022026.pdf',
]
if __name__=='__main__':probe.main()
