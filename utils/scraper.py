import random
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from logger import get_logger
import os

logger = get_logger(__name__, debug=os.getenv("DEBUG", "False") == "True")


def handle_captcha(driver: webdriver.Chrome):
    """If a captcha is detected, try clicking submit buttons."""
    try:
        submits = driver.find_elements(By.XPATH, "//input[@type='submit']")
        for submit in submits:
            logger.info("Clicking captcha submit button")
            submit.click()
            sleep(random.uniform(2, 4))
    except Exception as e:
        logger.error(f"[x] Scraper - Error handling captcha: {e}")
