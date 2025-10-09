


from selenium import webdriver
from selenium.webdriver.common.by import By
import requests
import os
import time

# 设置下载目录
download_dir = "e:\\dev\\qqgroup"
if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# 启动浏览器
driver = webdriver.Chrome()  # 或者使用其他浏览器驱动

# 访问QQ空间登录页面（或其他页面以设置Cookie）
driver.get("https://qzone.qq.com")

# 手动登录后，获取Cookie并添加到Selenium中
# 例如，假设你获取的Cookie如下：
cookies = [
    {
        "name": "your_cookie_name_1",
        "value": "your_cookie_value_1",
        "domain": ".qq.com"
    },
    {
        "name": "your_cookie_name_2",
        "value": "your_cookie_value_2",
        "domain": ".qq.com"
    },
    # 添加更多Cookie
]

# 添加Cookie到浏览器
for cookie in cookies:
    driver.add_cookie(cookie)

# 访问相册页面
driver.get("https://h5.qzone.qq.com/groupphoto/index?inqq=1&groupId=955864889")

# 等待页面加载
time.sleep(10)  # 根据需要调整等待时间

# 获取照片的URL
photos = driver.find_elements(By.TAG_NAME, "img")
photo_urls = [photo.get_attribute("src") for photo in photos]

# 下载照片
for i, url in enumerate(photo_urls):
    if url:  # 确保URL不为空
        response = requests.get(url)
        if response.status_code == 200:
            with open(os.path.join(download_dir, f"photo_{i}.jpg"), "wb") as f:
                f.write(response.content)
                print(f"Downloaded photo_{i}.jpg")

# 关闭浏览器
driver.quit()