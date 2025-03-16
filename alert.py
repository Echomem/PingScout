import os
import threading
import yaml
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ping_monitor import PingResult
from concurrent.futures import ThreadPoolExecutor
import sys

original_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')
import pygame
sys.stdout = original_stdout

class Alert:
    def __init__(self, logger):
        self.config = self.load_config()
        self.logger = logger
        self.enable_sound = self.config['alert']['sound']['enable']
        self.enable_email = self.config['alert']['email']['enable']
        self.condition_max_rtt = self.config['alert']['condition']['max_rtt']
        self.condition_loss_rate = self.config['alert']['condition']['max_loss_rate']
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.sound_lock = threading.Lock()
        pygame.mixer.init()
        

    def load_config(self):
        """ 加载配置文件 """
        with open('config/config.yaml', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def play_alarm(self):
        """ 同步播放配置文件中指定的声音文件 """
        sound_file = self.config['alert']['sound']['sound_file']
        # 处理文件路径，去掉不必要的 ./
        sound_file = os.path.abspath(sound_file)
        # 检查文件是否存在
        if not os.path.exists(sound_file):
            self.logger.error(f"声音文件不存在: {sound_file}")
            return
        # 播放声音
        
        try:
            with self.sound_lock:
                sound = pygame.mixer.Sound(sound_file)
                sound.play()
        except pygame.error as e:
            self.logger.error(f"播放声音发生错误: {e}")

    def send_email(self, message):
        """ 发送邮件 """
        # 读取配置文件中的邮件相关信息  
        smtp_server = self.config['alert']['email']['smtp_server']
        smtp_port = self.config['alert']['email']['smtp_port']
        username = self.config['alert']['email']['username']
        subject = self.config['alert']['email']['subject']
        recipients = self.config['alert']['email']['recipients']
        password = os.getenv('EMAIL_PASSWORD')  # 优先在环境变量中获取密码
        if password is None:
            password = self.config['alert']['email']['password']
        server = None
        try:
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.sendmail(username, recipients, msg.as_string())
            server.quit()
            self.logger.info("报警邮件发送成功")
        except Exception as e:
            if server:
                server.quit()
            self.logger.error(f"邮件发送失败: {e}")

    def check_alert_conditions(self, ping_result):
        """ 检查是否满足报警条件 """
        if ping_result.status == PingResult.UNREACHABLE:
            return True
        if ping_result.max_rtt > self.condition_max_rtt or ping_result.loss_rate > self.condition_loss_rate:
            return True
        return False

    def process_alert(self, ping_result):
        if not self.check_alert_conditions(ping_result):
            return 
        if self.enable_sound:
            self.executor.submit(self.play_alarm)
        if self.enable_email:
            message = ""
            if ping_result.status == PingResult.UNREACHABLE:
                message = f"{ping_result.timestamp} - 报警：\nIP: {ping_result.ip}\n状态: {ping_result.status}"
            else:
                message = f"{ping_result.timestamp} - 报警：\nIP: {ping_result.ip}\n状态: {ping_result.status}\n最大时延: {ping_result.max_rtt}ms\n最小时延: {ping_result.min_rtt}ms\n平均时延: {ping_result.avg_rtt}ms\n丢包率: {ping_result.loss_rate}%"
            # 后台线程发送邮件
            self.executor.submit(self.send_email, message)