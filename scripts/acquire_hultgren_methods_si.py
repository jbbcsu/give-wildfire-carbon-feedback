"""Stream the public publisher SI for local source review; never redistribute."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
URL='https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41586-025-09085-w/MediaObjects/41586_2025_9085_MOESM1_ESM.pdf'
EXPECTED=34800087

if __name__=='__main__':
    dest=ROOT/'data/raw/research_inputs/hultgren_2025_methods_si_20260908.pdf'
    receipt=ROOT/'data/provenance/hultgren_methods_si_acquisition_20260908.json'
    if dest.exists() or receipt.exists():raise ValueError('inspect existing acquisition; no automatic retry/overwrite')
    if shutil.disk_usage(ROOT).free-36*2**20<130*2**30:raise ValueError('insufficient protected disk reserve')
    dest.parent.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256();size=0
    request=urllib.request.Request(URL,headers={'Accept-Encoding':'identity','User-Agent':'precipitation-scc-research/1.0'})
    with urllib.request.urlopen(request,timeout=30) as response:
        if response.status!=200 or urlparse(response.url).hostname!='media.springernature.com':
            raise ValueError('unexpected source response')
        if int(response.headers.get('Content-Length','0'))!=EXPECTED:raise ValueError('publisher size changed; review source')
        with dest.open('xb') as stream:
            while True:
                chunk=response.read(min(256*1024,EXPECTED-size+1))
                if not chunk:break
                if size+len(chunk)>EXPECTED:raise ValueError('payload overrun; partial preserved')
                if not size and not chunk.startswith(b'%PDF-'):raise ValueError('not PDF content')
                if shutil.disk_usage(ROOT).free-len(chunk)<130*2**30:raise ValueError('protected disk floor reached')
                stream.write(chunk);digest.update(chunk);size+=len(chunk)
        if size!=EXPECTED:raise ValueError('truncated download; partial preserved')
        result=dict(source_url=URL,article_doi='10.1038/s41586-025-09085-w',
            bytes=size,sha256=digest.hexdigest(),etag=response.headers.get('ETag'),
            path=str(dest.relative_to(ROOT)),purpose='local_primary_source_methods_review_only',
            redistribution_authorized=False,license_terms_not_yet_verified=True,
            authorization='standing project data/research-input authorization recorded in task September 8, 2026 UTC',
            downloaded_at=response.headers.get('Date'),date_field_role='server_response_Date_not_local_clock',
            code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    receipt.write_text(json.dumps(result,indent=2)+'\n')
    print('publisher SI acquired',size,'bytes; no analysis or source verification claim')
