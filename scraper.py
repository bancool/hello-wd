import time
import pandas as pd
import tempfile
import shutil
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

def scrape_chinatelecom():
    """
    Scrapes procurement data from caigou.chinatelecom.com.cn
    with specific filters for province (Tianjin) and time (last 2 days)
    by interacting with the page's UI elements as requested.
    """
    user_data_dir = tempfile.mkdtemp()

    options = webdriver.ChromeOptions()
    options.page_load_strategy = 'eager'
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-pipe")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir={user_data_dir}")

    service = ChromeService(ChromeDriverManager().install(), service_args=['--disable-ipv6'], log_output='chrome.log')
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get("https://caigou.chinatelecom.com.cn/search")
        wait = WebDriverWait(driver, 20)

        # --- Step 1: Select Province ---
        province_select_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='请输入省份']/ancestor::div[contains(@class, 'el-input-group')]//button")))
        driver.execute_script("arguments[0].click();", province_select_button)

        tianjin_option_xpath = "//div[@aria-label='选择省份']//span[normalize-space()='天津']"
        tianjin_option = wait.until(EC.element_to_be_clickable((By.XPATH, tianjin_option_xpath)))
        driver.execute_script("arguments[0].click();", tianjin_option)
        time.sleep(1)

        # --- Step 2: Enter Date Range ---
        now_cst = datetime.now(ZoneInfo("Asia/Shanghai"))
        one_day_ago = now_cst - timedelta(days=1)
        start_date_str = one_day_ago.strftime('%Y-%m-%d')
        end_date_str = now_cst.strftime('%Y-%m-%d')

        start_date_input = wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='发布起始时间']")))
        end_date_input = driver.find_element(By.XPATH, "//input[@placeholder='发布截止时间']")

        start_date_input.send_keys(start_date_str)
        end_date_input.send_keys(end_date_str)

        # Send ESCAPE key to close the date picker
        end_date_input.send_keys(Keys.ESCAPE)
        time.sleep(1)

        # --- Step 3: Click Query and Wait ---
        try:
            first_row_before_filter = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'el-table__body-wrapper')]//tr[@class='el-table__row'][1]")))
        except:
            first_row_before_filter = None

        query_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button/span[contains(text(), '查询')]")))
        driver.execute_script("arguments[0].click();", query_button)

        if first_row_before_filter:
            try:
                wait.until(EC.staleness_of(first_row_before_filter))
            except:
                time.sleep(3)
        else:
             time.sleep(3)

        # --- Step 4: Scrape All Pages of Filtered Results ---
        all_data = []
        while True:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "tableList")))
            rows = driver.find_elements(By.XPATH, "//div[contains(@class, 'el-table__body-wrapper')]//tr[@class='el-table__row']")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) == 4:
                    all_data.append({
                        "title": cols[0].text,
                        "sale_start_time": cols[1].text,
                        "sale_end_time": cols[2].text,
                        "release_date": cols[3].text
                    })

            try:
                first_row_on_page = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'el-table__body-wrapper')]//tr[@class='el-table__row'][1]")))
                next_button = driver.find_element(By.XPATH, "//button[contains(@class, 'btn-next')]")
                if not next_button.is_enabled():
                    break
                driver.execute_script("arguments[0].click();", next_button)
                wait.until(EC.staleness_of(first_row_on_page))
            except Exception:
                break

        # --- Step 5: Save Data ---
        df = pd.DataFrame(all_data, columns=["title", "sale_start_time", "sale_end_time", "release_date"])
        df.to_csv("chinatelecom_tianjin_2days.csv", index=False, encoding='utf-8-sig')
        print(f"Scraped {len(df)} records, saved to chinatelecom_tianjin_2days.csv")

    finally:
        driver.quit()
        shutil.rmtree(user_data_dir)

if __name__ == "__main__":
    scrape_chinatelecom()
