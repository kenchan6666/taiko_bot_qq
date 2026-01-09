# Webhook 端点暴露设置指南

**目的**: 配置 LangBot 与 FastAPI 后端之间的 webhook 连接

**适用场景**: 
- 本地开发环境（使用 ngrok 等隧道服务）
- 生产环境（使用公网 IP/域名 + Nginx）

---

## 概述

LangBot 需要能够访问 FastAPI 后端的 `/webhook/langbot` 端点。根据部署环境的不同，有几种方法可以暴露这个端点：

1. **本地开发**: 使用 ngrok 或其他隧道服务
2. **生产环境**: 使用公网 IP/域名 + Nginx 反向代理（推荐 HTTPS）

---

## 方法 1: 本地开发 - 使用 ngrok

### 步骤 1: 安装 ngrok

**Windows**:
```powershell
# 下载 ngrok: https://ngrok.com/download
# 解压到任意目录，或使用 Chocolatey
choco install ngrok
```

**macOS**:
```bash
brew install ngrok
```

**Linux**:
```bash
# 下载并解压
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

### 步骤 2: 启动 ngrok 隧道

```bash
# 启动 ngrok，将本地 8000 端口暴露到公网
ngrok http 8000

# 或者指定域名（需要 ngrok 付费账户）
ngrok http 8000 --domain=your-custom-domain.ngrok.io
```

### 步骤 3: 获取公网 URL

ngrok 启动后会显示类似以下的信息：

```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

**复制 HTTPS URL** (例如: `https://abc123.ngrok.io`)

### 步骤 4: 配置 LangBot

在 LangBot 配置文件中，设置 webhook URL：

```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "https://abc123.ngrok.io/webhook/langbot"
```

### 步骤 5: 测试连接

```bash
# 测试 webhook 端点（使用 ngrok URL）
curl -X POST https://abc123.ngrok.io/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, test message",
    "images": []
  }'
```

### 注意事项

- **免费版限制**: ngrok 免费版每次重启会生成新的 URL，需要更新 LangBot 配置
- **稳定性**: 免费版可能有连接限制，生产环境建议使用付费版或公网 IP
- **HTTPS**: ngrok 自动提供 HTTPS，无需额外配置

---

## 方法 2: 本地开发 - 使用其他隧道服务

### Cloudflare Tunnel (cloudflared)

```bash
# 安装 cloudflared
# Windows: choco install cloudflared
# macOS: brew install cloudflared
# Linux: 下载二进制文件

# 启动隧道
cloudflared tunnel --url http://localhost:8000
```

### localtunnel

```bash
# 使用 npm 安装
npm install -g localtunnel

# 启动隧道
lt --port 8000
```

### serveo (SSH 隧道)

```bash
# 使用 SSH 创建反向隧道
ssh -R 80:localhost:8000 serveo.net
```

---

## 方法 3: 生产环境 - 公网 IP + Nginx

### 步骤 1: 确保服务器有公网 IP

确认你的服务器可以从互联网访问：

```bash
# 检查公网 IP
curl ifconfig.me

# 测试端口是否开放（从外部网络）
telnet your-server-ip 8000
```

### 步骤 2: 配置防火墙

**Ubuntu/Debian (ufw)**:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp  # 如果直接访问，否则只需要 80/443
sudo ufw enable
```

**CentOS/RHEL (firewalld)**:
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 步骤 3: 安装和配置 Nginx

**安装 Nginx**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx

# CentOS/RHEL
sudo yum install nginx
```

**配置 Nginx 反向代理**:

创建配置文件 `/etc/nginx/sites-available/taiko-bot` (Ubuntu) 或 `/etc/nginx/conf.d/taiko-bot.conf` (CentOS):

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;  # 替换为你的域名或 IP

    # 重定向 HTTP 到 HTTPS (推荐)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;  # 替换为你的域名

    # SSL 证书配置 (使用 Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 反向代理到 FastAPI 后端
    location /webhook/langbot {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }

    # 指标端点（可选，限制访问）
    location /metrics {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        # 可以添加 IP 白名单或认证
        # allow 127.0.0.1;
        # deny all;
    }
}
```

**启用配置**:

```bash
# Ubuntu/Debian
sudo ln -s /etc/nginx/sites-available/taiko-bot /etc/nginx/sites-enabled/
sudo nginx -t  # 测试配置
sudo systemctl reload nginx

# CentOS/RHEL
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

### 步骤 4: 配置 SSL 证书 (Let's Encrypt)

**安装 Certbot**:
```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx
```

**获取证书**:
```bash
sudo certbot --nginx -d api.yourdomain.com
```

Certbot 会自动配置 Nginx 使用 HTTPS。

### 步骤 5: 配置 LangBot

在 LangBot 配置文件中，设置 webhook URL：

```yaml
triggers:
  - type: keyword
    pattern: "(?i)(mika|米卡|mika酱)"
    webhook_url: "https://api.yourdomain.com/webhook/langbot"
```

### 步骤 6: 测试连接

```bash
# 测试 webhook 端点
curl -X POST https://api.yourdomain.com/webhook/langbot \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": "123456789",
    "user_id": "987654321",
    "message": "Mika, test message",
    "images": []
  }'

# 测试健康检查
curl https://api.yourdomain.com/health
```

---

## 方法 4: 生产环境 - 直接使用公网 IP (不推荐)

**注意**: 直接使用公网 IP 不推荐，因为：
- 没有 HTTPS（不安全）
- IP 可能变化
- 难以管理多个服务

如果必须使用，确保：

1. **防火墙配置**: 开放 8000 端口
2. **LangBot 配置**: 使用 `http://your-server-ip:8000/webhook/langbot`
3. **安全考虑**: 考虑使用 VPN 或 IP 白名单限制访问

---

## 验证 Webhook 连接

### 1. 检查 FastAPI 后端日志

```bash
# 查看 FastAPI 日志
docker-compose logs -f backend

# 或直接运行
tail -f logs/app.log
```

应该看到类似以下日志：
```
INFO: webhook_received message_type=group group_id=123456789 user_id=987654321...
```

### 2. 检查 LangBot 日志

查看 LangBot 日志，确认 webhook 请求已发送：
```
INFO: Sending webhook to https://api.yourdomain.com/webhook/langbot
INFO: Webhook response: 200 OK
```

### 3. 测试端到端

在 QQ 群中发送消息：
```
Mika, 你好！
```

检查：
- LangBot 是否检测到关键词
- Webhook 是否成功发送
- FastAPI 是否收到请求
- 机器人是否回复

---

## 故障排查

### 问题 1: ngrok 连接失败

**症状**: ngrok 无法启动或连接失败

**解决方案**:
- 检查端口 8000 是否被占用: `netstat -an | grep 8000`
- 确认 FastAPI 后端正在运行: `curl http://localhost:8000/health`
- 检查防火墙是否阻止 ngrok

### 问题 2: Nginx 502 Bad Gateway

**症状**: Nginx 返回 502 错误

**解决方案**:
- 检查 FastAPI 后端是否运行: `curl http://localhost:8000/health`
- 检查 Nginx 错误日志: `sudo tail -f /var/log/nginx/error.log`
- 确认 proxy_pass URL 正确: `http://localhost:8000` (不是 `http://127.0.0.1:8000`)

### 问题 3: SSL 证书错误

**症状**: 浏览器显示 SSL 证书错误

**解决方案**:
- 检查证书是否过期: `sudo certbot certificates`
- 更新证书: `sudo certbot renew`
- 确认域名 DNS 解析正确: `nslookup api.yourdomain.com`

### 问题 4: LangBot 无法连接 webhook

**症状**: LangBot 日志显示连接失败

**解决方案**:
- 验证 webhook URL 是否正确（包含 `/webhook/langbot`）
- 从 LangBot 服务器测试连接: `curl -X POST https://api.yourdomain.com/webhook/langbot`
- 检查防火墙规则是否允许 LangBot 服务器 IP
- 确认 FastAPI 后端正在运行并监听正确端口

### 问题 5: 超时错误

**症状**: Webhook 请求超时

**解决方案**:
- 增加 Nginx 超时设置（见上面的配置）
- 检查 FastAPI 后端响应时间
- 考虑增加 Temporal workflow 超时时间

---

## 安全建议

1. **使用 HTTPS**: 生产环境必须使用 HTTPS，保护 webhook 数据
2. **IP 白名单**: 如果可能，限制只有 LangBot 服务器可以访问 webhook 端点
3. **API 密钥验证**: 考虑在 webhook 请求中添加 API 密钥验证
4. **速率限制**: 确保 FastAPI 后端已配置速率限制（已在代码中实现）
5. **日志监控**: 监控 webhook 请求日志，检测异常活动

---

## 相关文档

- [quickstart.md](./specs/1-mika-bot/quickstart.md) - 完整设置指南
- [langbot.config.example.yaml](./langbot.config.example.yaml) - LangBot 配置示例
- [README.md](./README.md) - 项目概述

---

**最后更新**: 2026-01-09  
**维护者**: Mika Taiko Chatbot Team
