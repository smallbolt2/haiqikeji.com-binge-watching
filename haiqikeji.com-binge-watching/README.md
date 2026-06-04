# MOOC自动刷课系统 (Python版本)

这是一个使用Python重写的MOOC自动刷课系统，支持多用户并发刷课。

## 功能特点

- 支持多用户并发刷课
- Web界面管理
- 自动登录和课程处理
- 可配置的用户限制
- 详细的日志记录

## 安装要求

- Python 3.7+
- Chrome浏览器
- ChromeDriver (会自动安装)

## 安装步骤

1. 克隆项目到本地
2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置config.json：
```json
{
  "global": {
    "server": ":10086",
    "limit": 3
  },
  "users": [
    {
      "base_url": "https://your-mooc-platform.com/login",
      "school_id": 0,
      "username": "your_username",
      "password": "your_password"
    }
  ]
}
```

## 运行方法

```bash
python app.py
```

访问 http://localhost:10086 查看Web界面

## 注意事项

- 请确保网络连接稳定
- 建议使用代理IP避免被封禁
- 请遵守相关平台的使用条款
- 本工具仅供学习交流使用 