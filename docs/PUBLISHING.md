# 发布与后续维护

## 当前流程

- 推送 main、提交 PR 或手动运行 **Test and package**：Windows 上执行 Python 单元测试、Node 传输测试、全部 Python/Rust 参考答案、真实 VS Code 集成测试、VSIX 内置核心检查。通过后保存 `seagull-vsix` 安装包，保留 14 天。
- 推送 `v主版本.次版本.修订号` 标签：**Release extension** 检查标签等于插件版本、提交属于 main 历史、存在许可证和更新记录。重新验证该标签源码，然后上传测试过的 VSIX 到 GitHub Release。
- 仓库变量 `MARKETPLACE_ENABLED=true` 时，继续使用 Entra OIDC 发布同一份 VSIX 到 Marketplace。未开启时此步骤跳过，GitHub Release 仍可下载。
- 发布失败可在 Actions → Release extension → Run workflow，填写已有标签重试。版本已存在时跳过 Marketplace 重复发布；不会撤回或覆盖市场现有版本。

首次发布需要所有者完成发布者注册和身份授权；仓库中的 `publisher: Seagull-W` 尚不能证明已经注册该 ID。

## 你需要先完成的操作

1. 打开 [Marketplace 管理页](https://marketplace.visualstudio.com/manage)，使用 Microsoft 账号登录 → **Create publisher**。尝试 ID `Seagull-W`，显示名称可用 Seagull。ID 创建后无法修改，请确认最终 ID。
2. 告诉维护者实际 **Publisher ID**，并选择项目许可证。若 ID 不同，需要先修改 `extension/package.json`，重新生成并测试 VSIX。不要将账号密码或令牌放入聊天、源码或日志。
3. 如果只想先上架：进入该 Publisher → **New extension → Visual Studio Code**，上传本地测试过的 VSIX。网页上传无需将 PAT 交给维护者。发布处理可能需要时间；完成后确认市场页面可访问。
4. 自动发布按以下 Entra 配置完成。没有租户或注册应用权限时，先使用手动上传路线；告诉维护者限制，再决定身份配置方式。

## GitHub Actions 的 Entra OIDC 配置

本流程使用 Azure 公有云、GitHub 托管 runner 和无长期密钥的 OIDC 登录。需要可管理应用注册的 Microsoft Entra 租户；登录步骤允许无 Azure 订阅。是否能创建租户或应用取决于账号权限，流程本身不会创建付费资源。

1. [Microsoft Entra 管理中心](https://entra.microsoft.com) → **App registrations → New registration**，创建用于 Seagull Marketplace 发布的应用。记录 **Application (client) ID** 和 **Directory (tenant) ID**。不要创建 client secret。
2. 在应用的 **Certificates & secrets → Federated credentials → Add credential**，选择 GitHub Actions。组织/所有者 `Seagull-W`，仓库 `seagull-leetcode`，实体类型 **Environment**，名称 **marketplace**。Issuer 为 `https://token.actions.githubusercontent.com`，Audience 为 `api://AzureADTokenExchange`。Subject 必须精确等于 `repo:Seagull-W/seagull-leetcode:environment:marketplace`，大小写也须相同；不要在可选 owner/repository ID 字段加入数字 ID。
3. GitHub 仓库 **Settings → Environments → New environment**，创建 `marketplace`。可将允许部署的标签限制为 `v*`；若设置 required reviewers，每次发布会等待你的审核。
4. **Settings → Secrets and variables → Actions → Variables**，添加 `AZURE_CLIENT_ID`、`AZURE_TENANT_ID`。这些是身份标识，不是密码。先不要开启 `MARKETPLACE_ENABLED`。
5. GitHub **Actions → Check Marketplace identity → Run workflow**，选择 main。它验证 OIDC 登录并调用官方 Marketplace 身份接口，成功后在运行 Summary 输出身份 ID，不输出访问令牌。此 ID 不能直接假定等于应用 client ID 或 Entra object ID。失败时反馈错误信息；不需要发送任何访问令牌。
6. Marketplace 发布者管理页 → **Members**，添加上一步身份 ID，角色 **Contributor**。这是市场发布权限；Azure 订阅中的 Reader/Contributor 角色不能替代它。若页面不接受身份，请保留错误信息并反馈，勿创建或泄露新的密钥。
7. 完成授权后，在仓库 Actions Variables 添加 `MARKETPLACE_ENABLED=true`。推送一个版本标签或重试尚未上架的版本；检查 Marketplace 发布 job 成功，并验证扩展公开页面。

OIDC 的登录和市场权限需要分别验证。尚未配置账号时只能验证构建流程，不能承诺发布身份已可用。官方已公告 Azure DevOps 全局 PAT 于 **2026-12-01** 退休，因此本流程采用 Entra，而非长期保存全局 PAT。

## 后续修改和发布

1. 修改源码、题库或文档。共享 Python 核心在仓库根目录；`extension/python` 是生成目录。
2. 运行必要测试，并在 `extension` 执行 `npm run package`。首次发布前确认许可证和 publisher。
3. 在 `extension` 执行 `npm version patch --no-git-tag-version`（功能扩展可改为 minor）。它同步 `package.json` 和 lockfile。更新根目录 `CHANGELOG.md` 对应版本条目。
4. 提交并推送 main，等待 **Test and package** 全部通过。
5. 例如版本为 0.2.1，在仓库根目录执行：

```powershell
git tag v0.2.1
git push origin v0.2.1
```

6. 查看 [Actions](https://github.com/Seagull-W/seagull-leetcode/actions) 和 [Releases](https://github.com/Seagull-W/seagull-leetcode/releases)。市场失败时修复授权后重试；代码错误应升版本再发布，不移动已发布标签。

普通 push 不直接发布给所有用户。发布由版本标签触发，避免每次小修改都成为公开版本。未来如更改数据库 schema，先做可回滚迁移、迁移前备份和旧数据测试；不要在更新时删除用户数据。

## 官方依据

- [VS Code 扩展发布、Publisher、Entra 身份与 PAT 退休](https://code.visualstudio.com/api/working-with-extensions/publishing-extension)
- [Azure Login 的 GitHub OIDC 配置与无订阅登录](https://github.com/Azure/login)
- [VS Code 扩展持续集成](https://code.visualstudio.com/api/working-with-extensions/continuous-integration)
