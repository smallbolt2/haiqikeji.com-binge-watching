import requests
import time
import logging
import random
from datetime import datetime
import os
import json
import base64
from typing import List, Dict, Optional
import threading
from queue import Queue
import concurrent.futures

class User:
    def __init__(self, base_url: str, school_id: int, username: str, password: str, study_limit: int = 3):
        # 确保 base_url 格式正确
        self.base_url = base_url.rstrip('/')
        if self.base_url.endswith('/user/login'):
            self.base_url = self.base_url[:self.base_url.rfind('/user/login')]
        if self.base_url.endswith('/user'):
            self.base_url = self.base_url[:self.base_url.rfind('/user')]
        
        self.school_id = school_id
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.running = False
        self.current_status = "未启动"
        self.current_course = None
        self.current_video = None
        self.token = None
        self.student_id = None  # 添加student_id属性
        self.setup_logging()
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json, text/plain, */*',
            'Origin': self.base_url,
            'Referer': f"{self.base_url}/user/login"
        })
        
        self.logger.info(f"初始化完成，base_url: {self.base_url}")
        self.study_limit = study_limit  # 同时学习的课程数量限制
        self.study_queue = Queue()  # 课程学习队列
        self.study_threads = []  # 学习线程列表
        self.study_lock = threading.Lock()  # 线程锁
        self.active_courses = set()  # 当前正在学习的课程ID集合

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(f'User_{self.username}')

    def update_status(self, status: str):
        self.current_status = status
        self.logger.info(f"状态更新: {status}")

    def login(self) -> bool:
        """登录系统"""
        try:
            self.update_status("正在登录")
            
            # 第一步：获取schoolId
            school_id = None
            try:
                domain = self.base_url.split('://')[-1].split('/')[0]  # 从base_url提取domain
                domain_url = f"https://{domain}/api/course/selectdomain"
                domain_params = {'domain': domain}
                
                self.logger.info(f"获取schoolId，URL: {domain_url}，参数: {domain_params}")
                domain_response = self.session.get(domain_url, params=domain_params)
                
                if domain_response.status_code == 200:
                    domain_data = domain_response.json()
                    if domain_data.get('code') == 200 and 'data' in domain_data:
                        school_id = domain_data['data'].get('id')
                        self.logger.info(f"从selectdomain获取到schoolId: {school_id}")
                        if school_id:
                            self.school_id = school_id
                else:
                    self.logger.warning(f"获取schoolId失败: HTTP {domain_response.status_code}")
            except Exception as e:
                self.logger.warning(f"获取schoolId异常: {str(e)}")
            
            # 如果没有获取到schoolId，使用默认值或已有值
            if not school_id:
                school_id = str(self.school_id)
                self.logger.info(f"使用默认或已有的schoolId: {school_id}")
            
            # 登录请求
            login_data = {
                "platform": "Android",
                "username": self.username,
                "password": self.password,
                "pushId": "140fe1da9e67b9c14a7",
                "school_id": school_id,
                "imgSign": "533560501d19cc30271a850810b09e3e",
                "imgCode": "cryd"
            }
            
            # 先获取验证码
            try:
                code_url = f"{self.base_url}/api/captcha"
                self.logger.info(f"获取验证码: {code_url}")
                code_response = self.session.get(
                    code_url,
                    params={"t": int(time.time() * 1000)}
                )
                
                if code_response.status_code != 200:
                    self.logger.error(f"获取验证码失败，状态码: {code_response.status_code}")
                    return False
                
                # 解析JSON响应获取base64图像数据和验证码ID
                try:
                    captcha_data = code_response.json()
                    if captcha_data.get('code') != 200:
                        self.logger.error(f"获取验证码失败: {captcha_data.get('msg')}")
                        return False
                    
                    # 从data字段获取base64图像数据
                    image_base64 = captcha_data.get('data')
                    # 从msg字段获取验证码ID（UUID）
                    captcha_id = captcha_data.get('msg')
                    
                    if not image_base64:
                        self.logger.error("验证码数据为空")
                        return False
                    
                    # 解码base64为二进制
                    import io
                    image_data = base64.b64decode(image_base64)
                    
                    # 使用 ddddocr 识别验证码
                    import ddddocr
                    ocr = ddddocr.DdddOcr()
                    code = ocr.classification(image_data)
                    self.logger.info(f"登录验证码识别成功: {code}，验证码ID: {captcha_id}")
                    
                    # 添加验证码到登录数据
                    login_data["imgCode"] = code
                    # 尝试添加验证码ID（可能需要）
                    if captcha_id:
                        login_data["captchaId"] = captcha_id
                        login_data["captcha_id"] = captcha_id  # 尝试不同的字段名
                except json.JSONDecodeError:
                    self.logger.warning(f"验证码响应不是JSON格式，尝试直接使用二进制数据")
                    import ddddocr
                    ocr = ddddocr.DdddOcr()
                    code = ocr.classification(code_response.content)
                    self.logger.info(f"登录验证码识别成功: {code}")
                    login_data["imgCode"] = code
            except Exception as e:
                self.logger.warning(f"获取登录验证码失败: {str(e)}")
            
            # 第一步：验证验证码（暂时注释，因为实际登陆流程可能不需要）
            verify_url = f"{self.base_url}/api/verify"
            
            # 从login_data中取出验证码相关信息
            captcha_id = login_data.get('captchaId')
            img_code = login_data.get('imgCode')
            
            self.logger.info(f"使用schoolId: {school_id}")
            
            # 第二步：发送登录请求（GET方式，参数在URL中）
            login_url = f"{self.base_url}/api/user/login"
            self.logger.info(f"发送登录请求: {login_url}")
            
            # 构建GET请求参数
            login_params = {
                'number': self.username,
                'password': self.password,
                'schoolId': school_id
            }
            
            self.logger.info(f"登录参数: {login_params}")
            
            response = self.session.get(
                login_url,
                params=login_params,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Origin': self.base_url,
                    'Referer': f"{self.base_url}/user/login"
                }
            )
            
            # 打印响应内容以便调试
            self.logger.info(f"登录响应状态码: {response.status_code}")
            self.logger.info(f"登录响应: {response.text}")
            
            if response.status_code != 200:
                self.update_status(f"登录失败: HTTP {response.status_code}")
                return False
            
            resp_data = response.json()
            
            # 检查响应中的code字段
            if resp_data.get('code') != 200 and resp_data.get('code') != 0:
                error_msg = resp_data.get('msg', '未知错误')
                self.update_status(f"登录失败: {error_msg}")
                if resp_data.get('need_code'):
                    self.logger.info("需要验证码，重试登录")
                    return self.login()  # 递归重试
                return False
            
            # 保存token
            # 第一优先级：data字段直接就是token（字符串）
            if isinstance(resp_data.get('data'), str) and resp_data['data']:
                self.token = resp_data['data']
            # 第二优先级：data是字典，token在其中
            elif 'data' in resp_data and isinstance(resp_data['data'], dict):
                self.token = resp_data['data'].get('token') or resp_data['data'].get('accessToken')
            # 第三优先级：从result字段获取
            elif 'result' in resp_data:
                self.token = resp_data['result'].get('data', {}).get('token')
            else:
                self.token = None
            
            if not self.token:
                self.logger.error(f"响应中无法找到token: {resp_data}")
                return False
            
            self.logger.info(f"成功获取token: {self.token[:50]}..." if len(self.token) > 50 else f"成功获取token: {self.token}")
            
            # 从JWT token中解析student_id
            try:
                # JWT token格式: header.payload.signature
                parts = self.token.split('.')
                if len(parts) == 3:
                    payload = parts[1]
                    # Base64解码（需要处理padding，使用urlsafe_b64decode处理JWT格式）
                    # 正确的padding计算方式
                    missing_padding = len(payload) % 4
                    if missing_padding:
                        payload += '=' * (4 - missing_padding)
                    
                    try:
                        # 先尝试 urlsafe_b64decode（JWT标准）
                        payload_decoded = base64.urlsafe_b64decode(payload)
                    except Exception:
                        # 如果失败，尝试标准 b64decode
                        payload_decoded = base64.b64decode(payload)
                    
                    payload_json = json.loads(payload_decoded)
                    
                    # 从payload中获取用户信息
                    sub = payload_json.get('sub')
                    if sub:
                        # sub字段通常是用户信息的JSON字符串
                        user_data = json.loads(sub)
                        self.student_id = user_data.get('id')
                        extracted_school_id = user_data.get('schoolId')
                        if extracted_school_id:
                            self.school_id = extracted_school_id
                            school_id = str(extracted_school_id)
                        self.logger.info(f"从token中解析出 student_id: {self.student_id}, schoolId: {self.school_id}")
            except Exception as e:
                self.logger.warning(f"解析JWT token失败: {str(e)}")
            # 更新请求头，确保token格式正确
            self.session.headers.update({
                'Authorization': self.token,
                'token': self.token,
                'Cookie': f'token={self.token}',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json, text/plain, */*',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/user/login"
            })
            
            # 保存cookies
            for cookie in response.cookies:
                self.session.cookies.set(cookie.name, cookie.value)
            
            self.update_status("登录成功")
            return True
            
        except Exception as e:
            self.logger.error(f"登录失败: {str(e)}")
            self.update_status("登录过程出错")
            return False

    def get_courses(self) -> List[Dict]:
        """获取课程列表（包括分页）"""
        try:
            self.update_status("正在获取课程列表")
            
            # 确保token存在
            if not self.token:
                self.logger.error("Token不存在，需要重新登录")
                return []
            
            # 确保student_id存在
            if not self.student_id:
                self.logger.error("StudentId不存在")
                return []
            
            # 使用正确的API地址 - yee_my_course_list
            all_courses = []
            page_num = 1
            page_size = 100  # 每页获取100个，确保能获取所有课程
            
            while True:
                course_url = f"{self.base_url}/api/user/yee_my_course_list"
                course_params = {
                    "schoolId": str(self.school_id),
                    "studentId": str(self.student_id),
                    "type": "0",
                    "pageNum": str(page_num),
                    "pageSize": str(page_size)
                }
                
                self.logger.info(f"获取课程列表（第{page_num}页），URL: {course_url}, 参数: {course_params}")
                
                response = self.session.get(
                    course_url,
                    params=course_params,
                    headers={
                        'Authorization': self.token,
                        'token': self.token,
                        'Cookie': f'token={self.token}',
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36',
                        'Accept': 'application/json'
                    }
                )
                
                self.logger.info(f"课程列表响应状态码: {response.status_code}")
                
                if response.status_code != 200:
                    self.update_status(f"获取课程列表失败: HTTP {response.status_code}")
                    break
                
                resp_data = response.json()
                
                # 检查响应格式
                if resp_data.get('code') != 200 and resp_data.get('code') != 0:
                    error_msg = resp_data.get('msg', '未知错误')
                    self.update_status(f"获取课程列表失败: {error_msg}")
                    if "登录超时" in error_msg or "token" in error_msg.lower() or "认证失败" in error_msg:
                        self.token = None  # 清除token，触发重新登录
                    break
                
                # 获取当前页的课程
                courses = resp_data.get('data', [])
                if not courses:
                    break  # 没有更多课程了
                
                all_courses.extend(courses)
                
                # 检查是否有更多页面
                total_count = resp_data.get('count', 0)
                if len(all_courses) >= total_count:
                    break
                
                page_num += 1
            
            self.logger.info(f"总共获取 {len(all_courses)} 门课程")
            
            # 对每个课程检查学习进度，只返回未完成的课程
            incomplete_courses = []
            for course in all_courses:
                course_id = course.get('id')
                course_name = course.get('courseName', '未知课程')
                
                if not course_id:
                    continue
                
                try:
                    # 获取该课程的学习进度
                    progress_url = f"{self.base_url}/api/user/get_study_progress"
                    progress_params = {
                        "schoolId": str(self.school_id),
                        "userId": str(self.student_id),
                        "courseId": str(course_id)
                    }
                    
                    progress_response = self.session.get(
                        progress_url,
                        params=progress_params,
                        headers={
                            'Authorization': self.token,
                            'token': self.token,
                            'Cookie': f'token={self.token}',
                            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36',
                            'Accept': 'application/json'
                        },
                        timeout=10
                    )
                    
                    if progress_response.status_code == 200:
                        progress_data = progress_response.json()
                        if progress_data.get('code') == 200 and 'data' in progress_data:
                            summary = progress_data['data'].get('summary', {})
                            completion_rate = summary.get('completionRate', 1)
                            total_nodes = summary.get('totalNodes', 0)
                            completed_nodes = summary.get('completedNodes', 0)
                            
                            # 如果完成率 < 100% 或者未完成所有节点，则该课程未完成
                            if completion_rate < 1.0 or completed_nodes < total_nodes:
                                incomplete_courses.append(course)
                                self.logger.info(f"课程 '{course_name}' 未完成 (完成率: {completion_rate*100:.1f}%, 已完成: {completed_nodes}/{total_nodes})")
                            else:
                                self.logger.info(f"课程 '{course_name}' 已完成")
                except Exception as e:
                    self.logger.warning(f"获取课程 {course_id} 学习进度失败: {str(e)}")
                    continue
            
            self.update_status(f"找到 {len(incomplete_courses)} 门未完成课程（总共 {len(all_courses)} 门）")
            return incomplete_courses
            
        except Exception as e:
            self.logger.error(f"获取课程列表失败: {str(e)}")
            return []
    def get_course_nodes(self, course_id: int) -> List[Dict]:
        """使用新的进度接口获取课程所有节点列表 (加入防缓存机制)"""
        try:
            if not self.token:
                self.logger.error("Token不存在，需要重新登录")
                return []
            
            progress_url = f"{self.base_url}/api/user/get_study_progress"
            
            # 【修复核心】：引入动态时间戳，强制服务器每次都返回最新进度
            progress_params = {
                "schoolId": str(self.school_id),
                "userId": str(self.student_id),
                "courseId": str(course_id),
                "t": str(int(time.time() * 1000))  # 👈 伪造一个实时变动的时间参数
            }
            
            response = self.session.get(
                progress_url,
                params=progress_params,
                headers={
                    'Authorization': self.token,
                    'token': self.token,
                    'Cookie': f'token={self.token}',
                    'Cache-Control': 'no-cache',  # 👈 双重保险：在请求头严禁服务器使用缓存
                    'Pragma': 'no-cache'
                }
            )
            
            if response.status_code != 200:
                self.logger.error(f"获取课程节点失败: HTTP {response.status_code}")
                return []
            
            resp_data = response.json()
            if resp_data.get('code') == 200 and 'data' in resp_data:
                # 直接返回 nodeProgressList 列表
                return resp_data['data'].get('nodeProgressList', [])
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取课程节点异常: {str(e)}")
            return []
            


    def get_node_progress(self, node_id: int, course_id: int) -> Dict:
        """通过获取课程整体进度，提取单个视频节点的进度 (替代失效的 video.json)"""
        try:
            
            nodes = self.get_course_nodes(course_id)
            for node in nodes:
                if str(node.get('nodeId')) == str(node_id):
                    return node
            return {}
        
        except Exception as e:
            self.logger.error(f"提取节点进度失败: {str(e)}")
            return {}
    def parse_duration(self, duration_str: str) -> int:
        """将 '1小时2分3秒' 或 '9分6秒' 等字符串解析为秒数"""
        if not duration_str:
            return 0
        
        import re
        total_seconds = 0
        
        h_match = re.search(r'(\d+)\s*小时', duration_str)
        if h_match:
            total_seconds += int(h_match.group(1)) * 3600
            
        m_match = re.search(r'(\d+)\s*分', duration_str)
        if m_match:
            total_seconds += int(m_match.group(1)) * 60
            
        s_match = re.search(r'(\d+)\s*秒', duration_str)
        if s_match:
            total_seconds += int(s_match.group(1))
            
        return total_seconds
    def check_node_status(self, node: Dict) -> str:
        """检查视频节点状态
        返回: "completed" - 已完成, "unlocked" - 已解锁未完成, "locked" - 未解锁, "error" - 错误
        """
        try:
            node_id = node.get('id')
            if not node_id:
                return "error"
            
            progress_data = self.get_node_progress(node_id)
            if not progress_data:
                return "error"
            
            study_total = progress_data.get('study_total', {})
            if not study_total:
                return "error"
            
            state = study_total.get('state')
            if state == "2":
                return "completed"
            elif state == "1":
                return "unlocked"
            elif state == "0":
                return "locked"
            else:
                return "error"
                
        except Exception as e:
            self.logger.error(f"检查视频状态失败: {str(e)}")
            return "error"

    def study_node(self, node: Dict) -> bool:
        """学习视频节点（应用心跳机制 + 本地时间模拟防卡死换课）"""
        try:
            # 错峰启动机制，防止瞬间高并发击穿服务器
            delay = random.uniform(1.0, 4.0)
            time.sleep(delay)

            node_id = node.get('id')
            course_id = node.get('course_id')
            node_name = node.get('name', '未知视频')

            if not node_id or not course_id:
                return False

            self.current_video = node_name
            self.update_status(f"正在学习: {node_name}")

            # 【新增逻辑】：在开始前，一次性提取视频的总时长和已看时长
            progress_info = self.get_node_progress(node_id, course_id)
            duration_str = progress_info.get('videoDuration', '')
            watch_duration_str = progress_info.get('watchDuration', '')
            
            total_required_seconds = self.parse_duration(duration_str)
            elapsed_seconds = self.parse_duration(watch_duration_str)
            
            # 如果解析不到时间，兜底 15 分钟
            if total_required_seconds <= 0:
                self.logger.warning(f"[{node_name}] 无法解析视频时长 ({duration_str})，默认设置兜底时长 15 分钟")
                total_required_seconds = 900
            else:
                self.logger.info(f"[{node_name}] 🎯 视频总时长: {total_required_seconds}秒, 起始已看: {elapsed_seconds}秒")

            common_headers = {
                'Authorization': self.token,
                'token': self.token,
                'Cookie': f'token={self.token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            # 1. 开启学习会话
            start_url = f"{self.base_url}/api/user/study_session_start"
            start_payload = {
                "schoolId": str(self.school_id),
                "userId": str(self.student_id),
                "courseId": str(course_id),
                "nodeId": str(node_id),
                "terminal": "web"
            }

            response = None
            try:
                headers_json = common_headers.copy()
                headers_json['Content-Type'] = 'application/json'
                response = self.session.post(start_url, json=start_payload, headers=headers_json, timeout=10)
                if response.status_code != 200:
                    headers_form = common_headers.copy()
                    headers_form['Content-Type'] = 'application/x-www-form-urlencoded'
                    response = self.session.post(start_url, data=start_payload, headers=headers_form, timeout=10)
            except Exception as e:
                self.logger.error(f"[{node_name}] 开启会话网络请求异常: {str(e)}")
                return False

            try:
                start_data = response.json()
            except Exception:
                time.sleep(3) 
                return False

            if start_data.get('code') != 200:
                time.sleep(3) 
                return False

            session_id = start_data.get('data')
            if not session_id:
                return False

            self.logger.info(f"[{node_name}] 🎉 会话成功开启！")




            # 2. 进入心跳循环
            heartbeat_url = f"{self.base_url}/api/user/study_session_heartbeat"
            if total_required_seconds<100:
                total_required_seconds = 100  # 只要服务器返回的所需学习时长小于 100 秒，就强制当成 100 秒
            heartbeat_payload = {
                "sessionId": session_id,
                "progress": str(total_required_seconds)
            }

            heartbeat_count = 0

            while self.running:
                # 严格等待 12 秒
                time.sleep(12)
                # 【核心】：我们自己本地累加 12 秒的学习时间
                elapsed_seconds += 12

                # 发送心跳包
                headers_json = common_headers.copy()
                headers_json['Content-Type'] = 'application/json'
                try:
                    hb_response = self.session.post(heartbeat_url, json=heartbeat_payload, headers=headers_json, timeout=10)
                except Exception as e:
                    self.logger.error(f"[{node_name}] 心跳请求网络异常: {e}")
                    time.sleep(2)
                    continue
                




                if hb_response.status_code != 200:
                    headers_form = common_headers.copy()
                    headers_form['Content-Type'] = 'application/x-www-form-urlencoded'
                    hb_response = self.session.post(heartbeat_url, data=heartbeat_payload, headers=headers_form, timeout=10)

                try:
                    hb_data = hb_response.json()
                except Exception:
                    time.sleep(5)
                    continue

                if hb_data.get('code') == 200:
                    heartbeat_count += 1
                elif hb_data.get('code') == 500 and "频繁" in str(hb_data.get('data', '')):
                    self.logger.warning(f"[{node_name}] 心跳被限流，延长等待时间...")
                    time.sleep(5)

                # 每成功发送 3 次心跳 (约 36-40 秒)，打印一次本地计算的进度
                if heartbeat_count % 3 == 0:
                    percent = min(100, int((elapsed_seconds / total_required_seconds) * 100))
                    #self.logger.info(f"[{node_name}] 本地模拟学习进度: {percent}% ({elapsed_seconds}/{total_required_seconds}秒)")

                # 【核心防护】：如果本地看的时间已经达到了视频总时长（加15秒缓冲确保服务器记满），直接强行结束本视频！
                if hb_data.get('code') == 500 :
                    self.logger.info(f"[{hb_data}] 🏆 异常")
                    continue
                else:
                    break
            # 视频结束时提交学习完成记录
            end_success = self.end_study_session(node_name, course_id, node_id, session_id, elapsed_seconds)
            if not end_success:
                self.logger.warning(f"[{node_name}] 学习会话结束提交失败，可能不会记录完成。")

            return end_success

        except Exception as e:
            self.logger.error(f"学习节点失败: {str(e)}")
            time.sleep(3)
            return False

    def end_study_session(self, node_name: str, course_id: int, node_id: int, session_id: str, elapsed_seconds: int) -> bool:
        """提交视频学习完成状态到 study_session_end 接口。"""
        try:
            end_url = f"{self.base_url}/api/user/study_session_end"
            # 真实请求抓包显示：POST + JSON body {"sessionId":"..."}
            payload = {"sessionId": session_id}

            common_headers = {
                'Authorization': self.token,
                'token': self.token,
                'Cookie': f'token={self.token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/plain, */*',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/student/course-study"
            }

            # 给后端一点时间登记会话（多数环境里立即生效，但稳妥一点）
            time.sleep(0.5)

            # 优先以 JSON POST 精确发送 sessionId（与浏览器抓包一致）
            try:
                response = self.session.post(end_url, json=payload, headers=common_headers, timeout=10)
            except Exception as e:
                self.logger.error(f"[{node_name}] 提交结束请求网络错误: {e}")
                return False

            # 兼容性回退：如果服务器不接受 JSON，再尝试 form-data
            if response.status_code != 200:
                headers_form = common_headers.copy()
                headers_form['Content-Type'] = 'application/x-www-form-urlencoded'
                response = self.session.post(end_url, data={'sessionId': session_id}, headers=headers_form)

            try:
                end_data = response.json()
            except Exception as e:
                self.logger.error(f"[{node_name}] 解析结束接口响应失败: {e} / raw: {response.text}")
                return False

            if end_data.get('code') == 200:
                self.logger.info(f"[{node_name}] 已成功提交学习结束接口: {end_data.get('msg')}")
                return True

            self.logger.warning(f"[{node_name}] 学习结束接口返回异常: {response.status_code} {end_data}")
            return False
        except Exception as e:
            self.logger.error(f"[{node_name}] 提交学习结束接口失败: {str(e)}")
            return False

    def handle_captcha(self) -> str:
        """处理验证码"""
        try:
            self.update_status("正在识别验证码")
            
            # 获取验证码图片
            response = self.session.get(
                f"{self.base_url}/api/captcha",
                params={"t": int(time.time() * 1000)}
            )
            
            # 尝试解析JSON格式的响应
            try:
                captcha_data = response.json()
                if captcha_data.get('code') == 200:
                    image_base64 = captcha_data.get('data')
                    if image_base64:
                        import io
                        image_data = base64.b64decode(image_base64)
                    else:
                        image_data = response.content
                else:
                    image_data = response.content
            except json.JSONDecodeError:
                image_data = response.content
            
            # 使用 ddddocr 识别验证码
            import ddddocr
            ocr = ddddocr.DdddOcr()
            code = ocr.classification(image_data)
            
            self.update_status(f"验证码识别成功: {code}")
            return code
            
        except Exception as e:
            self.logger.error(f"验证码识别失败: {str(e)}")
            return ""

    def study_course(self, course: Dict) -> bool:
        """学习整个课程（适配新版数据结构）"""
        try:
            course_name = course.get('name', '未知课程')
            course_id = course.get('id')
            if not course_id:
                self.logger.error(f"课程数据无效: {course}")
                return False
                
            self.current_course = course_name
            self.update_status(f"开始学习课程: {course_name}")
            
            nodes = self.get_course_nodes(course_id)
            if not nodes:
                self.logger.warning(f"未能获取到课程 [{course_name}] 的视频节点")
                return False
            
            for node in nodes:
                if not self.running:
                    break
                    
                chapter_name = node.get('chapterName', '未知章节')
                node_name = node.get('nodeName', '未知视频')
                node_id = node.get('nodeId')
                state = node.get('state', 0)
                progress_percent = node.get('progressPercent', 0)
                
                if state == 2 or progress_percent >= 100:
                    self.logger.info(f"节点已完成，跳过: [{chapter_name}] -> {node_name}")
                    continue
                
                self.logger.info(f"准备学习未完成节点: [{chapter_name}] -> {node_name}")
                
                study_data = {
                    'id': node_id,
                    'name': node_name,
                    'video_state': state,
                    'course_id': course_id
                }
                
                try:
                    success = self.study_node(study_data)
                    # 【核心防护】：如果开启学习失败，立刻踩刹车跳出循环，防止引发请求风暴！
                    if not success:
                        self.logger.warning(f"[{node_name}] 学习异常，安全暂停该课程的学习。")
                        break  
                except Exception as e:
                    self.logger.error(f"处理视频节点 {node_name} 失败: {str(e)}")
                    break
            
            return True
            
        except Exception as e:
            self.logger.error(f"学习课程失败: {str(e)}")
            return False
            


    def study_course_thread(self, course: Dict):
        """在线程中学习课程"""
        try:
            course_id = course.get('id')
            if not course_id:
                return
            
            with self.study_lock:
                if course_id in self.active_courses:
                    return
                self.active_courses.add(course_id)
            
            try:
                self.study_course(course)
            finally:
                with self.study_lock:
                    self.active_courses.remove(course_id)
        except Exception as e:
            self.logger.error(f"课程学习线程异常: {str(e)}")

    def run(self):
        """主运行逻辑，使用线程池处理并发"""
        self.running = True
        self.update_status("开始运行")
        
        while self.running:
            try:
                # 登录
                if not self.login():
                    self.update_status("登录失败，等待重试")
                    time.sleep(60)
                    continue
                
                # 获取未完成课程
                courses = self.get_courses()
                if not courses:
                    self.update_status("没有未完成课程，等待重试")
                    time.sleep(300)
                    continue
                
# 使用线程池处理课程
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.study_limit) as executor:
                    # 提交所有课程到线程池
                    futures = []
                    for course in courses:
                        if not self.running:
                            break
                            
                        # 1. 修复名称为空的问题：获取课程名称并统一赋值给 'name' 供后续方法使用
                        course_name = course.get('courseName') or course.get('name', '未知课程')
                        course['name'] = course_name  
                        course_id = course.get('id')
                        
                        # 2. 检查是否在学习时间范围内
                        start_date_str = course.get('startDate')
                        end_date_str = course.get('endDate')
                        
                        if start_date_str and end_date_str:
                            try:
                                # 截取前10位(YYYY-MM-DD)，防止部分接口返回带时分秒的格式
                                start_date = datetime.strptime(start_date_str[:10], '%Y-%m-%d').date()
                                end_date = datetime.strptime(end_date_str[:10], '%Y-%m-%d').date()
                                current_date = datetime.now().date()
                                
                                # 如果当前日期不在开始和结束日期之间，则跳过
                                if not (start_date <= current_date <= end_date):
                                    self.logger.info(f"当前课程[{course_name}][{course_id}] 不在学习时间内 ({start_date_str} 至 {end_date_str}), 跳过")
                                    continue
                            except Exception as e:
                                self.logger.warning(f"解析课程日期失败 [{start_date_str}] - [{end_date_str}]: {str(e)}")
                                
                        # 注：此处已删除原先 buggy 的 progress 和 state 检查。
                        # 因为在 get_courses 中，已经通过 completion_rate 严格筛选出未完成的课程了。
                            
                        self.logger.info(f"准备开始学习课程[{course_name}][{course_id}]")
                        futures.append(executor.submit(self.study_course, course))
                    
                    # 等待所有课程完成
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.error(f"课程学习异常: {str(e)}")
                
                # 完成一轮后等待
                wait_time = random.randint(300, 600)
                self.update_status(f"本轮完成，等待 {300} 秒")
                time.sleep(300)
                
            except Exception as e:
                self.logger.error(f"运行出错: {str(e)}")
                self.update_status("运行过程出错")
                time.sleep(60)

    def stop(self):
        """停止运行"""
        self.running = False
        self.update_status("正在停止")
        # 等待所有学习线程结束
        for thread in self.study_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        self.update_status("已停止")

    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            'status': self.current_status,
            'course': self.current_course,
            'video': self.current_video,
            'running': self.running
        } 