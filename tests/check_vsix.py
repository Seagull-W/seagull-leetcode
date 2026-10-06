"""Smoke-test the packaged core and reject accidental private/build payloads."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from content.catalog import BY_ID

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    source_manifest = json.loads((root/'extension/package.json').read_text(encoding='utf-8-sig'))
    parser.add_argument('package', nargs='?', type=Path, default=root/'work/dist'/f'{source_manifest["name"]}-{source_manifest["version"]}.vsix')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='vsix-smoke-',dir=root/'work') as directory:
        directory = Path(directory)
        with zipfile.ZipFile(args.package) as bundle:
            names = bundle.namelist()
            assert not any('node_modules/' in name or name.endswith('.sqlite3') or '/data/' in name or '/work/' in name for name in names)
            assert 'extension/out/extension.js' in names and 'extension/python/worker.py' in names
            for name in names:
                if not (directory/name).resolve().is_relative_to(directory.resolve()): raise ValueError('Unsafe archive path')
            bundle.extractall(directory)
        manifest = json.loads((directory/'extension/package.json').read_text(encoding='utf-8-sig'))
        assert manifest['version'] == source_manifest['version']
        assert manifest['publisher'] == source_manifest['publisher']
        assert not manifest.get('dependencies'), 'Runtime package must be self-contained'
        proc = subprocess.Popen([sys.executable,'-u','-X','utf8',str(directory/'extension/python/worker.py'),
                                 '--data-dir',str(directory/'data')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        def request(rid, method, params):
            proc.stdin.write((json.dumps(dict(version=1,id=rid,method=method,params=params))+'\n').encode('utf-8'));proc.stdin.flush()
            result = json.loads(proc.stdout.readline())
            assert 'error' not in result, result
            return result['result']
        try:
            assert len(request('boot','bootstrap',{})['problems']) == 63
            for language in ('python','rust'):
                result = request(language,'judge',dict(id='a01',language=language,code=BY_ID['a01']['solutions'][language],mode='submit'))
                assert result['result']['status'] == '通过', result
        finally:
            proc.stdin.close();proc.wait(timeout=10)
            proc.stdout.close();proc.stderr.close()
        print(f'VSIX {manifest["version"]}: {len(names)} files, {args.package.stat().st_size} bytes; bundled Python/Rust judge PASS; no personal data or node_modules')

if __name__=='__main__':main()
