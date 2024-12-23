import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import sys
import random
import re

def terminate_chrome_instances():
    try:
        # Check if any Chrome processes are running
        chrome_check = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], capture_output=True, text=True)
        if 'chrome.exe' in chrome_check.stdout:
            print("Terminating existing Chrome instances...")
            # Terminate all Chrome processes
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], check=True)
            print("All Chrome instances terminated.")
        else:
            print("No existing Chrome instances found.")
    except subprocess.CalledProcessError as e:
        print(f"Error while terminating Chrome instances: {e}")
    except Exception as e:
        print(f"Unexpected error while handling Chrome instances: {e}")

def launch_chrome():
    terminate_chrome_instances()
    chrome_cmd = r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug-profile"'
    try:
        subprocess.Popen(chrome_cmd, shell=True)
        print("Launching Chrome with remote debugging...")
        time.sleep(5)  # Wait for Chrome to start
    except Exception as e:
        print(f"Error launching Chrome: {e}")
        sys.exit(1)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        return driver
    except WebDriverException:
        print("Error: Unable to connect to Chrome. Please make sure Chrome is running with remote debugging enabled.")
        print("The script attempted to start Chrome automatically. If it failed, please run the following command manually:")
        print(r'"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-debug-profile"')
        print("Then navigate to https://chat.openai.com/ and log in if necessary.")
        print("After that, run this script again.")
        sys.exit(1)

def navigate_to_chatgpt(driver):
    if driver.current_url != 'https://chat.openai.com/':
        driver.get('https://chat.openai.com/')
        print("Navigated to ChatGPT website.")
    else:
        print("Already on ChatGPT website.")

def find_input_box(driver):
    try:
        input_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "prompt-textarea"))
        )
        return input_box
    except:
        print("Could not find input box")
        return None

def find_send_button(driver):
    try:
        send_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-testid='send-button']"))
        )
        return send_button
    except:
        print("Could not find send button")
        return None

def send_message(driver, message):
    try:
        print("Attempting to locate input box...")
        input_box = find_input_box(driver)
        if input_box is None:
            raise Exception("Could not find input box")
        print("Input box found.")
        
        print("Attempting to focus input box...")
        driver.execute_script("arguments[0].focus();", input_box)
        print("Input box focused.")
        
        print("Typing message...")
        ActionChains(driver).send_keys(message).perform()
        print("Message typed.")
        
        print("Locating send button...")
        send_button = find_send_button(driver)
        if send_button is None:
            raise Exception("Could not find send button")
        print("Send button found.")
        
        print("Clicking send button...")
        send_button.click()
        print("Send button clicked.")
        
        print(f"Message sent: {message}")
    except Exception as e:
        print(f"Error sending message: {e}")
        print("Trying alternative method...")
        try:
            print("Using JavaScript to input message and click send button...")
            js_code = f"document.getElementById('prompt-textarea').value = '{message}';"
            driver.execute_script(js_code)
            driver.execute_script("document.getElementById('prompt-textarea').dispatchEvent(new Event('input', { bubbles: true }));")
            driver.execute_script("document.querySelector('button[data-testid=\"send-button\"]').click();")
            print(f"Message sent using JavaScript: {message}")
        except Exception as js_error:
            print(f"Error sending message using JavaScript: {js_error}")

def count_responses(driver):
    return len(driver.find_elements(By.XPATH, "//div[contains(@class, 'markdown')]"))

def wait_for_response(driver, initial_count):
    try:
        print("Waiting for ChatGPT response...")
        WebDriverWait(driver, 120).until(
            lambda d: count_responses(d) > initial_count
        )
        
        # Wait for the response to finish generating
        WebDriverWait(driver, 120).until_not(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'result-streaming')]"))
        )
        
        print("Response received and fully generated.")
        return True
    except TimeoutException:
        print("Timeout waiting for ChatGPT response.")
        return False

def clean_and_format_text(text):
    # Remove duplicate lines
    lines = text.split('\n')
    unique_lines = []
    for line in lines:
        if line not in unique_lines:
            unique_lines.append(line)
    
    # Join unique lines
    cleaned_text = '\n'.join(unique_lines)
    
    # Remove excessive newlines
    cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
    
    # Ensure proper spacing after punctuation
    cleaned_text = re.sub(r'([.!?])([^\s])', r'\1 \2', cleaned_text)
    
    return cleaned_text.strip()

def get_latest_response(driver):
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Get all response elements
            response_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'markdown')]")
            
            if response_elements:
                # Get the last (most recent) response element
                latest_response = response_elements[-1]
                
                # Get all child elements of the response
                response_parts = latest_response.find_elements(By.XPATH, ".//*")
                
                # Combine the text from all parts
                full_response = "\n".join([part.text for part in response_parts if part.text.strip()])
                
                if full_response.strip():
                    return clean_and_format_text(full_response)
                else:
                    print(f"Response is empty. Retrying... (Attempt {attempt + 1}/{max_retries})")
            else:
                print(f"No response elements found. Retrying... (Attempt {attempt + 1}/{max_retries})")
        
        except StaleElementReferenceException:
            print(f"Stale element reference. Retrying... (Attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"Error getting latest response: {e}. Retrying... (Attempt {attempt + 1}/{max_retries})")
        
        # Wait before the next retry
        time.sleep(retry_delay)
    
    print("Failed to get the latest response after multiple attempts.")
    return None

def capture_conversation(driver):
    try:
        conversation_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'text-base')]")
        conversation = []
        for element in conversation_elements:
            role = "User" if "bg-gray-50" in element.get_attribute("class") else "ChatGPT"
            text = clean_and_format_text(element.text.strip())
            if text:
                conversation.append(f"{role}:\n{text}")
        return "\n\n".join(conversation)
    except Exception as e:
        print(f"Error capturing conversation: {e}")
        return None

def main():
    launch_chrome()
    driver = setup_driver()
    navigate_to_chatgpt(driver)

    print("ChatGPT page is ready. You can now interact with it.")
    print("Type your message to send to ChatGPT, 'capture' to save the current conversation, or 'exit' to quit.")

    while True:
        user_input = input("Enter your message or command: ")
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'capture':
            conversation = capture_conversation(driver)
            if conversation:
                filename = f"chatgpt_conversation_{int(time.time())}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(conversation)
                print(f"Conversation saved to {filename}")
            else:
                print("Failed to capture conversation.")
        else:
            initial_response_count = count_responses(driver)
            send_message(driver, user_input)
            if wait_for_response(driver, initial_response_count):
                response = get_latest_response(driver)
                if response:
                    print("ChatGPT response:")
                    print(response)
                else:
                    print("Failed to get a response from ChatGPT.")
            else:
                print("Failed to get a response from ChatGPT.")

    print("Script execution complete. You can continue using the browser.")
    driver.quit()

if __name__ == "__main__":
    main()
