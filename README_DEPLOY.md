# 部署到 Render 指南

本项目已配置好部署到 Render 所需的所有文件。

## 部署步骤

### 1. 准备代码仓库

确保你的代码已推送到 Git 仓库（GitHub、GitLab 或 Bitbucket）。

### 2. 在 Render 上创建服务

有两种方式部署：

#### 方式一：使用 render.yaml（推荐）

1. 登录 [Render Dashboard](https://dashboard.render.com/)
2. 点击 "New" -> "Blueprint"
3. 连接你的 Git 仓库
4. Render 会自动检测 `render.yaml` 文件并创建两个服务：
   - **zhuhaibay-web**: Web 服务（Flask API）
   - **zhuhaibay-scheduler**: Worker 服务（定时任务，每天9点自动抓取数据）

#### 方式二：手动创建服务

##### 创建 Web 服务

1. 点击 "New" -> "Web Service"
2. 连接你的 Git 仓库
3. 配置如下：
   - **Name**: zhuhaibay-web
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 backend.api:app`
   - **Python Version**: 3.13.0

##### 创建 Worker 服务（定时任务）

1. 点击 "New" -> "Background Worker"
2. 连接相同的 Git 仓库
3. 配置如下：
   - **Name**: zhuhaibay-scheduler
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m backend.scheduler`
   - **Python Version**: 3.13.0

##### 创建持久化磁盘（两个服务共享）

1. 在 Web 服务或 Worker 服务中，进入 "Disks" 标签
2. 点击 "Create Disk"
3. 配置：
   - **Name**: zhuhaibay-disk
   - **Mount Path**: `/opt/render/project/src/data`
   - **Size**: 1 GB（可根据需要调整）
4. 在另一个服务中也附加这个磁盘

### 3. 环境变量（可选）

如果需要自定义配置，可以在 Render Dashboard 中设置环境变量。

### 4. 部署完成

部署成功后：
- Web 服务会提供一个 URL，用于访问 API
- Worker 服务会在后台运行，每天9点自动抓取数据
- 数据库文件存储在持久化磁盘上，即使服务重启也不会丢失

## API 端点

部署后可以通过以下端点访问：

- `GET /api/records` - 获取所有历史记录
- `GET /api/latest` - 获取最新记录
- `GET /api/properties` - 获取所有楼盘列表
- `GET /api/property/<property_name>` - 获取指定楼盘的历史数据
- `GET /api/properties/latest` - 获取最新的所有楼盘数据
- `POST /api/refresh` - 手动刷新数据

## 注意事项

1. **时区问题**: scheduler 使用服务器时区的 09:00，如果需要特定时区，可以修改 `backend/scheduler.py` 中的时区设置。

2. **数据库路径**: 数据库文件存储在持久化磁盘的 `data/properties.db`，确保两个服务都挂载了同一个磁盘。

3. **免费计划限制**: Render 免费计划的服务在15分钟无活动后会休眠，唤醒需要几秒钟时间。

4. **日志查看**: 可以在 Render Dashboard 中查看实时日志，监控应用运行状态。

## 故障排除

如果遇到问题：

1. 查看服务日志：在 Render Dashboard 中点击服务 -> "Logs"
2. 检查数据库路径是否正确
3. 确认所有依赖都已安装在 `requirements.txt` 中
4. 验证 gunicorn 命令是否正确

