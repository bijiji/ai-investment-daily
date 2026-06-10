# AI 投资日报机器人

追踪指定美股/ADR，拉取股价与新闻，用 OpenAI 生成中文日报，并通过 Gmail 发送到你的邮箱。

支持**本地手动运行**和 **GitHub Actions 定时自动运行**（每天墨尔本时间早上 7:00）。

## 追踪标的

| 代码 | 公司 |
|------|------|
| NVDA | NVIDIA |
| TSLA | Tesla |
| MSFT | Microsoft |
| GOOGL | Alphabet |
| ASML | ASML Holding |
| TSM | 台积电 |

## 前置准备

1. **Python 3.10+**
2. **OpenAI API Key** — [platform.openai.com](https://platform.openai.com/)
3. **Gmail 应用专用密码**
   - 开启 Google 账号两步验证
   - 前往 [应用专用密码](https://myaccount.google.com/apppasswords) 生成 16 位密码

## 安装

```bash
cd Projects/ai-investment-daily
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 配置

复制环境变量模板并填入真实值：

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

编辑 `.env`：

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

GMAIL_USER=your.email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
RECIPIENT_EMAIL=your.email@gmail.com
```

> `GMAIL_APP_PASSWORD` 填 16 位应用密码，空格可留可去。  
> `RECIPIENT_EMAIL` 可填其他收件地址；不填则默认发到 `GMAIL_USER`。

## 本地运行

```bash
python main.py
```

成功后会看到类似输出：

```
正在获取股票数据与新闻...
正在调用 OpenAI (gpt-4o-mini) 生成日报...
正在发送邮件...
完成！日报已发送至 your.email@gmail.com
```

## GitHub Actions 定时运行

### 1. 推送代码到 GitHub

```bash
git init
git add .
git commit -m "Add AI investment daily report"
git remote add origin https://github.com/<你的用户名>/ai-investment-daily.git
git push -u origin main
```

> 确保 `.env` 已在 `.gitignore` 中，**不要**把密钥提交到仓库。

### 2. 配置 Repository Secrets

在 GitHub 仓库页面：**Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 必填 | 说明 |
|-------------|------|------|
| `OPENAI_API_KEY` | 是 | OpenAI API Key |
| `GMAIL_USER` | 是 | 发件 Gmail 地址 |
| `GMAIL_APP_PASSWORD` | 是 | Gmail 应用专用密码 |
| `RECIPIENT_EMAIL` | 否 | 收件地址，不填则发到 `GMAIL_USER` |
| `OPENAI_MODEL` | 否 | 默认 `gpt-4o-mini` |

### 3. 启用定时任务

工作流文件位于 `.github/workflows/daily-report.yml`，推送后会自动生效：

- **定时执行**：每天墨尔本时间 **07:00**（`Australia/Melbourne`，自动处理夏令时）
- **手动触发**：GitHub 仓库 → **Actions** → **AI Investment Daily Report** → **Run workflow**

### 4. 查看运行日志

**Actions** 标签页可查看每次运行的日志。若失败，优先检查 Secrets 是否正确、OpenAI 账户是否有余额。

> GitHub 定时任务可能有最多约 15 分钟的延迟，属于正常现象。

## 数据来源

- **股价与新闻**：通过 [yfinance](https://github.com/ranaroussi/yfinance) 从 Yahoo Finance 获取，无需额外 API Key
- **日报生成**：OpenAI Chat Completions API
- **邮件发送**：Gmail SMTP（`smtp.gmail.com:465`）

## 项目结构

```
ai-investment-daily/
├── .github/
│   └── workflows/
│       └── daily-report.yml  # GitHub Actions 定时任务
├── main.py                   # 主程序
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── .env                      # 本地密钥（勿提交到 Git）
└── README.md
```

## 常见问题

**Gmail 登录失败**  
确认使用的是「应用专用密码」，不是 Google 账号登录密码。

**股价显示为空**  
Yahoo Finance 偶尔限流或维护，稍后重试即可。

**OpenAI 报错**  
检查 API Key 是否有效、账户是否有余额。

## 免责声明

本工具生成的内容仅供参考，不构成投资建议。投资有风险，决策请自行判断。
