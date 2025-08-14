import time
import pandas as pd
import tempfile
import shutil
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def scrape_chinatelecom():
    """
    Scrapes procurement data from caigou.chinatelecom.com.cn
    with specific filters for province (Tianjin) and time (last 2 days).
    """
    user_data_dir = tempfile.mkdtemp()

    # Initialize WebDriver
    options = webdriver.ChromeOptions()
    options.page_load_strategy = 'eager'
    # options.add_argument("--headless") # Disabled for visible debugging
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-pipe")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-data-dir={user_data_dir}")

    service = ChromeService(ChromeDriverManager().install(), service_args=['--disable-ipv6'], log_output='chrome.log')
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Open the URL
        driver.get("https://caigou.chinatelecom.com.cn/search")

        # --- Step 1: Select Province ---
        wait = WebDriverWait(driver, 20)

        # Click on the province "Select" button
        province_select_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='请输入省份']/ancestor::div[contains(@class, 'el-input-group')]//button")))
        driver.execute_script("arguments[0].click();", province_select_button)

        # Wait for the dialog and select "Tianjin"
        tianjin_option_xpath = "//div[@aria-label='选择省份']//span[normalize-space()='天津']"
        tianjin_option = wait.until(EC.element_to_be_clickable((By.XPATH, tianjin_option_xpath)))
        driver.execute_script("arguments[0].click();", tianjin_option)

        # A short wait for the filter to apply and content to refresh
        time.sleep(3)

        # --- Step 2: Scrape Data from the first page ---
        all_data = []

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "tableList")))

        rows = driver.find_elements(By.XPATH, "//div[contains(@class, 'el-table__body-wrapper')]//tr[@class='el-table__row']")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            # The province filter on the site is slow and unreliable.
            # We will grab all data from the first page and filter it locally.
            if len(cols) == 4:
                all_data.append({
                    "title": cols[0].text,
                    "sale_start_time": cols[1].text,
                    "sale_end_time": cols[2].text,
                    "release_date": cols[3].text
                })

        # --- Step 3: Filter and Save Data ---
        df = pd.DataFrame(all_data, columns=["title", "sale_start_time", "sale_end_time", "release_date"])

        if not df.empty:
            # Filter by province
            df = df[df['title'].str.contains('【天津】', na=False)]

            # Filter by date
            df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
            df.dropna(subset=['release_date'], inplace=True)

            now_cst = datetime.now(ZoneInfo("Asia/Shanghai"))
            one_day_ago = now_cst - timedelta(days=1)

            df = df[df['release_date'].dt.date >= one_day_ago.date()]
            df['release_date'] = df['release_date'].dt.strftime('%Y-%m-%d')

        df.to_csv("chinatelecom_tianjin_2days.csv", index=False, encoding='utf-8-sig')
        print(f"Scraped and filtered {len(df)} records, saved to chinatelecom_tianjin_2days.csv")

    finally:
        # Close the browser
        driver.quit()
        # Clean up the temporary directory
        shutil.rmtree(user_data_dir)

if __name__ == "__main__":
    scrape_chinatelecom()
