import asyncio
import threading
import time
import socket
import struct
import random
import logging
import yaml
from logging.handlers import TimedRotatingFileHandler
import os
import queue
from concurrent.futures import ThreadPoolExecutor

class ICMPError(Exception):
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message
    

class ICMPSender:
    def __init__(self, ip):
        self.id = random.randint(0, 65535)
        self.seq = 1
        self.ip = ip
        self.sock = None

    def checksum(self, data):
        s = 0
        n = len(data) % 2
        for i in range(0, len(data)-n, 2):
            s += (data[i]) + ((data[i+1]) << 8)
        if n:
            s += data[-1]
        while (s >> 16):
            s = (s & 0xFFFF) + (s >> 16)
        s = ~s & 0xFFFF
        return s

    def send(self, timeout=1):
        try:
            icmp = socket.getprotobyname('icmp')
            # 创建一个原始套接字
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        except PermissionError:
            raise ICMPError(f"没有足够的权限创建套接字，请使用管理员权限运行")
        except socket.error as e:
            raise ICMPError(f"创建套接字时出错: {e}")
        # 记录发送时间
        send_time = time.time()
        # 生成ICMP包
        checksum = 0
        header = struct.pack('!BBHHH', 8, 0, checksum, self.id, self.seq)
        data = struct.pack('!d', send_time)
        checksum = self.checksum(header + data)
        header = struct.pack('!BBHHH', 8, 0, socket.htons(checksum), self.id, self.seq)
        packet = header + data

        try:
            # 发送ICMP包
            self.sock.sendto(packet, (self.ip, 1))
            # 设置超时时间
            self.sock.settimeout(timeout)

            # 接收响应
            recv_packet, addr = self.sock.recvfrom(1024)
            # 记录接收时间
            recv_time = time.time()

            # 解析ICMP头
            icmp_header = recv_packet[20:28]
            type, code, received_checksum, packet_id, seq = struct.unpack('!BBHHH', icmp_header)

            if type == 0 and packet_id == self.id and seq == self.seq:
                # 计算时延
                delay = (recv_time - send_time) * 1000
                return delay
            else:
                raise ICMPError(f"收到返回的ICMP包异常")
        except socket.timeout:
            return None
        finally:
            self.sock.close()
            self.sock = None

class ICMPEvent:
    def __init__(self, timestamp, status, ip, rtt):
        self.timestamp = timestamp
        self.status = status
        self.ip = ip
        self.rtt = rtt

class ICMPMonitor:
    def __init__(self):
        self.config = self.load_config()
        self.logger = self.setup_logger()
        self.running = False
        self.event_queue = queue.Queue()

    def load_config(self):
        with open('config/config.yaml', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def setup_logger(self):
        logger = logging.getLogger('PingMonitor')
        logger.setLevel(logging.INFO)

        log_dir = self.config['logging']['log_dir']
        os.makedirs(log_dir, exist_ok=True)

        # 创建按天滚动的文件处理器
        handler = TimedRotatingFileHandler(
            filename=f"{log_dir}/log.txt",
            when="midnight",
            interval=1,
            backupCount=self.config['logging']['max_days'],
            encoding='utf-8'
        )
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        handler.suffix = "%Y-%m-%d.txt"
        logger.addHandler(handler)
        return logger

    def sync_ping(self, ip):
        """同步的 ping 操作函数"""
        icmp_packet = ICMPSender(ip)
        try:
            delay = icmp_packet.send(self.config['timeout'])
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            if delay is not None:
                return ICMPEvent(timestamp, 'reachable', ip, delay)
            else:
                return ICMPEvent(timestamp, 'unreachable', ip, -1)
        except Exception as e:
            self.logger.error(f"发生错误: {e}") 
            return None

    async def async_ping(self, ip, executor):
        """异步的 ping 操作函数"""
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(executor, self.sync_ping, ip)
            if result:
                self.event_queue.put(result)
                if result.status == 'reachable':
                    self.logger.info(f"{ip}:可达 - 延迟：{result.rtt:.0f} ms")
                elif result.status == 'unreachable':
                    self.logger.info(f"{ip}:不可达")
        except Exception as e:
            self.logger.error(f"发生错误: {e}")

    async def monitor_targets(self):
        """主异步函数，用于管理多个 ping 请求"""
        while self.running: 
            with ThreadPoolExecutor() as executor:
                tasks = [self.async_ping(target['ip'], executor) for target in self.config['targets']]
                await asyncio.gather(*tasks)        
            await asyncio.sleep(self.config['interval'])

    def start(self):
        """ 启动监控器，不阻塞（开启一个新的线程） """
        self.running = True
        def inner_monitor():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.monitor_targets())
            loop.close()
        thread = threading.Thread(target=inner_monitor)
        thread.daemon = True    #设置为守护线程，主线程退出时子线程也会退出
        thread.start()

    def stop(self):
        self.running = False