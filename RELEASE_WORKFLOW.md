# Research Starter 发行操作指南

本文件是开发版的发行规范。Codex 或其他维护者每次制作 Windows 发布版时必须遵守，不能把“文件成功压缩”视为发布完成。

## 发布边界

- 从本地开发版源码构建，不能从旧 Release Test 目录反向制作发行包。
- 不提交或打包 `config.local.json`、`.runtime`、Codex 登录状态、API Key、个人任务和非公开 Inbox/Output 数据。
- 只携带 allow-list 中的三个 `public-sample`。
- 无可信证书时发布状态必须明确为“未签名内部测试版”；禁止生成或分发自签名根证书。
- 发行版只能从项目官方 GitHub Releases 页面提供。

## 自动构建

无可信证书时：

```powershell
& '.\tools\Build Windows Release.ps1' -Version '<new-version>'
```

取得可信证书后：

```powershell
& '.\tools\Build Windows Release.ps1' -Version '<new-version>' -CertificateThumbprint '<SHA1 thumbprint>' -RequireSignature
```

脚本生成：

- `dist/Research-Starter-Windows-<version>.zip`；
- `dist/Research-Starter-Windows-<version>-SHA256SUMS.txt`；
- `dist/Research-Starter-Windows-<version>-RELEASE.md`；
- ZIP 内的 `RELEASE-INTEGRITY.txt`。

## 发布前强制检查

1. 工作区中没有意外的个人文件或凭据变更。
2. 运行项目测试，并实际解压新 ZIP，在独立测试目录启动一次。
3. 确认发行包不含 `.git`、`.gitignore`、`config.local.json`、`.runtime` 或个人 Codex 状态。
4. 重新计算 ZIP SHA-256，并确认与 `SHA256SUMS.txt` 第一行一致。
5. 确认 `RELEASE-INTEGRITY.txt` 中的启动器 SHA-256 与解压后的文件一致。
6. 将 ZIP、`SHA256SUMS.txt` 一起上传到同一个 GitHub Release。
7. 把自动生成的 `-RELEASE.md` 内容纳入 Release 说明，并补充该版本功能变化。
8. 发布后从 GitHub 重新下载 ZIP，再核对一次 SHA-256；同一版本号不得静默覆盖。

如果任何检查失败，停止发布并修正；不要降低校验要求来绕过失败。
