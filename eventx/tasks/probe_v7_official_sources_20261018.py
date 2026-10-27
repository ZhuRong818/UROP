"""Bounded, original-source endpoint discovery; no model or market payloads."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import uuid
import httpx

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data/v7/official_source_capture_20261018'
URLS = [
 'https://www.bls.gov/news.release/cpi.nr0.htm',
 'https://www.bls.gov/news.release/ppi.nr0.htm',
 'https://www.bls.gov/news.release/empsit.nr0.htm',
 'https://www.bls.gov/feed/',
 'https://www.federalreserve.gov/feeds/press_monetary.xml',
 'https://www.federalreserve.gov/feeds/speeches_and_testimony.xml',
 'https://www.federalreserve.gov/feeds/feeds.htm',
 'https://www.bea.gov/news/rss.xml',
 'https://www.bea.gov/news/current-releases',
 'https://www.bea.gov/news/schedule',
]

class Links(HTMLParser):
 def __init__(self): super().__init__(); self.hrefs=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   value=dict(attrs).get('href','')
   if any(x in value for x in ['.rss','.xml','personal-income','domestic-product']):self.hrefs.append(value)

def main():
 out=BASE/'probes'/uuid.uuid4().hex;out.mkdir(parents=True)
 (out/'request_receipt.json').write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'urls':URLS,'purpose':'setup endpoint discovery; first observations are not timely historical releases'},indent=2))
 def get(pair):
  i,url=pair; r={'url':url,'started_at':datetime.now(timezone.utc).isoformat()}
  try:
   with httpx.Client(timeout=20,follow_redirects=True,headers={'User-Agent':'EventXResearchCapture/1.0 (public economic releases; no trading)'}) as client:
    response=client.get(url);body=response.content
   (out/f'{i:02}.body').write_bytes(body)
   parser=Links();parser.feed(response.text)
   r.update(status=response.status_code,final_url=str(response.url),bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),content_type=response.headers.get('content-type'),candidate_links=parser.hrefs[:35])
  except Exception as exc:r.update(error_type=type(exc).__name__,error=str(exc)[:160])
  r['ended_at']=datetime.now(timezone.utc).isoformat();return r
 with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(get,enumerate(URLS)))
 (out/'responses.json').write_text(json.dumps(rows,indent=2))
 print(json.dumps({'directory':str(out.relative_to(ROOT)),'responses':rows},indent=2))
if __name__=='__main__':main()
