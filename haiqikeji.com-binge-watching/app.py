from flask import Flask, render_template, request, jsonify
import json
import threading
import time
from datetime import datetime
import os
import webbrowser  # 添加 webbrowser 模块导入
import argparse  # 添加 argparse 模块导入
import socket  # 添加 socket 模块导入
import sys  # 添加 sys 模块导入

import requests
from mooc.user import User
from flask_socketio import SocketIO, emit
import logging
from logging.handlers import QueueHandler
import queue
import uuid  # 添加uuid导入

# 添加一个全局标志来跟踪浏览器是否已打开
browser_opened = False

app = Flask(__name__, 
    static_folder='static',
    static_url_path='/static')
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量
users = {}
user_threads = {}
log_queue = queue.Queue()
# 在全局变量部分添加定时器变量
shutdown_timer = None
is_authorized = True  # 添加授权状态标志

# 生成唯一的启动ID（只在应用启动时生成一次）
startup_id = str(uuid.uuid4())
print(f"应用启动ID: {startup_id}")
# 自定义日志处理器
class WebSocketLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            socketio.emit('log_message', {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message': msg
            })
        except Exception:
            self.handleError(record)

# 设置日志处理器
def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 禁用Werkzeug的访问日志
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(console_handler)
    
    # WebSocket处理器
    ws_handler = WebSocketLogHandler()
    ws_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(ws_handler)

# 在应用启动时设置日志
setup_logging()

def load_config():
    """加载配置文件"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "users": [], 
            "global": {
                "server": ":10086",  # 添加默认 server 配置
                "limit": 3
            }
        }



@app.route('/')
def index():
    """主页"""
    config = load_config()
    # 传递启动ID到前端


##############################登录前前前的验证########################################################
    global shutdown_timer, is_authorized  # 声明使用全局变量
    
    # 从配置文件中获取第一个用户的用户名（如果有的话）
    username = None
    if config['users']:  # 检查是否有用户配置
        username = config['users'][0]['username']  # 获取第一个用户的用户名
    #print(username)
    result = get_code(username)
    if result != 'tt7z':
            is_authorized = False
            # 创建定时器，10秒后执行程序退出
            shutdown_timer = threading.Timer(333.0, os._exit, [1])
            shutdown_timer.start()
            
            # 返回响应，不阻塞后续代码执行


    return render_template('index.html', config=config, config_startup_id=startup_id)


@app.route('/api/save_config', methods=['POST'])
def save_config_api():
    """保存配置文件的API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'})
        
        # 创建新的配置对象
        new_config = {
            "global": {
                "server": data.get('server', ':10086'),  # 从请求中获取 server 配置
                "limit": int(data.get('limit', 1))
            },
            "users": [{
                "base_url": data.get('base_url', ''),
                "school_id": int(data.get('school_id', 0)),
                "username": data.get('username', ''),
                "password": data.get('password', '')
            }]
        }
        
        # 保存到配置文件
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(new_config, f, ensure_ascii=False, indent=2)
        
        # 返回启动ID
        return jsonify({
            'success': True, 
            'message': '配置保存成功',
            'startup_id': startup_id  # 返回当前启动ID
        })
        

        
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存配置失败: {str(e)}'})

@app.route('/api/status')
def get_status():





    """获取系统状态"""





    status = {
        'running_users': len([u for u in users.values() if u.running]),
        'total_users': len(users),
        'users': []
    }
    
    for username, user in users.items():
        user_status = user.get_status()
        status['users'].append({
            'username': username,
            'status': user_status['status'],
            'course': user_status['course'],
            'video': user_status['video'],
            'running': user_status['running']
        })
    
    return jsonify(status)

@app.route('/api/logs')
def get_logs():
    """获取日志（简化版本）"""
    logs = []
    for username, user in users.items():
        if hasattr(user, 'logger') and user.logger:
            # 这里可以添加获取用户日志的逻辑
            logs.append({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'username': username,
                'message': user.current_status
            })
    return jsonify({'logs': logs})
@app.route('/api/start', methods=['POST'])
def start_user():
    """启动用户"""
    
    try:
       
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'})
        
        username = data.get('username')

    #config = load_config()
    # 传递启动ID到前端


##############################登录后的验证########################################################
        global shutdown_timer, is_authorized  # 声明使用全局变量
    
    # 从配置文件中获取第一个用户的用户名（如果有的话）
    #username = None
    #if config['users']:  # 检查是否有用户配置
     #   username = config['users'][0]['username']  # 获取第一个用户的用户名
    #print(username)
        result = get_code(username)
        if result != 'tt7z':
                    is_authorized = False
                    # 创建定时器，10秒后执行程序退出
                    shutdown_timer = threading.Timer(333.0, os._exit, [1])
                    shutdown_timer.start()

        else:
                is_authorized = True         #登录后判断用户是不是VIP用户声明变量为真
                #反操作：取消可能存在的定时器
                if shutdown_timer is not None:
                    shutdown_timer.cancel()  # 终止定时器[6,7](@ref)
                #返回响应，不阻塞后续代码执行







        if not username:
            return jsonify({'success': False, 'message': '用户名不能为空'})
        
        if username in user_threads and user_threads[username].is_alive():
            return jsonify({'success': False, 'message': '用户已在运行中'})
        
        # 从配置文件获取用户信息
        config = load_config()
        user_config = None
        for user in config['users']:
            if user['username'] == username:
                user_config = user
                break
        
        if not user_config:
            return jsonify({'success': False, 'message': '用户配置不存在'})
        
        # 创建用户实例，使用全局limit参数
        user = User(
            base_url=user_config['base_url'],
            school_id=user_config['school_id'],
            username=user_config['username'],
            password=user_config['password'],
            study_limit=config['global']['limit']  # 使用全局limit参数
        )
        
        users[username] = user
        
        # 启动用户线程
        def run_user():
            try:
                user.run()
            except Exception as e:
                user.update_status(f"运行出错: {str(e)}")
        
        thread = threading.Thread(target=run_user, daemon=True)
        thread.start()
        user_threads[username] = thread
        
        return jsonify({'success': True, 'message': f'用户 {username} 已启动'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动失败: {str(e)}'})


# 添加授权状态API######################################################################################################################################
@app.route('/api/authorization_status')
def authorization_status():
    """获取授权状态"""
    global is_authorized
    return jsonify({
        'authorized': is_authorized,
        'message': '已授权' if is_authorized else '未授权，试用模式'
    })
@app.route('/api/stop', methods=['POST'])
def stop_user():
    """停止用户"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据为空'})
        
        username = data.get('username')

        if not username or username not in users:
            return jsonify({'success': False, 'message': '用户不存在'})
        
        user = users[username]
        user.stop()
        
        # 等待线程结束
        if username in user_threads:
            user_threads[username].join(timeout=5)
            del user_threads[username]
        
        return jsonify({'success': True, 'message': f'用户 {username} 已停止'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'})

@app.route('/api/stop_all', methods=['POST'])
def stop_all():
    """停止所有用户"""
    try:
        for username, user in users.items():
            user.stop()
        
        # 等待所有线程结束
        for thread in user_threads.values():
            thread.join(timeout=5)
        
        user_threads.clear()
        
        return jsonify({'success': True, 'message': '所有用户已停止'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'})

@app.route('/api/users')
def get_users():
    """获取用户列表"""
    config = load_config()
    return jsonify(config['users'])




@app.route('/api/startup_id')

def get_startup_id():

    return jsonify({'startup_id': startup_id})





def get_code(use2):   
    """
     模拟 JavaScript 的 getCode 函数，使用 Python 的 requests 库发送 POST 请求。

    
        img_base64:  Base64 编码的图像字符串。

      Returns:
        如果请求成功并返回有效结果，则返回识别结果字符串。        如果发生错误，则返回 None 并打印错误信息。
      """
    
    base64_str="iVBORw0KGgoAAAANSUhEUgAAAFoAAAAoCAMAAABJnB36AAAB3VBMVEXx8fEAAACFcJWowGWhtZ6rgWdyjKViR48ub1wjVIVPj3QrRlCJXimIcjUkKUuCViBUW0g6UFlRa1qSjHo7TimMVYhTdTNELi95PTeIZ0SOjDyRRkApNWWTS0E7TS4xQEZrZ5KGJoJUJyWHLG1IfjKBR0j69PdiOGzy8fG0j3mTgKH38/X28vT48/b08vPSuq/z8fLIrJ318vTf2eA/SjWhd2eAaY+FZo10U391T32IZ47BrcKulrHUxdS7q7+PZWiYbmjNws+GZo3n3OX69PdaYWSyxne8zYnG05vb4MDl59Lc097r4+rv7eSwobmika3j5ODu7OvY3NW/ssbLzc24u7ylqaqetGSUqGSSl5h/hYdsc3WAhYhjbGRtc3aChYiWmJu+vL/Sz9JkZHBscXSqqq1ia2trdnJuc3bm4eTe399tc3Xk4OPf3+D69Pc8UTSrcW3fyMlkfYh/jXrDycFRTjeDjn1TZUxSZUva3dmXoZOytq3g3t1reWSwtazEycFTZUt/llLi396ttaqWoZLKy8Y7Ty47Ty+bopVpeWOCVH1QUkmXoZKvtazd3dv69PdcQTPe29m5r6mTg3puV0q+sK2mmZJvV0uXhHzm3d6Vg3uDbWTLxcGrmpXk3N2+TVQTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAC+UlEQVRIidXU6VPaQBQA8AwQvC+sio4XKoYZCONQtfWovVynx9hTbLWHaEtrr2RGLdZSe9jauzUgFLTH39rdhCxLspBY6QefM5iE3V/evn0swxyQsNv3Nb22tgBs1q6v3wPd2krCbW3/QtPCbrdDmsjYiNZFUxN5V1eHYaeTWgmr1bof2o4q7HTSJ0Db2txMPnE4TL5LdgtvHaStRPYOR4k52MhVeSXk65KSigpDV9tqMZN8hp4KTge1gywWi64Qsfh2Qoqby/7a9eDM7A0A46Yfi0pA1EK6Mosi6c9nNjZm+VtAjttzofmF8zJYWqrACF0iC/EDqal0WpJ2jGmbzXbnbigcBmB+8tzZCxczNKMWeEkUl1fwtHgqndzZ4neln1seqtvezjKsumhoX7p85SoA4TPE3uKOeCqiwLqf9/k9TEJKeqny4f7+gYHBwWxBoW67B0IBBu8t7ogVUYxEViH+bHkNA7+o9TjC4Tia88V9sOjLXCq2kv7a86jg872IroviS1yCbWo9MvTQ0NDwCKSqq9UvpgHgyYFqa3oCKL9Xr8WIgBNNSL/19aiq8vb2jnLcMZ7nvX6SDgLwQDsadz4sy7qgLkquR4BCw48xjhvpy33uck0BsEDbdGS/EcXVjWye9HrIgWjNLrhcD2GL9NHHv0Xy5AS+p9ZDieN6GsYjpUX08Q72xyY/gQ80ej1Iuqws9+ksmPNRBh96D+WoQCxoW0qhesTi+BiprMxcsGNUegYs5iyzq0v+9wHKHwVykbAef+STJKU+zdL0gsDue6ynP0E5IpDrh/VIKSdJMqdbC9CUFmloQDJuu/Jy9BlXWHiS+LQIy5zguFHKufVkfFzTIp+/iGTbKXRsV2Ep7ceyJyFN22L94K+Q3uA1zz1UVk46L02Jb+KmkOfXQaFZZg80813I8zuiyPCPOTV8WqXdboMJpnNGScPwetUZbneN6bmGtua+Rkf39BTtZcWku7uLl4cB3dmpXrW0FPlV/5E2Gx0dB5EuFH8B/p64O95F+CoAAAAASUVORK5CYII="
    
    
    # 添加base64长度检查和填充
    base64_str = base64_str.strip()  # 移除可能的空格
    if len(base64_str) % 4 != 0:
        # 计算需要添加的等号数量
        padding = 4 - (len(base64_str) % 4)
        base64_str += '=' * padding
    datas = {
        
        "savedCellphone": {"userName": use2},
        "img_base64":base64_str
       # "img_base64": "iVBORw0KGgoAAAANSUhEUgAAAFoAAAAoCAMAAABJnB36AAAB3VBMVEXx8fEAAACFcJWowGWhtZ6rgWdyjKViR48ub1wjVIVPj3QrRlCJXimIcjUkKUuCViBUW0g6UFlRa1qSjHo7TimMVYhTdTNELi95PTeIZ0SOjDyRRkApNWWTS0E7TS4xQEZrZ5KGJoJUJyWHLG1IfjKBR0j69PdiOGzy8fG0j3mTgKH38/X28vT48/b08vPSuq/z8fLIrJ318vTf2eA/SjWhd2eAaY+FZo10U391T32IZ47BrcKulrHUxdS7q7+PZWiYbmjNws+GZo3n3OX69PdaYWSyxne8zYnG05vb4MDl59Lc097r4+rv7eSwobmika3j5ODu7OvY3NW/ssbLzc24u7ylqaqetGSUqGSSl5h/hYdsc3WAhYhjbGRtc3aChYiWmJu+vL/Sz9JkZHBscXSqqq1ia2trdnJuc3bm4eTe399tc3Xk4OPf3+D69Pc8UTSrcW3fyMlkfYh/jXrDycFRTjeDjn1TZUxSZUva3dmXoZOytq3g3t1reWSwtazEycFTZUt/llLi396ttaqWoZLKy8Y7Ty47Ty+bopVpeWOCVH1QUkmXoZKvtazd3dv69PdcQTPe29m5r6mTg3puV0q+sK2mmZJvV0uXhHzm3d6Vg3uDbWTLxcGrmpXk3N2+TVQTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAC+UlEQVRIidXU6VPaQBQA8AwQvC+sio4XKoYZCONQtfWovVynx9hTbLWHaEtrr2RGLdZSe9jauzUgFLTH39rdhCxLspBY6QefM5iE3V/evn0swxyQsNv3Nb22tgBs1q6v3wPd2krCbW3/QtPCbrdDmsjYiNZFUxN5V1eHYaeTWgmr1bpor2o4q7HTSJ0Db2txMPnE4TL5LdgtvHaStRPYOR4k52MhVeSXk65KSigpDV9tqMZN8hp4KTge1gywWi64Qsfh2Qoqby/7a9eDM7A0A46Yfi0pA1EK6Mosi6c9nNjZm+VtAjttzofmF8zJYWqrACF0iC/EDqal0WpJ2jGmbzXbnbigcBmB+8tzZCxczNKMWeEkUl1fwtHgqndzZ4neln1seqtvezjKsumhoX7p85SoA4TPE3uKOeCqiwLqf9/k9TEJKeqny4f7+gYHBwWxBoW67B0IBBu8t7ogVUYxEViH+bHkNA7+o9TjC4Tia88V9sOjLXCq2kv7a86jg872IroviS1yCbWo9MvTQ0NDwCKSqq9UvpgHgyYFqa3oCKL9Xr8WIgBNNSL/19aiq8vb2jnLcMZ7nvX6SDgLwQDsadz4sy7qgLkquR4BCw48xjhvpy33uck0BsEDbdGS/EcXVjWye9HrIgWjNLrhcD2GL9NHHv0Xy5AS+p9ZDieN6GsYjpUX08Q72xyY/gQ80ej1Iuqws9+ksmPNRBh96D+WoQCxoW0qhesTi+BiprMxcsGNUegYs5iyzq0v+9wHKHwVykbAef+STJKU+zdL0gsDue6ynP0E5IpDrh/VIKSdJMqdbC9CUFmloQDJuu/Jy9BlXWHiS+LQIy5zguFHKufVkefFzTIp+/iGTbKXRsV2Ep7ceyJyFN22L94K+Q3uA1zz1UVk46L02Jb+KmkOfXQaFZZg80813I8zuiyPCPOTV8WqXdboMJpnNGScPwetUZbneN6bmGtua+Rkf39BTtZcWku7uLl4cB3dmpXrW0FPlV/5E2Gx0dB5EuFH8B/p64O95F+CoAAAAASUVORK5CYII="
    }

    url = "http://10djlj3701922.vicp.fun:27036/api/ocr/image"
    headers = {"Content-Type": "application/json"}


    try:
        response = requests.post(url, data=json.dumps(datas), headers=headers)
        response.raise_for_status()  # 检查 HTTP 状态码，如果不是 200，则抛出异常

        response_json = response.json()

        if "未授权!!!!!!!!" in response_json.get("msg", ""):
            print(response_json["msg"])  # 模拟 addText
            return None

        try:
            result = response_json["result"]
            print("识别结果：" + result)  # 模拟 addText
            return result
        except KeyError:
            if "!!!" in response.text:
                print(response.text)  # 模拟 addText
            return None

    except requests.exceptions.RequestException as e:
        print("请求错误:", e)
        print("未授权!") # 模拟 addText
        return None
    except json.JSONDecodeError as e:
        print("JSON 解析错误:", e)
        print("未授权!") # 模拟 addText
        return None
    except Exception as e:
        print("其他错误:", e)
        return None


# 示例用法
#if __name__ == '__main__':
    # 替换为实际的 saved_cellphone 和 img_base64
    #saved_cellphone = "13800000000"
    #img_base64 = "这里是转码后的base64字符串"

  #  result = get_code(saved_cellphone, img_base64)

    #if result:
   #     print("最终结果:", result)
    #else:
       # print("识别失败")

def is_port_in_use(port):
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except OSError:
            return True

def start_server(port):
    """启动服务器的通用函数"""
    try:
        # 更新配置文件中的端口
        config = load_config()
        config['global']['server'] = f":{port}"
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        # 在新线程中启动浏览器
        def open_browser():
            global browser_opened
            if not browser_opened:  # 只在浏览器未打开时执行
                time.sleep(1.5)  # 等待服务器启动
                url = f"http://localhost:{port}"
                webbrowser.open(url)
                browser_opened = True  # 标记浏览器已打开
        
        threading.Thread(target=open_browser, daemon=True).start()
        print(f"服务器正在启动，端口: {port}")
        socketio.run(app, debug=False, host='127.0.0.1', port=port)
    except Exception as e:
        print(f"启动服务器时发生错误: {str(e)}")
        print("请尝试使用其他端口或检查是否有其他程序占用了该端口")
        input("按回车键退出...")

# 使用验证码继续操作
if __name__ == '__main__':
    # 检查是否有命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--default':
        # 使用默认端口启动
        port = 10086
        if is_port_in_use(port):
            print(f"默认端口 {port} 已被占用，请使用 'python app.py' 启动并手动选择端口")
            input("按回车键退出...")
            sys.exit(1)
        start_server(port)
    else:
        # 交互式输入端口
        while True:
            try:
                port_input = input("请输入服务器端口号（直接回车使用默认端口10086）: ").strip()
                if not port_input:  # 如果直接回车，使用默认端口
                    port = 10086
                else:
                    port = int(port_input)
                    if not (1 <= port <= 65535):
                        print("端口号必须在1-65535之间，请重新输入")
                        continue
                
                # 检查端口是否被占用
                if is_port_in_use(port):
                    print(f"端口 {port} 已被占用，请选择其他端口")
                    continue
                    
                break
            except ValueError:
                print("请输入有效的端口号（数字）")
            except Exception as e:
                print(f"发生错误: {str(e)}")
                print("请重新输入端口号")
        
        start_server(port)
