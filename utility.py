from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class utility:
    def __init__(self, driver, timeout=10):
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def wait_for_element(self, locator, condition=EC.presence_of_element_located):
        return self.wait.until(condition(locator))

    def click(self, locator):
        """Wait until element is clickable and then click"""
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.click()

    def enter_text(self, locator, text, clear_first=True):
        """Wait until element is visible and enter text"""
        element = self.wait.until(EC.visibility_of_element_located(locator))
        if clear_first:
            element.clear()
        element.send_keys(text)

    def scroll_into_element(self, locator):
        """Scroll until element is in view"""
        element = self.wait.until(EC.presence_of_element_located(locator))
        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)

    def scroll_to_top(self):
        """Scroll to top of page"""
        self.driver.execute_script("window.scrollTo(0, 0);")

    def scroll_to_middle(self):
        """Scroll to middle of page"""
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")

    def mouse_over(self, locator):
        """Hover mouse over element"""
        element = self.wait.until(EC.visibility_of_element_located(locator))
        ActionChains(self.driver).move_to_element(element).perform()
