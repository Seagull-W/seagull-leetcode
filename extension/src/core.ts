import {ChildProcessWithoutNullStreams, spawn} from 'node:child_process';
import {mkdir} from 'node:fs/promises';
import * as path from 'node:path';
import {createInterface} from 'node:readline';

export class RpcError extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}
export interface CoreOptions { python: string; script: string; dataDir: string; rustc?: string; log?: (s: string) => void }
interface Pending { resolve: (v: any) => void; reject: (e: Error) => void; timer: NodeJS.Timeout }

/** Private subprocess transport, shared by every view in one extension host. */
export class CoreBridge {
  private proc?: ChildProcessWithoutNullStreams;
  private pending = new Map<string, Pending>();
  private counter = 0;
  private launching?: Promise<void>;
  private disposed = false;
  constructor(readonly options: CoreOptions) {}

  private async start(): Promise<void> {
    if (this.disposed) throw new Error('核心已关闭');
    if (this.proc) return;
    if (this.launching) return this.launching;
    this.launching = (async () => {
      const tmp = path.join(this.options.dataDir, 'tmp');
      await mkdir(tmp, {recursive: true});
      const pycache = path.join(this.options.dataDir, 'cache', 'pycache');
      await mkdir(pycache, {recursive: true});
      if (this.disposed) throw new Error('核心已关闭');
      const args = ['-u', '-X', 'utf8', this.options.script, '--data-dir', this.options.dataDir];
      if (this.options.rustc) args.push('--rustc', this.options.rustc);
      const proc = spawn(this.options.python, args, {
        windowsHide: true, shell: false, cwd: path.dirname(this.options.script),
        env: {...process.env, PYTHONPYCACHEPREFIX: pycache, TEMP: tmp, TMP: tmp, TMPDIR: tmp}
      });
      this.proc = proc;
      proc.stdin.on('error', () => {});
      const reader = createInterface({input: proc.stdout});
      reader.on('line', line => {
        try {
          const message = JSON.parse(line);
          if (message.version !== 1 || typeof message.id !== 'string') throw new Error('协议响应格式错误');
          const waiter = this.pending.get(message.id);
          if (!waiter) return;
          clearTimeout(waiter.timer); this.pending.delete(message.id);
          if (message.error) waiter.reject(new RpcError(message.error.code, message.error.message));
          else waiter.resolve(message.result);
        } catch (error) {
          this.options.log?.(`核心协议错误：${String(error)}`);
          this.fail(new Error('核心协议响应错误；请重启核心'));
          proc.stdin.end();
        }
      });
      proc.stderr.on('data', data => this.options.log?.(String(data).trim()));
      proc.on('error', error => {
        if (this.proc === proc) this.proc = undefined;
        this.fail(new Error(`无法启动 Python：${error.message}。请配置 seagull.pythonPath。`));
      });
      proc.on('exit', (code, signal) => {
        reader.close();
        if (this.proc === proc) this.proc = undefined;
        this.fail(new Error(`Python 核心已退出（${code ?? signal}）；草稿保留在编辑器中，可重试或重启核心。`));
      });
    })();
    try { await this.launching; } finally { this.launching = undefined; }
  }

  async request(method: string, params: any = {}, timeoutMs = 45000, onId?: (id: string) => void): Promise<any> {
    await this.start();
    const proc = this.proc;
    if (!proc) throw new Error('Python 核心不可用');
    const id = String(++this.counter);
    const message = JSON.stringify({version: 1, id, method, params}) + '\n';
    if (Buffer.byteLength(message) > 20_000_000) throw new Error('消息超过 20 MB');
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        // An uncertain save response must never be blindly retried with a stale revision.
        reject(new Error('核心响应超时；代码仍在编辑器中，请刷新记录后重试。'));
        if (method === 'judge') void this.request('cancel', {request_id: id}).catch(() => {});
      }, timeoutMs);
      this.pending.set(id, {resolve, reject, timer});
      proc.stdin.write(message, error => {
        if (error) { clearTimeout(timer); this.pending.delete(id); reject(error); }
      });
      onId?.(id);
    });
  }

  private fail(error: Error): void {
    for (const waiter of this.pending.values()) { clearTimeout(waiter.timer); waiter.reject(error); }
    this.pending.clear();
  }

  dispose(): void {
    this.disposed = true;
    this.fail(new Error('Seagull 核心已关闭'));
    const proc = this.proc;
    this.proc = undefined;
    if (!proc) return;
    proc.stdin.end(); // EOF cancels active work and allows SQLite to finish transactions.
    const timer = setTimeout(() => {
      if (proc.exitCode !== null || proc.signalCode !== null) return;
      if (process.platform === 'win32' && proc.pid) {
        const killer = spawn('taskkill', ['/PID', String(proc.pid), '/T', '/F'], {windowsHide: true, stdio: 'ignore'});
        killer.on('error', () => proc.kill());
      } else proc.kill();
    }, 2500);
    timer.unref();
    proc.once('exit', () => clearTimeout(timer));
  }
}
