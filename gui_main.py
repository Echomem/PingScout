import queue
import tkinter as tk
from tkinter import ttk, scrolledtext
from ping_monitor import PingMonitor, PingResult

class StatusDot:
    """ 状态圆点控件 """
    def __init__(self, parent):
        self.parent = parent
        self.status_colors = {
            'init': 'gray',
            'reachable': 'green',
            'unreachable': 'red'
        }
        self.status = 'init'
        self.color = self.status_colors[self.status]
        
        self.canvas = tk.Canvas(self.parent, width=20, height=20)
        self.canvas.pack(side="left")
        self.dot = self.canvas.create_oval(6, 6, 20, 20, fill=self.color)
    
    def change_status(self, status):
        self.status = status
        self.color = self.status_colors[self.status]
        self.canvas.itemconfig(self.dot, fill=self.color)

class NetworkMonitorGUI:
    def __init__(self):
        self.monitor = PingMonitor()
        self.setup_ui()
        self.running = False
        self.root.after(100, self.process_events)
    
    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("网络状态监控系统")

        # 状态标签容器
        self.status_frame = ttk.LabelFrame(self.root, text="监控目标状态")
        self.status_frame.pack(padx=10, pady=5, fill='x')
        # 初始化状态标签
        self.status_dots = {}
        self.status_labels = {}
        for target in self.monitor.config['targets']:
            self.status_dots[target['ip']] = StatusDot(self.status_frame)
            lbl = ttk.Label(self.status_frame, text=target['name'])
            lbl.pack(side="left", padx=5, pady=5)
            lbl_status = ttk.Label(self.status_frame, text='-ms')
            lbl_status.pack(side="left", padx=0, pady=5)
            self.status_labels[target['ip']] = lbl_status


        # 日志显示区域
        self.log_area = scrolledtext.ScrolledText(self.root, height=30, state='disabled')
        self.log_area.pack(padx=5, pady=5, fill='both', expand=True)
    
        # 控制按钮区域
        self.toggle_btn = ttk.Button(self.root, text="启动监控", command=self.toggle_monitoring)
        self.toggle_btn.pack(padx=10, pady=10)

    def process_events(self):
        try:
            event = self.monitor.ping_events.get_nowait()
            if self.running:
                self.update_ui(event)
        except queue.Empty:
            pass
        self.root.after(100, self.process_events)
    
    def update_ui(self, event):
        """ 更新UI界面 """
        log_line = ""
        if event.status == PingResult.REACHABLE:
            log_line = f"[{event.timestamp}] {event.ip}可达 - 平均延迟: {event.avg_rtt:.0f}ms 丢包率:{event.loss_rate}%\n"
            self.status_labels[event.ip].config(text=f"{event.avg_rtt:.0f}ms")
        elif event.status == PingResult.UNREACHABLE:
            log_line = f"[{event.timestamp}] {event.ip} - 不可达\n"
            self.status_labels[event.ip].config(text=f"-ms")
        else:
            pass
        self.status_dots[event.ip].change_status(event.status)
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, log_line)
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')

    def toggle_monitoring(self):
        """ 切换监控按钮事件处理 """
        self.running = not self.running
        if self.running:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        """ 启动监控 """
        self.monitor.start()
        self.toggle_btn.config(text="停止监控")
    
    def stop_monitoring(self):
        """ 停止监控 """
        self.monitor.stop()
        self.toggle_btn.config(text="启动监控")
        for ip, dot in self.status_dots.items():
            dot.change_status('init')
        for ip, lbl in self.status_labels.items():
            lbl.config(text='-ms')
        self.monitor = PingMonitor()    # 重新初始化监控器，防止老线程继续运行。

    def run(self):
        self.root.mainloop()
