import os
import time
import pickle
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# URL配置
damai_url = 'https://www.damai.cn/'
login_url = 'https://passport.damai.cn/login?ru=https%3A%2F%2Fwww.damai.cn%2F'
target_url = 'https://detail.damai.cn/item.htm?spm=a2oeg.search_category.0.0.47974d15ngpFMm&id=998575574191&clicktitle=%E9%83%AD%E5%AF%8C%E5%9F%8EICONIC%E4%B8%96%E7%95%8C%E5%B7%A1%E5%9B%9E%E6%BC%94%E5%94%B1%E4%BC%9A2026-%E8%A5%BF%E5%AE%89%E7%AB%99'


class Concert:
    def __init__(self):
        self.status = 0
        self.login_method = 1
        self.click_count = 0
        self.last_url = ""

        options = Options()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, 15)

    def set_cookies(self):
        self.driver.get(damai_url)
        print('###请手动点击登录并扫码###')
        while '大麦网-全球演出赛事官方购票平台' in self.driver.title:
            sleep(1)
        print('###扫码登录成功###')
        pickle.dump(self.driver.get_cookies(), open('cookies.pkl', 'wb'))
        print('###Cookie已保存###')
        self.driver.get(target_url)

    def get_cookie(self):
        cookies = pickle.load(open('cookies.pkl', 'rb'))
        for cookie in cookies:
            self.driver.add_cookie({
                'domain': '.damai.cn',
                'name': cookie.get('name'),
                'value': cookie.get('value')
            })
        print('###已载入Cookie###')

    def login(self):
        if self.login_method == 0:
            self.driver.get(login_url)
        else:
            if not os.path.exists('cookies.pkl'):
                self.set_cookies()
            else:
                self.driver.get(target_url)
                self.get_cookie()
                self.driver.refresh()

    def enter_concert(self):
        print('###打开浏览器，进入大麦网###')
        self.login()
        self.driver.refresh()
        self.status = 2
        print('###登录成功###')

        try:
            self.wait.until(EC.element_to_be_clickable(
                (By.XPATH,
                 "//*[contains(@class,'close') or contains(text(),'关闭') or contains(@class,'cancel')]"))).click()
        except:
            pass

    def choose_ticket(self):
        if self.status != 2:
            return

        print('=' * 60)
        print('###开始监控 - 优先选票档 → 寻找“不，立即预订”按钮###')

        max_attempts = 500

        for attempt in range(1, max_attempts + 1):
            print(f"\n第 {attempt} 次尝试...")

            try:
                self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                current_url = self.driver.current_url

                # 1.优先尝试点击票档
                self._try_select_ticket_tier()

                # 2.重点寻找“不，立即预订”或“立即预订”
                if self._try_click_no_buy_now():
                    print("已尝试点击 '不，立即预订' / '立即预订'，等待3-5秒观察...")
                    sleep(4)

                    new_url = self.driver.current_url
                    new_title = self.driver.title

                    if any(k in new_title.lower() for k in ["订单", "confirm", "payment", "结算", "购票"]):
                        print("!!! 检测到订单/支付页面跳转成功 !!!")
                        self.check_order()
                        return

                    if new_url != current_url and "item" not in new_url:
                        print("页面发生变化，可能进入预订流程...")
                        sleep(6)
                        continue

                    self.click_count += 1
                    if self.click_count >= 4:
                        print("连续点击未进展，休息30秒再试...")
                        sleep(30)
                        self.click_count = 0
                    continue

                print("本轮未找到目标按钮，刷新页面...")
                self.driver.refresh()
                sleep(5)

            except Exception as e:
                print(f"异常: {str(e)}")
                try:
                    self.driver.save_screenshot(f"debug_attempt_{attempt}.png")
                    print(f"已保存截图: debug_attempt_{attempt}.png")
                except:
                    pass
                sleep(6)

        print("达到最大尝试次数，脚本结束。")

    def _try_select_ticket_tier(self):
        # 触发购买流程
        tier_selectors = [
            '.sku-item', '.ticket-item', '.price-item', '[class*="sku"]', '[class*="ticket"]', '[class*="price"]',
            '.perform__order__price .item', '.ticket-list li'
        ]

        for sel in tier_selectors:
            try:
                items = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if items:
                    print(f"找到 {len(items)} 个票档，尝试点击第一个...")
                    for item in items:
                        if item.is_displayed() and "缺货登记" not in item.text:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", item)
                            sleep(0.5)
                            self.driver.execute_script("arguments[0].click();", item)
                            sleep(1.2)
                            return True
            except:
                continue
        print("未找到可点击票档（可能全缺货）")

    def _try_click_no_buy_now(self):

        keywords = ["不，立即预订", "立即预订", "立即购买", "预订", "购票"]

        xpaths = [
            '//button[contains(text(), "不，立即预订") or contains(text(), "立即预订") or contains(text(), "立即购买")]',
            '//span[contains(text(), "不，立即预订") or contains(text(), "立即预订")]',
            '//div[contains(text(), "不，立即预订") or contains(text(), "立即预订")]',
            '//*[contains(@class, "buy") or contains(@class, "order") or contains(@class, "preOrder") or contains(@class, "btn-fixed")][contains(text(), "预订") or contains(text(), "购买")]'
        ]

        for xp in xpaths:
            try:
                elements = self.driver.find_elements(By.XPATH, xp)
                for el in elements:
                    text = (el.text or "").strip()
                    if any(kw in text for kw in keywords) and el.is_displayed() and el.is_enabled():
                        print(f"!!! 找到目标按钮！文字：{text} !!!")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                        sleep(0.6)
                        self.driver.execute_script("arguments[0].click();", el)
                        return True
            except:
                continue

        print("未找到 '不，立即预订' 或 '立即预订' 按钮")
        return False

    def check_order(self):
        print('###进入订单/确认页面，开始选人+提交###')
        sleep(2)

        try:
            viewers = [1, 1]  # 修改观演人序号
            for idx in viewers:
                xpath = f'//*[@id="container"]/div/div[2]/div[2]/div[{idx}]/div/label'
                try:
                    self.driver.find_element(By.XPATH, xpath).click()
                    print(f"已勾选第 {idx} 个观演人")
                    sleep(0.4)
                except:
                    pass

            submit_xpaths = [
                '//*[@id="container"]/div/div[9]/button',
                '//button[contains(text(), "提交订单") or contains(text(), "确认") or contains(text(), "支付")]',
                '//button[contains(@class, "submit") or contains(@class, "confirm")]'
            ]

            for xp in submit_xpaths:
                try:
                    btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                    btn.click()
                    print("###已点击提交/确认按钮！请尽快支付###")
                    return
                except:
                    continue

            print("未找到提交按钮，请手动完成")
        except Exception as e:
            print("订单页异常:", str(e))

    def finish(self):
        try:
            self.driver.quit()
        except:
            pass
        print("浏览器已关闭")


if __name__ == '__main__':
    con = Concert()
    try:
        con.enter_concert()
        con.choose_ticket()
    except Exception as e:
        print("程序异常:", e)
    finally:
        con.finish()