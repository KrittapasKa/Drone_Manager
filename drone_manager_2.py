import logging
import socket
import sys
import threading
import time

# การตั้งค่าการบันทึก
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)  # สร้าง logger ที่มีชื่อเดียวกับโมดูลที่กำลังทำงาน

class DroneManager(object):
    def __init__(self, host_ip='192.168.10.3', host_port=8889,
                 drone_ip='192.168.10.1', drone_port=8889):
        # การตั้งค่าคุณสมบัติของคลาส
        self.host_ip = host_ip
        self.host_port = host_port
        self.drone_ip = drone_ip
        self.drone_port = drone_port
        self.drone_address = (drone_ip, drone_port)

        # การสร้างและเชื่อมต่อ socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host_ip, self.host_port))

        # การตั้งค่าเริ่มต้น
        self.response = None  # ตัวแปรสำหรับเก็บข้อมูลการตอบสนอง
        self.stop_event = threading.Event()  # สร้าง event สำหรับการหยุดเธรด
        self.response_thread = threading.Thread(
            target=self.receive_response,  # กำหนดฟังก์ชันที่เธรดจะเรียกใช้
            args=(self.stop_event,)  # ส่ง stop_event เป็น argument ไปยังฟังก์ชัน
        )
        self.response_thread.start()  # เริ่มต้นเธรด

        # ส่งคำสั่งเริ่มต้นให้กับโดรน
        self.send_command('command')
        self.send_command('streamon')

    def receive_response(self, stop_event):
        # ฟังก์ชันที่ทำงานในเธรดเพื่อตอบสนองการรับข้อมูลจากโดรน
        while not stop_event.is_set():  # ทำงานต่อไปจนกว่าจะมีการตั้งค่า stop_event
            try:
                self.response, ip = self.socket.recvfrom(3000)  # รับข้อมูลจาก socket
                logger.info({'action': 'receive_response', 'response': self.response})  # บันทึกข้อมูลที่ได้รับ
            except socket.error as ex:
                logger.error({'action': 'receive_response', 'ex': ex})  # บันทึกข้อผิดพลาดหากเกิดขึ้น
                break

    def stop(self):
        # ฟังก์ชันสำหรับหยุดการทำงานของเธรดและปิดการเชื่อมต่อ
        self.stop_event.set()  # ตั้งค่า stop_event เพื่อหยุดการทำงานของเธรด
        retry = 0
        while self.response_thread.is_alive():  # ตรวจสอบว่าเธรดยังทำงานอยู่หรือไม่
            time.sleep(0.3)  # หยุดชั่วคราวเพื่อไม่ให้ใช้ทรัพยากรมากเกินไป
            if retry > 30:  # หากลองมานานเกินไป
                break
            retry += 1
        self.socket.close()  # ปิดการเชื่อมต่อ socket

    def send_command(self, command):
        # ฟังก์ชันสำหรับส่งคำสั่งไปยังโดรน
        logger.info({'action': 'send_command', 'command': command})  # บันทึกคำสั่งที่ส่งออกไป
        self.socket.sendto(command.encode('utf-8'), self.drone_address)  # ส่งคำสั่งเป็นข้อมูล UDP
        retry = 0
        self.response = None  # เคลียร์ข้อมูลการตอบสนองก่อนการส่งคำสั่งใหม่
        while self.response is None:  # รอจนกว่าจะได้รับการตอบสนอง
            time.sleep(0.3)  # หยุดชั่วคราวเพื่อไม่ให้ใช้ทรัพยากรมากเกินไป
            if retry > 3:  # หากลองมานานเกินไป
                break
            retry += 1

        if self.response is None:
            response = None  # หากไม่มีการตอบสนอง
        else:
            response = self.response.decode('utf-8')  # แปลงข้อมูลการตอบสนองเป็นสตริง
        self.response = None  # เคลียร์ข้อมูลการตอบสนองหลังจากการประมวลผล
        return response

    def takeoff(self):
        # ฟังก์ชันสำหรับสั่งให้โดรนขึ้นบิน
        return self.send_command('takeoff')

    def land(self):
        # ฟังก์ชันสำหรับสั่งให้โดรนลงจอด
        return self.send_command('land')


if __name__ == '__main__':
    drone_manager = DroneManager()  # สร้างอ็อบเจกต์ของ DroneManager
    drone_manager.takeoff()  # สั่งให้โดรนขึ้นบิน
    time.sleep(10)  # รอ 10 วินาที
    drone_manager.land()  # สั่งให้โดรนลงจอด
    drone_manager.stop()  # หยุดการทำงานของเธรดและปิดการเชื่อมต่อ
