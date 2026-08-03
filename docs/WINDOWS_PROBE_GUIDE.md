# Windows 本地数据源探测指南

本指南面向不熟悉编程的用户。所有命令都在你自己的 Windows PowerShell 中运行。不要把 Token 发给 Codex、ChatGPT、GitHub Issue 或任何聊天窗口。

## 1. 打开 PowerShell

点击 Windows 开始菜单，输入 `PowerShell`，打开“Windows PowerShell”或“终端”。后续命令一次复制一行，执行完再复制下一行。

## 2. 取得最新版代码

### 第一次下载项目

选择一个存放项目的目录，然后运行：

```powershell
git clone --branch agent-data-source-probe --single-branch https://github.com/labes030115-png/CS2-.git
cd CS2-
```

### 已经下载过项目

进入项目目录后运行：

```powershell
git switch agent-data-source-probe
git pull --ff-only
```

如果 `git pull --ff-only` 提示本地文件冲突，请停止，不要使用 `git reset --hard`，先保留提示内容再寻求帮助。

## 3. 安装 Python 3.12

先检查是否已经安装：

```powershell
py -3.12 --version
```

如果能看到 `Python 3.12.x`，直接进入下一节。如果提示找不到 Python，可运行：

```powershell
winget install -e --id Python.Python.3.12
```

安装完成后关闭并重新打开 PowerShell，再次运行版本检查命令。

## 4. 创建并安装项目运行环境

确认 PowerShell 当前位于 `CS2-` 项目目录，然后依次运行：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

这些命令只创建项目自己的 Python 环境，不会要求你把 Token 写入配置文件。

## 5. 安全保存 Token

运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.csqaq_local credential set
```

看到 `CSQAQ Token（输入内容不会显示）:` 后，在这个 PowerShell 窗口中输入或粘贴 Token，然后按 Enter。输入时屏幕不会出现星号或字符，这是正常的。

成功时只会显示：

```json
{
  "status": "credential_saved"
}
```

Token 保存在当前 Windows 用户的 Credential Manager 中。不要使用 `--token` 参数，不要设置 `CSQAQ_TOKEN` 环境变量，也不要把 Token 写入 `.env`、TOML、JSON 或文本文件。

## 6. 检查凭据状态

运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.csqaq_local credential status
```

已保存时会显示 `"saved": true`，未保存时会显示 `"saved": false`。该命令绝不会显示 Token 内容。

## 7. 运行当前价格探测

运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.csqaq_local probe current
```

此命令会调用真实 CSQAQ 接口，所以只能由你在自己的 Windows 电脑上主动执行。Codex 云端不得代替你运行。

工具只允许输出这些脱敏信息：

- 数据来源 `YYYP`
- 指标 `lowest_listing`
- 币种 `CNY`
- 本机检查时间 `checked_at_utc`
- 四个少量样本的名称、状态和有效最低在售价

工具不会输出 Token、请求头、完整请求 URL、Cookie、原始响应正文或服务器异常详情。

## 8. 查看脱敏结果

结果会直接以 JSON 显示在 PowerShell 窗口中。确认最外层包含：

```json
{
  "source_code": "YYYP",
  "metric": "lowest_listing"
}
```

在正式能力审查完成前，即使看到价格，也不能据此承诺历史范围、时间粒度或缺口回补能力。

建议只在屏幕上查看结果。不要复制服务器原始响应，也不要使用抓包工具保存请求头。

## 9. 删除测试凭据

测试结束后运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.csqaq_local credential delete
```

删除成功会显示 `credential_deleted`。如果凭据原本就不存在，会安全显示 `credential_not_found`。该命令可以重复执行。

## 10. 常见错误处理

### `CSQAQAuthenticationError`

表示 Token 认证失败。先删除旧凭据，再重新执行 `credential set`，并确认使用的是 CSQAQ 官方页面生成的有效 Token。不要把 Token 粘贴到报错截图或聊天中。

### `CSQAQIPAuthorizationError`

表示当前公网 IP 可能没有完成官方白名单绑定。登录 CSQAQ 官方页面检查绑定状态，并按官方流程绑定当前公网 IP。不要修改程序绕过白名单，也不要把 Token 交给他人代绑。

### `CSQAQUnavailableError`

表示网络超时、无法连接或服务暂时不可用。先检查本机网络，稍后再试。网络错误通常不需要重新保存 Token。

### `CSQAQRateLimitError`

表示请求过快。停止重复运行，等待一段时间后只执行一次探测。不要通过并发或更换身份绕过限流。

### `LocalCredentialError`

表示 Windows Credential Manager 操作失败。确认是在 Windows 上运行，并检查项目依赖是否完整安装。工具不会退回到明文文件保存 Token。

## 11. Git 提交安全清单

可以提交到 Git 的内容：

- 项目源代码和测试代码
- 本指南和其他不含凭据的文档
- 明确标记 `synthetic: true`、`contains_real_response: false` 的人工合成夹具

绝对不能提交到 Git 的内容：

- API Token、Cookie、登录凭据或 Credential Manager 导出文件
- `.env`、包含 Token 的 TOML、JSON、TXT 或 PowerShell 脚本
- 服务器原始响应、请求头、完整请求 URL 或抓包文件
- 包含 Token 的终端日志、命令历史、截图或录屏
- 本地数据库、备份、真实探测日志和未经人工检查的输出文件

提交前运行：

```powershell
git status --short
```

如果看到不认识的日志、响应、数据库、截图或配置文件，不要执行 `git add -A`，先停止并检查。
