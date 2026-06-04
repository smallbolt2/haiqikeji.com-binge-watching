from pathlib import Path
p = Path(r'd:\本科\刷网课\haiqikeji.com网站专用刷课\haiqikeji.com-binge-watching\mooc\user.py')
text = p.read_text(encoding='utf-8')
start_marker = '# 2. 进入心跳循环'
end_marker = '# 视频结束时提交学习完成记录'
start = text.find(start_marker)
end = text.find(end_marker, start)
if start == -1 or end == -1:
    raise SystemExit(f'marker not found: start={start}, end={end}')
new = '''# 2. 心跳逻辑暂时注释掉，改为会话开启后直接提交结束包
            # heartbeat_url = f"{self.base_url}/api/user/study_session_heartbeat"
            # heartbeat_params = {
            #     "schoolId": str(self.school_id),
            #     "userId": str(self.student_id),
            #     "courseId": str(course_id),
            #     "nodeId": str(node_id),
            #     "sessionId": session_id
            # }
            #
            # heartbeat_count = 0
            # while self.running:
            #     # 严格等待 12 秒
            #     time.sleep(12)
            #     # 【核心】：我们自己本地累加 12 秒的学习时间
            #     elapsed_seconds += 12
            #
            #     # 发送心跳包
            #     hb_response = self.session.get(heartbeat_url, params=heartbeat_params, headers=common_headers)
            #
            #     if hb_response.status_code != 200 or hb_response.json().get('code') == 500:
            #         headers_json = common_headers.copy()
            #         headers_json['Content-Type'] = 'application/json'
            #         hb_response = self.session.post(heartbeat_url, json=heartbeat_params, headers=headers_json)
            #
            #     try:
            #         hb_data = hb_response.json()
            #     except Exception:
            #         time.sleep(5)
            #         continue
            #
            #     if hb_data.get('code') == 200:
            #         pass # 心跳成功不再每 12 秒频繁刷屏
            #     elif hb_data.get('code') == 500 and "频繁" in str(hb_data.get('data', '')):
            #         self.logger.warning(f"[{node_name}] 心跳被限流，延长等待时间...")
            #         time.sleep(5)
            #
            #     # 每成功发送 3 次心跳 (约 36-40 秒)，打印一次本地计算的进度
            #     heartbeat_count += 1
            #     if heartbeat_count % 3 == 0:
            #         percent = min(100, int((elapsed_seconds / total_required_seconds) * 100))
            #         self.logger.info(f"[{node_name}] 本地模拟学习进度: {percent}% ({elapsed_seconds}/{total_required_seconds}秒)")
            #
            #         # 【核心防护】：如果本地看的时间已经达到了视频总时长（加15秒缓冲确保服务器记满），直接强行结束本视频！
            #         if elapsed_seconds >= total_required_seconds + 15:
            #             self.logger.info(f"[{node_name}] 🏆 视频学习时长已满，自动切换下一个章节！")
            #             break
'''
new_text = text[:start] + new + text[end:]
p.write_text(new_text, encoding='utf-8')
print('updated')
