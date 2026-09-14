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

## 当前无可信证书时

不要创建自签名证书冒充公开可信签名，也不要要求测试用户安装自签名根证书。直接省略 `-CertificateThumbprint` 和 `-RequireSignature` 构建未签名内测版：

```powershell
& '.\tools\Build Windows Release.ps1' -Version '<version>'
```

该模式不会影响发行包运行。脚本会自动：

- 将发行状态标记为 `Unsigned internal beta`；
- 在发行包中生成 `RELEASE-INTEGRITY.txt`；
- 在 `dist` 生成 ZIP 与启动器的 `SHA256SUMS.txt`；
- 生成一份可放入 GitHub Release 的校验声明；
- 保留警告，避免维护者误以为文件已经签名。

每个已发布版本必须保持不可变。内容发生变化时必须使用新版本号重新构建，不得替换同一版本号下已经公开的 ZIP。
