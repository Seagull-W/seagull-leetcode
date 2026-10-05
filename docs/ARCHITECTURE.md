# 共用核心与 VS Code 插件

根目录 Python 源文件为唯一实现来源。`service.py` 组织参数校验、题库、判题和存储；`server.py` 是保留的 HTTP 适配器；`worker.py` 是插件用的标准输入输出适配器。构建时复制 Python 核心及题库到 `extension/python`，该目录不提交 Git。

## 消息协议 v1

UTF-8，每行一个 JSON 对象。请求：

```json
{"version":1,"id":"42","method":"draft","params":{"id":"a01","language":"rust"}}
```

成功响应含 `result`，失败响应含 `error: {code, message}`；每条响应原样回显请求 ID。不同操作可以乱序返回。日志只写 stderr；判题子进程输出由判题器捕获，不进入协议流。消息上限 20 MB，代码上限 100 KB。协议是本机父子进程之间的私有通信，不开启端口。

核心操作：`bootstrap`、`state`、`draft`、`saveDraft`、`history`、`judge`、`progress`、`solution`、`knowledge`、`export`、`import`、`importDatabase`。worker 独立处理 `cancel`，目标为原判题请求 ID。一次最多一个判题，读取和草稿保存可在判题中继续。

输入 EOF 设置未完成任务的取消标记，再等待事务与判题清理。插件正常退出先同步草稿，再关闭输入；2.5 秒后仍未退出才终止其进程树。程序或机器强制退出不依赖这个流程保证数据完整，而依赖 SQLite 事务、编辑器热退出和磁盘恢复副本。

## 编辑器与数据库

- 打开的 `TextDocument` 是编辑内容的来源；提交前立即捕获文本和题目/语言，不在等待之后重新读取文本。
- `drafts.updated_at` 同时作为不透明修订标记。`saveDraft` 的 `expected` 与当前标记必须相同；`null` 表示预计尚无草稿。检查和更新在 `BEGIN IMMEDIATE` 事务中完成。
- 网页兼容调用可以省略 `expected`；它的更新仍改变标记，因此插件下一次保存能够检测外部更新。
- 原生文件是练习入口，数据库是跨入口的恢复草稿来源。文件不要求每次提交前保存。
- 恢复未保存缓冲区时，如果无法确认它基于当前数据库修订，就保留双方并要求比较；不能在重启核心时跳过冲突检查。
- 提交记录是不可变代码快照。草稿冲突可以暂缓草稿同步，但不阻止保存提交快照。
- 笔记/问答明确保存；恢复表单不算正式记录，且不包含在数据库 JSON 导出中。它们暂未提供代码草稿同级的跨窗口修订检测。

SQLite schema 和 JSON 备份版本仍为 1，未新增表或破坏旧记录。以后变更结构必须另行提供带备份的显式迁移。

## 界面与执行边界

TypeScript Extension Host 负责命令、Tree View、编辑器绑定、文件对话框、Webview 消息校验与 Python 进程管理。Webview 仅渲染题面、表单和结果；只允许白名单操作，不传递任意执行命令或文件路径。参考/历史代码通过只读 `TextDocumentContentProvider` 提供。

资源使用 `asWebviewUri`，仅允许插件 media 目录。CSP 默认禁止所有来源，只开放受控样式和 nonce 脚本。题面和用户文本全部 HTML 转义，跟随 VS Code 主题变量。

未受信任工作区不运行题目，解释器配置只读取用户层。远程开发中的执行暂不支持。Python 核心和题目代码仍以当前用户权限运行，不构成安全沙箱。
