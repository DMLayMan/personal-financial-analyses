"""Mirror source-only inputs for a self-contained, reproducible Site checkout."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'sites/personal-financial-analyses'
paths=[]
for directory in ('pfa','knowledge','static','docs','tests','scripts'):
    paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in ('.py','.json','.js','.html','.css','.md') and '__pycache__' not in p.parts)
paths += [ROOT/'fixtures/companies.json',ROOT/'quality/features.json',ROOT/'quality/latest-functional.json',ROOT/'requirements.txt']
# Include the authored deployment files named in the functional manifest too.
report=ROOT/'quality/latest-functional.json'
if report.is_file():
    paths += [ROOT/name for name in json.loads(report.read_text()).get('source_manifest',{}) if not name.startswith('data/')]
paths=list(dict.fromkeys(paths))
# No raw data, database, credentials, logs, holdings or downloaded originals.
target=SITE/'kernel';target.mkdir(exist_ok=True)
manifest={}
for path in paths:
    if not path.exists():continue
    dest=target/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
    manifest[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
(SITE/'kernel-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(source_files=len(manifest),data_files=0)))
