"""Audited bounded Parquet column reads from immutable HTTP range objects."""
import hashlib
import io
import json
import re
import httpx
import pyarrow.parquet as pq
from eventx.tasks.discover_v7_direct_pilot_20261022 import now,write

class RangeStore:
    def __init__(self,out,budget=96*1024*1024):
        self.out=out;self.out.mkdir(parents=True,exist_ok=True);self.budget=budget;self.total=0
        self.client=httpx.Client(timeout=30,follow_redirects=True,headers={'Accept-Encoding':'identity'})
        self.receipts=[];self.objects={}
    def log(self,r):
        self.receipts.append(r)
        with (self.out/'requests.jsonl').open('a') as f:f.write(json.dumps(r,sort_keys=True)+'\n')
    def head(self,url):
        r={'at':now().isoformat(),'method':'HEAD','url':url}
        try:
            response=self.client.head(url);r.update(http_status=response.status_code);response.raise_for_status()
            r.update(size=int(response.headers['content-length']),etag=response.headers.get('etag'),accept_ranges=response.headers.get('accept-ranges'))
            self.objects[url]=r;return r
        except Exception as e:r['error_type']=type(e).__name__;raise
        finally:self.log(r)
    def get(self,url,start,end,role):
        n=end-start+1
        if n<=0 or self.total+n>self.budget:raise RuntimeError('Range budget exceeded')
        r={'at':now().isoformat(),'method':'GET','url':url,'start':start,'end':end,'role':role}
        try:
            with self.client.stream('GET',url,headers={'Range':f'bytes={start}-{end}'}) as response:
                r['http_status']=response.status_code
                if response.status_code!=206:raise RuntimeError('Range response required; refuse full download')
                cr=response.headers.get('content-range','');r['content_range']=cr
                match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',cr)
                if not match or tuple(map(int,match.groups()))!=(start,end,self.objects[url]['size']):raise RuntimeError('Unexpected byte range')
                etag=response.headers.get('etag')
                if self.objects[url].get('etag') and etag!=self.objects[url]['etag']:raise RuntimeError('Object changed')
                chunks=[];count=0
                for chunk in response.iter_bytes():
                    count+=len(chunk)
                    if count>n:raise RuntimeError('Response exceeds requested size')
                    chunks.append(chunk)
                body=b''.join(chunks)
                if len(body)!=n:raise RuntimeError('Truncated range')
            self.total+=n;h=hashlib.sha256(body).hexdigest();p=self.out/h
            if not p.exists():p.write_bytes(body)
            r.update(bytes=n,sha256=h,finished_at=now().isoformat());return body
        except Exception as e:r['error_type']=type(e).__name__;raise
        finally:self.log(r)
    def metadata(self,url):
        info=self.head(url);size=info['size'];tail=self.get(url,size-8,size-1,'footer_length')
        if tail[-4:]!=b'PAR1':raise RuntimeError('Not Parquet')
        n=int.from_bytes(tail[:4],'little')
        if n<=0 or n>8*1024*1024:raise RuntimeError('Footer size exceeds bound')
        footer=self.get(url,size-8-n,size-9,'footer_only')
        meta=pq.read_metadata(io.BytesIO(b'PAR1'+footer+tail))
        return meta,info

class ColumnRanges(io.RawIOBase):
    def __init__(self,store,url,meta,groups,columns,role):
        super().__init__();self.store=store;self.url=url;self.meta=meta;self.pos=0;self.role=role;self.ranges=[];self.cache={}
        for i in groups:
            rg=meta.row_group(i)
            for j in range(rg.num_columns):
                c=rg.column(j)
                if c.path_in_schema not in columns:continue
                start=min(v for v in [c.dictionary_page_offset,c.data_page_offset] if v is not None and v>=0)
                self.ranges.append((start,start+c.total_compressed_size))
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.store.objects[self.url]['size']+offset
        return self.pos
    def read(self,n=-1):
        if n<0:raise RuntimeError('Unbounded read prohibited')
        if n==0:return b''
        start=self.pos;end=start+n
        if not any(a<=start and end<=b for a,b in self.ranges):raise RuntimeError('Read outside approved column chunks')
        key=(start,end)
        if key not in self.cache:self.cache[key]=self.store.get(self.url,start,end-1,self.role)
        self.pos=end;return self.cache[key]
    def readinto(self,b):
        data=self.read(len(b));b[:len(data)]=data;return len(data)

def read_columns(store,url,meta,group,columns,role):
    reader=ColumnRanges(store,url,meta,[group],columns,role)
    file=pq.ParquetFile(reader,metadata=meta,pre_buffer=False,buffer_size=0)
    return file.read_row_group(group,columns=columns,use_threads=False)
