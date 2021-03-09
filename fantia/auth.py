from selenium import webdriver
import time

def get_cookies(username, password):
    wd = webdriver.Chrome()
    wd.get("https://fantia.jp/sessions/signin")
    wd.find_element_by_xpath("//input[@id='user_email']").send_keys(username)
    wd.find_element_by_xpath("//input[@id='user_password']").send_keys(password)
    wd.find_element_by_xpath("//button[@type='submit']").click()
    time.sleep(5)
    wd.get_cookies()