import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer


# 自定义请求处理类
class HelloWorldHandler(BaseHTTPRequestHandler):
    # 处理 GET 请求
    def do_GET(self):
        # 设置响应状态码
        self.send_response(200)
        # 设置响应头
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        # 写入响应内容（注意要转成 bytes）
        now_str = f"Hello, World! {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}"
        self.wfile.write(bytes(now_str, encoding = "utf8"))

# 启动服务器
if __name__ == '__main__':
    server_address = ('', 8080)  # 监听所有接口的8080端口
    httpd = HTTPServer(server_address, HelloWorldHandler)
    print('Server running on http://localhost:8080 ...')
    httpd.serve_forever()