# Windows 启动器数字签名

`Research Starter.exe` 支持在发行包构建阶段使用可信 Authenticode 证书签名。项目不会生成或附带自签名证书，因为自签名不能为其他用户建立可信发布者身份。

## 发布要求

1. 获取由受信任证书机构签发、属于发布者的 Windows 代码签名证书，并将证书安装到执行构建的当前用户证书存储区。
2. 确认 Windows SDK 的 `signtool.exe` 可用。
3. 使用证书指纹执行发行构建：

```powershell
& '.\tools\Build Windows Release.ps1' -Version '<version>' -CertificateThumbprint '<SHA1 thumbprint>' -RequireSignature
```

构建脚本使用 SHA-256 文件摘要和 RFC 3161 时间戳，并在压缩前执行 Authenticode 验证。`-RequireSignature` 会让缺少证书的发行构建直接失败，防止误发未签名启动器。

证书私钥、导出的 PFX 文件及其密码不得存入项目目录、Git 或 GitHub Release。
