# Seagull VS Code 本地练习台

在 VS Code 原生编辑器中练习 Python / Rust，阅读中文题面、背景知识与参考答案，保存历史与复习笔记。包含 63 道双语言算法题、14 篇知识说明和 10 道后训练问答。

## 安装与使用

1. 安装 Python 3.10+；做 Rust 题还需 rustc。插件不自动安装语言工具链。
2. VS Code 扩展面板菜单 → **从 VSIX 安装** → 选择 `seagull-practice-<版本>.vsix`。已发布版本可从仓库的 [Releases](https://github.com/Seagull-W/seagull-leetcode/releases) 下载；Marketplace 上架后也可直接搜索安装。
3. 点击活动栏 Seagull 图标，在专题树选择题目。编辑器打开 `.py` / `.rs`，旁边显示题面。
4. 实现 `solve`。`Ctrl+Enter` 提交，`Alt+Enter` 运行示例；macOS 提交为 `Cmd+Enter`。也可使用编辑器工具栏或题面按钮。
5. “笔记与复习”和后训练问答使用明确的**保存**按钮；未保存表单以 Webview 状态辅助恢复。代码草稿约 600ms 自动同步。

未保存到文件的编辑器内容也可提交；提交记录保存点击提交时的代码快照。Python 与 Rust 草稿和通过状态分别保存，笔记按题目共享。

参考答案和历史代码通过只读文档打开，可与当前草稿比较。替换历史代码前需要选择“替换当前草稿”；编辑器支持撤销。首次打开题目时仍会有模板中的 `NotImplementedError` / `todo!()`，这是等待实现的标记。

原生编辑器提供查找、撤销、多光标和语法高亮。Python/Rust 的高级补全需相应语言扩展；Rust 独立文件不是 Cargo 项目，本版不承诺完整 rust-analyzer 语义诊断。

## 数据目录与 D 盘

Windows 检测到 D 盘时，默认根目录为 **`D:\SeagullPractice`**。没有 D 盘时才使用 VS Code 的 `globalStorageUri`。可设置 `seagull.dataDirectory` 为其他绝对路径。

```json
{
  "seagull.pythonPath": "D:\\python\\python312\\python.exe",
  "seagull.dataDirectory": "D:\\objects\\seagull-leetcode\\data",
  "seagull.rustcPath": ""
}
```

若沿用本项目现有数据库，可把数据目录设置为上面的 `data` 路径；否则使用导入命令迁移。修改配置后运行 **Seagull: 重启 Python 核心**，目录切换不会自动搬走旧数据。

根目录结构：

| 路径 | 用途 |
|---|---|
| `practice.sqlite3` | 草稿、提交、进度、笔记与知识回答 |
| `solutions/<题目 ID>/solution.py` 或 `.rs` | 可在原生编辑器打开的练习文件 |
| `recovery/<窗口 ID>/` | 尚未同步或有冲突的代码恢复副本 |
| `runs/` | 判题临时目录，完成、超时或取消后清理 |
| `tmp/`、`cache/pycache/` | Python 进程临时文件与字节码缓存 |
| `backups/`、`before-import-*.json` | 手动导出与导入前备份 |
| `pending-forms.json` | 尚未点击保存的笔记与问答恢复副本 |

VS Code 自身安装、已有 Python/Rust 及语言扩展的位置不会被插件迁移。插件自身很小；本项目的 npm 缓存、依赖、构建产物及隔离测试目录也放在 D 盘。`rustc` 来自 PATH 或配置路径，不下载新的 Rust 工具链。

**不要删除数据库和 recovery 目录来清理空间。** 判题目录自动清理；备份按需手动归档。本地数据没有加密，也不上传网络。

## 旧数据迁移和冲突

命令面板 → **Seagull: 导入备份 / 迁移旧记录**：可选择网页导出的 JSON，或旧版 `practice.sqlite3`。SQLite 迁移以只读事务读取包含 WAL 的快照，不移动原文件；导入前自动备份目标数据库。重复提交按 ID 去重，草稿与笔记保留较新版本。

已经打开的编辑器不会被导入覆盖。需要采用迁移后的草稿时重新打开题目，或运行 **Seagull: 比较并解决草稿冲突**。两个窗口同时改同一草稿会通过数据库时间修订标记检测冲突；当前编辑器与 recovery 副本保留，比较后选择要保存的版本。冲突不阻止保存不可变的提交快照。

导出备份前同步当前草稿；冲突未解决时需要先解决。恢复副本不属于数据库 JSON 备份，请另行保留，或先恢复到草稿。VS Code 热退出缓冲区也会优先保留。

代码草稿提供修订冲突检测；笔记与问答按最后保存的内容更新，请避免在多个窗口同时修改同一条笔记。未保存表单缓存是辅助恢复，不替代点击保存或数据库备份。

## 首版边界

- 仅本地桌面 VS Code；远程 SSH、WSL、容器和浏览器版执行暂不支持。Windows 为实际验证平台。
- 受限工作区可以浏览题库；运行代码需要 Workspace Trust。运行配置在未信任时只读取用户设置。
- Python 子进程、Rust 编译器以当前用户权限运行。这是个人练习执行器，**不是安全沙箱**。
- Rust 编译 30 秒，整组测试执行 4 秒，输出限制 256 KB。通知中的取消按钮会终止判题进程树。
- 暂无硬内存限制、云同步、多人竞赛、PyTorch 编程题或复杂度自动评分。
- 不依赖 HTTP 端口或在线 API。SQLite schema v1 和旧版 JSON 格式保持兼容。

## 开发

在仓库的 `extension` 目录运行：

```powershell
npm.cmd ci
npm.cmd run build
npm.cmd test
npm.cmd run test:integration
npm.cmd run package
```

依赖在 `extension/node_modules`，npm 缓存在 `work/npm-cache`。构建复制共享 Python 源到 `extension/python`；它是生成目录，不直接编辑。VSIX 输出在 `work/dist`。

使用 F5 调试时以 `extension` 为 VS Code 工作区。集成测试优先使用 `SEAGULL_VSCODE_EXECUTABLE` 指定现有 VS Code，避免下载另一套编辑器。测试数据和用户配置在仓库 `work` 下隔离，不修改日常 VS Code 设置。

仓库根目录 `python -X utf8 server.py --open` 仍可启动网页版本。网页与插件共用 `service.py`、`judge.py`、`store.py` 和题库。

## 更新与隐私

Marketplace 安装后，VS Code 按扩展自动更新设置获取新版本。手动 VSIX 安装可安装新版覆盖旧版。练习数据库在独立数据目录，不随扩展覆盖安装删除；升级前仍建议导出备份。

插件不包含遥测、云账号或网络上传功能。执行 Python / Rust 练习使用本机工具链。题库、运行结果及个人练习记录留在本地。

自动测试和发布配置见仓库的 [发布指南](https://github.com/Seagull-W/seagull-leetcode/blob/main/docs/PUBLISHING.md)。
