# PingScout
通过不间断发送ICMP包（类似ping）确定目标地址在线状态或者网络线路是否中断的Python项目

## 功能特点：
- 检测目标主机的在线状态。
- 记录检测日志。
- 支持多线程并发检测。
- 提供图形界面展示在线情况。

## 安装指南：
1. 确保您的系统上已经安装了Python 3.x。
2. 克隆或下载PingScout的源代码。
3. 打开命令行终端，进入PingScout的目录。
4. 运行以下命令来安装所需的依赖库：
   ```
   pip install -r requirements.txt
   ```
5. 配置PingScout：
   - 打开config/config.yaml文件。
   - 根据需要修改配置项，例如目标IP地址、名称、超时时间、检测间隔时间等。
6. 运行PingScout：
   默认使用图形界面启动：
   ```
   python run.py
   ```
   或者使用命令行启动：
   ```
   python run.py -c 
   ```

## 项目结构：
- config/config.yaml：配置文件，用于设置目标IP地址、名称、超时时间、检测间隔时间等。
- log/log.txt：日志文件，用于记录检测结果。
- resources/：资源文件目录，包括告警声音等。

## 使用说明：
- config/config.yaml中配置需要监测的目标地址。
- 运行run.py即可开始监测。
- 监测结果将显示在图形界面上，并记录在log目录下的log.txt文件中。

## 注意事项
 - 权限问题：在 Linux 系统中，运行此代码通常需要 root 权限，因为创建原始套接字需要较高的权限。
 - 防火墙和网络策略：防火墙或网络策略可能会阻止 ICMP 数据包的传输，导致即使目标 IP 地址实际上可达，也会被判断为不可达。

## 贡献指南：
欢迎您对PingScout进行贡献！如果您发现了任何问题或有改进建议，请通过GitHub的问题跟踪功能提交。

## 联系信息：
如果您有任何问题或建议，请通过以下方式联系我：
- 邮箱EMAIL- 邮箱：echo.io@hotmail.com