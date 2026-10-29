# 访问状态

2026-10-28 初次构建：本地静态书已生成，HTTP 预览使用 `127.0.0.1:8765`。
该地址只适用于运行服务器的机器或已建立端口转发的客户端，不是公网地址。

Git 仓库地址：`https://github.com/guoweikang/xkernel-review-book`。
Git 推送与网站部署是两件事；当前未部署 GitHub Pages 或 Sites 版本。
本地 `.openai/hosting.json` 属于未部署的托管配置，不随仓库提交。

远程使用本地预览的方式：

```sh
ssh -N -L 8765:127.0.0.1:8765 <你的服务器 SSH 地址>
```

然后在客户端打开 `http://127.0.0.1:8765/`。如果服务器使用 Docker，SSH 入口还需
能访问当前容器中的服务；未确认网络拓扑前，不保证上述转发直接可用。

重新启动预览：在仓库根目录运行
`python3 -m http.server 8765 --bind 127.0.0.1 --directory dist`。
