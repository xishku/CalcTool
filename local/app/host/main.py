import datetime

from flask import Flask, Response
from fibonacci import Fibonacci

app = Flask(__name__)

count = 0

@app.route('/')
def hello_world():
    global count
    count += 1
    return f'Hello, World! {datetime.datetime.now()} 访问{count}次'

@app.route('/fibonacci/<int:num>')
def fibonacci(num):
    if num > 1000 or num < 0:
        return f'仅支持[0, 1000]范围的fibonacci数列'

    fib_result = ""
    for i, n in enumerate(Fibonacci.fibonacci(num)):
        fib_result += (f"第{i}个：{n}<br>")

    return f'fibonacci:<p>{fib_result}'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
