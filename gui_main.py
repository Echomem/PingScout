import queue
import tkinter as tk
from tkinter import ttk, scrolledtext
from icmp_monitor import ICMPMonitor

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
        self.monitor = ICMPMonitor()
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
        for target in self.monitor.config['targets']:
            self.status_dots[target['ip']] = StatusDot(self.status_frame)
            lbl = ttk.Label(self.status_frame, text=target['name'])
            lbl.pack(side="left", padx=5, pady=5)

        # 日志显示区域
        self.log_area = scrolledtext.ScrolledText(self.root, height=30, state='normal')
        self.log_area.pack(padx=5, pady=5, fill='both', expand=True)
    
        # 控制按钮区域
        self.toggle_btn = ttk.Button(self.root, text="启动监控", command=self.toggle_monitoring)
        self.toggle_btn.pack(padx=10, pady=10)

    def process_events(self):
        try:
            event = self.monitor.event_queue.get_nowait()
            if event.status == 'reachable':
                self.status_dots[event.ip].change_status('reachable')
                log_line = f"[{event.timestamp}] {event.ip}可达 - 延迟: {event.rtt:.0f}ms\n"
                self.log_area.insert(tk.END, log_line)
                self.log_area.see(tk.END)
            elif event.status == 'unreachable':
                self.status_dots[event.ip].change_status('unreachable')
                log_line = f"[{event.timestamp}] {event.ip} - 不可达\n"
                self.log_area.insert(tk.END, log_line)
                self.log_area.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.process_events)
    

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

    def run(self):
        self.root.mainloop()
