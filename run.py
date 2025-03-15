import argparse
import logging
from gui_main import NetworkMonitorGUI
from ping_monitor import PingMonitor
from alert import Alert

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def console_main():
    """ 控制台方式启动程序 """
    try:
        monitor = PingMonitor()
        monitor.start()
        alert = Alert(monitor.logger)
        while True:
            try:
                event = monitor.ping_events.get()
                logging.info(event)
                alert.process_alert(event)
            except KeyboardInterrupt:
                monitor.stop()
                logging.info("程序已停止")
                break
    except Exception as e:
        logging.error(f"控制台启动程序时出现错误: {e}")

def gui_main():
    """ GUI方式启动程序 """
    try:
        app = NetworkMonitorGUI()
        app.run()
    except Exception as e:
        logging.error(f"GUI启动程序时出现错误: {e}")

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='PingScout程序启动器')
    parser.add_argument('-c', '--console', action='store_true', help='使用控制台方式启动')
    parser.add_argument('-g', '--gui', action='store_true', help='使用图形界面方式启动')

    # 解析命令行参数
    args = parser.parse_args()

    if args.console:
        console_main()
    elif args.gui:
        gui_main()
    else:
        # 默认图形方式启动
        gui_main()

if __name__ == "__main__":
    main()
