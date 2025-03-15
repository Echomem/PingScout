import time
import socket
import struct
import yaml
import logging
from logging.handlers import TimedRotatingFileHandler
import threading
import random
import os
import queue
from concurrent.futures import ThreadPoolExecutor

class ICMPError(Exception):
    """ 自定义ICMP错误异常类，用于在ICMP包发送或接收过程中发生错误时抛出异常并提供错误信息 """
    def __init__(self, message):
        super().__init__()
        self.message = message

    def __str__(self):
        return self.message

class ICMPPacket:
    """ ICMP包类，用于封装ICMP包的相关信息和方法 """
    def __init__(self, id, seq=1):
        self.id = id
        self.seq = seq
    
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
    
    def pack(self):
        """ 打包ICMP包 """
        icmp_type = 8   # ICMP 类型（8 表示回显请求）
        icmp_code = 0
        icmp_checksum = 0
        header = struct.pack('!BBHHH', icmp_type, icmp_code, icmp_checksum, self.id, self.seq)
        data = struct.pack('!d', time.time())
        icmp_checksum = self.checksum(header + data)
        header = struct.pack('!BBHHH', icmp_type, icmp_code, socket.htons(icmp_checksum), self.id, self.seq)
        packet = header + data
        return packet

class ICMPSender:
    """ ICMP发送器类，用于发送ICMP包并接收响应 """
    def __init__(self, ip):
        self.id = random.randint(0, 65535)
        self.ip = ip
        self.sock = None

    def send(self, count=1, timeout=1):
        """ 
            发送ICMP包-阻塞 
            count: 发送次数
            timeout: 超时时间（秒）
        """
        try:
            icmp = socket.getprotobyname('icmp')
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
            self.sock.settimeout(timeout)
        except PermissionError:
            raise ICMPError(f"没有足够的权限创建套接字，请使用管理员权限运行")
        except socket.error as e:
            raise ICMPError(f"创建套接字发生错误:{e}")

        rtts = []   # 存储每个数据包的往返时间
        successful_count = 0    # 成功发送的数据包数量
        failed_count = 0        # 失败发送的数据包数量
        try:
            for seq in range(1, count+1):
                send_time = time.time()
                packet = ICMPPacket(self.id, seq).pack()
                try:
                    self.sock.sendto(packet, (self.ip, 0))
                    recv_packet, addr = self.sock.recvfrom(1024)
                    recv_time = time.time()
                    # 解析ICMP头
                    icmp_header = recv_packet[20:28]
                    type, code, received_checksum, packet_id, received_seq = struct.unpack('!BBHHH', icmp_header)
                    if type == 0 and packet_id == self.id and received_seq == seq:
                        # 计算时延
                        delay = (recv_time - send_time) * 1000
                        rtts.append(delay)
                        successful_count += 1
                    else:
                        failed_count += 1
                except socket.timeout:
                    failed_count += 1
                    continue
        except Exception as e:
            raise ICMPError(f"发送ICMP包发生错误:{e}")
        finally:
            self.sock.close()
        return rtts, successful_count, failed_count

class PingResult:
    """ Ping结果类，用于封装Ping操作的结果信息 """
    REACHABLE = 'reachable'
    UNREACHABLE = 'unreachable'

    def __init__(self, ip, successful_count=0, loss_rate=100, rtts=None):
        self.timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        self.ip = ip 
        self.successful_count = successful_count
        self.loss_rate = loss_rate
        if loss_rate >= 100:
            self.status = self.UNREACHABLE
        else:
            self.status = self.REACHABLE
        self.avg_rtt = sum(rtts) / len(rtts) if rtts else None
        self.max_rtt = max(rtts) if rtts else None
        self.min_rtt = min(rtts) if rtts else None

    def __str__(self):
        if self.status == self.REACHABLE:
            return f"{self.timestamp} Ping - {self.ip}: {self.status} 最大时延:{self.max_rtt:.0f}ms 最小时延:{self.min_rtt:.0f}ms 平均时延:{self.avg_rtt:.0f}ms 丢包率:{self.loss_rate}%"
        return f"{self.timestamp} Ping - {self.ip}: {self.status}"

class PingMonitor:
    """ Ping监视器类，用于循环监控配置文件中IP目标设备的Ping状态 """
    def __init__(self):
        self.config = self.load_config()
        self.logger = self.setup_logger()
        self.ping_events = queue.Queue()
        self.running = False
        self.thread_num = len(self.config['targets'])
        self.thread_num = self.thread_num if self.thread_num > 1 else 1

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

    def ping(self, ip):
        """ 同步函数 ping 并返回结果 """
        sender = ICMPSender(ip)
        try:
            rtts, successful_count, failed_count = sender.send(self.config['count'], self.config['timeout'])
            loss_rate = failed_count / self.config['count'] * 100   # 计算丢包率
            return PingResult(ip, successful_count, loss_rate, rtts)
        except Exception as e:
            self.logger.error(f"ping发生错误: {e}") 
            return None

    def _ping(self, ip):
        """ 调用ping函数并将结果存入队列 """
        try:
            result = self.ping(ip)
            if result:
                self.ping_events.put(result)
                self.logger.info(result)
        except Exception as e:
            self.logger.error(f"_ping发生错误: {e}")

    def monitor_targets(self):
        """ 使用线程池发送多个 ping 请求 """
        with ThreadPoolExecutor(max_workers=self.thread_num) as executor:
            while self.running: 
                for target in self.config['targets']:
                    executor.submit(self._ping, target['ip'])      
                time.sleep(self.config['interval'])

    def start(self):
        # 启动监控器，不阻塞（开启一个新的线程）
        self.running = True
        thread = threading.Thread(target=self.monitor_targets)
        thread.daemon = True    #设置为守护线程，主线程退出时子线程也会退出
        thread.start()

    def stop(self):
        self.running = False
