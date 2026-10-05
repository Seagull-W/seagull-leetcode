"""Run trusted personal practice code locally. This is NOT a security sandbox."""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

LIMIT = 256_000

def rust_value(value, kind):
    if kind == 'i64':
        return str(value) + 'i64'
    if kind == 'String':
        # Rust accepts JSON escapes except JSON's Unicode escape form;
        # ensure_ascii=False keeps actual Unicode codepoints.
        return json.dumps(value, ensure_ascii=False) + '.to_string()'
    if kind.startswith('Vec<'):
        inner = kind[4:-1]
        return 'vec![' + ','.join(rust_value(v, inner) for v in value) + ']'
    raise ValueError('Unsupported input type')

RUST_JSON = r'''
trait SeagullJson { fn seagull_json(&self) -> String; }
impl SeagullJson for i64 {fn seagull_json(&self)->String{self.to_string()}}
impl SeagullJson for bool {fn seagull_json(&self)->String{self.to_string()}}
impl SeagullJson for String {
    fn seagull_json(&self)->String{
        let mut s=String::from("\"");
        for c in self.chars(){match c {
            '"'=>s.push_str("\\\""), '\\'=>s.push_str("\\\\"),
            '\n'=>s.push_str("\\n"), '\r'=>s.push_str("\\r"), '\t'=>s.push_str("\\t"),
            c if (c as u32)<32 => s.push_str(&format!("\\u{:04x}",c as u32)),
            c=>s.push(c),
        }}s.push('"');s
    }
}
impl<T:SeagullJson> SeagullJson for Vec<T>{
    fn seagull_json(&self)->String{format!("[{}]",self.iter().map(|x|x.seagull_json()).collect::<Vec<_>>().join(","))}
}
'''

def execute(command, cwd, timeout):
    """File-backed capture bounds RAM; kill process tree on Windows timeout."""
    started = time.perf_counter()
    outpath, errpath = Path(cwd)/'stdout.txt', Path(cwd)/'stderr.txt'
    with outpath.open('wb') as out, errpath.open('wb') as err:
        proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=out, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
            start_new_session=os.name!='nt')
        expired = False
        oversized = False
        deadline = started + timeout
        while proc.poll() is None:
            if time.perf_counter() > deadline or outpath.stat().st_size + errpath.stat().st_size > LIMIT:
                expired = time.perf_counter() > deadline
                oversized = not expired
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],
                        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    import signal
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.kill(); proc.wait()
                break
            time.sleep(0.02)
    elapsed = (time.perf_counter()-started)*1000
    stdout = outpath.read_bytes()[:LIMIT].decode('utf-8',errors='replace')
    stderr = errpath.read_bytes()[:LIMIT].decode('utf-8',errors='replace')
    oversized = oversized or outpath.stat().st_size + errpath.stat().st_size > LIMIT
    return dict(code=proc.returncode, stdout=stdout, stderr=stderr,
                timeout=expired, oversized=oversized, elapsed=round(elapsed,2))

def equal(actual, expected, unordered=False):
    # JSON bool is not interchangeable with int, even though Python says True == 1.
    def typed(x):
        if isinstance(x,list): return ('list',tuple(typed(v) for v in x))
        return (type(x).__name__,x)
    if unordered:
        if not isinstance(actual,list): return False
        a=sorted(json.dumps(typed(x),ensure_ascii=False) for x in actual)
        e=sorted(json.dumps(typed(x),ensure_ascii=False) for x in expected)
        return a==e
    return typed(actual)==typed(expected)

def judge(problem, language, code, mode='submit', temp_root=None):
    cases = problem['cases'][:2] if mode=='run' else problem['cases']
    marker = 'SEAGULL_'+secrets.token_hex(12)+':'
    base = dict(status='运行错误', passed=0,total=len(cases),execution_ms=0,compile_ms=0,
                cases=[],message='',stderr='')
    if language not in ('python','rust'): raise ValueError('不支持的语言')
    if len(code.encode('utf-8')) > 100_000: raise ValueError('代码不能超过 100 KB')
    if temp_root: Path(temp_root).mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='submission-',dir=temp_root) as folder:
        folder=Path(folder)
        if language=='python':
            (folder/'solution.py').write_text(code,encoding='utf-8')
            runner = 'import json,sys,importlib.util\nspec=importlib.util.spec_from_file_location("solution", "solution.py")\nm=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(m)\n'
            runner += f'cases=json.loads({json.dumps(json.dumps([c["input"] for c in cases],ensure_ascii=False))})\n'
            runner += f'for args in cases:\n    result=m.solve(*args)\n    print({marker!r}+json.dumps(result,ensure_ascii=False),flush=True)\n'
            (folder/'runner.py').write_text(runner,encoding='utf-8')
            command=[sys.executable,'-I','-X','utf8',str(folder/'runner.py')]
        else:
            compiler=shutil.which('rustc')
            if not compiler:
                return {**base,'status':'环境缺失','message':'未找到 rustc。安装 Rust 后重新启动平台。'}
            (folder/'solution.rs').write_text(code,encoding='utf-8')
            calls=[]
            for c in cases:
                args=','.join(rust_value(v,typ) for v,(_,typ) in zip(c['input'],problem['args']))
                calls.append(f'{{ let answer: {problem["result_type"]} = solution::solve({args}); println!("{marker}{{}}", answer.seagull_json()); }}')
            runner='mod solution;\n'+RUST_JSON+'\nfn main(){\n'+'\n'.join(calls)+'\n}\n'
            (folder/'runner.rs').write_text(runner,encoding='utf-8')
            binary=folder/('runner.exe' if os.name=='nt' else 'runner')
            built=execute([compiler,'--edition=2021','-C','opt-level=1','-o',str(binary),str(folder/'runner.rs')],folder,30)
            base['compile_ms']=built['elapsed']
            if built['timeout'] or built['code']!=0 or built['oversized']:
                return {**base,'status':'编译错误','message':'编译超时（30 秒）' if built['timeout'] else 'Rust 编译失败，请查看编译器信息。', 'stderr':built['stderr'][:12000]}
            command=[str(binary)]
        ran=execute(command,folder,4)
        base['execution_ms']=ran['elapsed'];base['stderr']=ran['stderr'][:12000]
        lines=[line[len(marker):] for line in ran['stdout'].splitlines() if line.startswith(marker)]
        malformed=False
        for i,line in enumerate(lines[:len(cases)]):
            try: actual=json.loads(line)
            except (ValueError,TypeError): malformed=True;break
            case=cases[i];ok=equal(actual,case['expected'],problem.get('unordered',False))
            base['cases'].append(dict(index=i+1,input=case['input'],expected=case['expected'],actual=actual,passed=ok))
            base['passed']+=int(ok)
        if ran['timeout']: base.update(status='超时',message='整组测试执行超过 4 秒，已终止进程。')
        elif ran['oversized']: base.update(status='输出过多',message='输出超过 256 KB，请减少调试打印。')
        elif ran['code']!=0: base.update(status='运行错误',message='程序异常退出。Python 需要定义 solve，Rust 需要 pub fn solve。')
        elif malformed or len(lines)!=len(cases): base.update(status='运行错误',message='未获得全部有效的返回值，请检查返回类型和输出。')
        elif base['passed']==len(cases): base.update(status='通过',message='示例通过；提交后检查全部测试。' if mode=='run' else '全部测试通过。可标记掌握程度或安排复习。')
        else: base.update(status='答案错误',message='存在不匹配的结果，下面展示测试输入和期望结果。')
        base['stdout']='\n'.join(line for line in ran['stdout'].splitlines() if not line.startswith(marker))[:4000]
        return base
