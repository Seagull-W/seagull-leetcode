"""Compile/run all bilingual reference answers through the actual judge."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from content.catalog import PROBLEMS
from judge import judge

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--language',choices=['python','rust','all'],default='all');parser.add_argument('--report',type=Path)
    args=parser.parse_args();rows=[];failures=[]
    for language in (['python','rust'] if args.language=='all' else [args.language]):
        for p in PROBLEMS:
            result=judge(p,language,p['solutions'][language]);rows.append(dict(id=p['id'],language=language,**result))
            print(f'{language:6} {p["id"]}: {result["status"]} {result["passed"]}/{result["total"]}',flush=True)
            if result['status']!='通过':failures.append((p['id'],language,result))
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(rows)-len(failures)}/{len(rows)} reference answers passed.')
    for pid,lang,result in failures:print(pid,lang,json.dumps(result,ensure_ascii=False))
    return bool(failures)

if __name__=='__main__':raise SystemExit(main())
