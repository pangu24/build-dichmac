import sys
import os
import shutil
import time
import re
import random
import math
import pyperclip
import hashlib
import base64
import subprocess
import platform
from datetime import datetime, date, time as dt_time
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
QFrame, QLabel, QPushButton, QComboBox, QLineEdit, QTextEdit,
QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
QMessageBox, QProgressBar, QGroupBox, QSplitter, QSpinBox,
QAbstractSpinBox, QDialog, QListWidget, QDialogButtonBox)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QWaitCondition, QMutex
from PySide6.QtGui import QFont
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

MODEL_CONFIG=[
("Gemini Flash 3",200,"nhanh"),
("Gemini Thinking 3",400,"tưduy"),
("Gemini Pro 3",500,"pro")
]
MODEL_DISPLAY=[i[0] for i in MODEL_CONFIG]
MODEL_CHUNK_SIZE={i[0]:i[1] for i in MODEL_CONFIG}
MODEL_SELECTOR={i[0]:i[2] for i in MODEL_CONFIG}

def get_appdata_dir():
 if platform.system()=="Darwin":
  return os.path.expanduser("~/Library/Application Support")
 return os.environ.get("APPDATA","")

def get_chrome_major_version():
 if platform.system()=="Darwin":
  try:
   out=subprocess.check_output(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','--version'],text=True)
   m=re.search(r"Chrome\s+(\d+)\.",out)
   if m:return int(m.group(1))
  except:pass
 elif platform.system()=="Windows":
  try:
   import winreg
   reg_paths=[r"SOFTWARE\Google\Chrome\BLBeacon",r"SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon"]
   for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
    for path in reg_paths:
     try:
      key=winreg.OpenKey(hive,path)
      version,_=winreg.QueryValueEx(key,"version")
      if version:
       try:return int(version.split(".")[0])
       except:pass
     except:continue
  except:pass
  possible_paths=[
  os.path.join(os.environ.get("PROGRAMFILES",r"C:\Program Files"),"Google","Chrome","Application","chrome.exe"),
  os.path.join(os.environ.get("PROGRAMFILES(X86)",r"C:\Program Files (x86)"),"Google","Chrome","Application","chrome.exe"),
  ]
  for p in possible_paths:
   if os.path.exists(p):
    try:
     cmd=f'powershell -NoProfile -Command "(Get-Item \\"{p}\\").VersionInfo.ProductVersion"'
     out=subprocess.check_output(cmd,shell=True,stderr=subprocess.DEVNULL,text=True).strip()
     if out:
      try:return int(out.split(".")[0])
      except:pass
    except:pass
 raise RuntimeError("Không xác định được phiên bản Chrome.")

def get_cached_uc_driver_major():
 exe_name="undetected_chromedriver" if platform.system()=="Darwin" else "undetected_chromedriver.exe"
 exe_path=os.path.join(get_appdata_dir(),"undetected_chromedriver",exe_name)
 if not os.path.exists(exe_path):return None
 try:
  out=subprocess.check_output([exe_path,"--version"],stderr=subprocess.STDOUT,text=True)
  m=re.search(r"ChromeDriver\s+(\d+)\.",out)
  if m:return int(m.group(1))
 except:pass
 return None

def ensure_uc_driver_matches_chrome():
 chrome_major=get_chrome_major_version()
 driver_major=get_cached_uc_driver_major()
 if driver_major is not None and driver_major!=chrome_major:
  cache_dir=os.path.join(get_appdata_dir(),"undetected_chromedriver")
  shutil.rmtree(cache_dir,ignore_errors=True)
 return chrome_major

class LicenseManager:
 def __init__(self):
  hex_key="42ab258cda380b5d0c58131f999c3436dceaec01c9889c502f850f1ca515e650"
  hex_iv="a1b2c3d4e5f67890a1b2c3d4e5f67890"
  self.key=bytes.fromhex(hex_key)
  self.iv=bytes.fromhex(hex_iv)
 def get_machine_id(self):
  try:
   if platform.system()=="Darwin":
    out=subprocess.check_output(["ioreg","-rd1","-c","IOPlatformExpertDevice"],text=True)
    m=re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"',out)
    machine_guid=m.group(1) if m else "MAC_UUID"
    cpu_id=platform.processor()
    combined=f"{machine_guid}_{cpu_id}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
   else:
    import winreg
    reg=winreg.ConnectRegistry(None,winreg.HKEY_LOCAL_MACHINE)
    key=winreg.OpenKey(reg,r"SOFTWARE\Microsoft\Cryptography")
    machine_guid=winreg.QueryValueEx(key,"MachineGuid")[0]
    cpu_key=winreg.OpenKey(reg,r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
    cpu_id=winreg.QueryValueEx(cpu_key,"ProcessorNameString")[0]
    combined=f"{machine_guid or ''}_{cpu_id or ''}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16].upper()
  except Exception:
   return "UNKNOWN_ID"
 def check_license(self,parent_window=None):
  infile=os.path.join(os.getcwd(),"license.key")
  try:
   if not os.path.exists(infile) or os.path.getsize(infile)==0:
    return False,None,"Thiếu file license.key"
   with open(infile,"rb") as f:
    raw_data=f.read().strip()
   try:
    decoded=base64.b64decode(raw_data,validate=True)
   except Exception:
    return False,None,"File Key lỗi định dạng (Base64)"
   try:
    cipher=Cipher(algorithms.AES(self.key),modes.CBC(self.iv),backend=default_backend())
    decryptor=cipher.decryptor()
    decrypted_padded=decryptor.update(decoded)+decryptor.finalize()
    unpadder=padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted=unpadder.update(decrypted_padded)+unpadder.finalize()
    decrypted_str=decrypted.decode("utf-8")
   except ValueError:
    return False,None,"Key không khớp (Sai mã hóa)"
   except Exception as e:
    return False,None,f"Lỗi giải mã: {str(e)}"
   if ";" not in decrypted_str:
    return False,None,"Dữ liệu Key sai cấu trúc"
   parts=decrypted_str.split(";",1)
   if len(parts)!=2:
    return False,None,"Dữ liệu Key sai cấu trúc"
   machine_id,expiry_str=parts
   current_id=self.get_machine_id()
   if machine_id.strip().upper()!=current_id.strip().upper():
    return False,None,"Key này không dành cho máy này"
   try:
    expiry_date=datetime.strptime(expiry_str.strip(),"%Y-%m-%d").date()
   except ValueError:
    return False,None,"Định dạng ngày không hợp lệ"
   today=date.today()
   if today>expiry_date:
    return False,None,"License đã hết hạn"
   expiry_full=datetime.combine(expiry_date,dt_time(23,59,59))
   seconds_left=(expiry_full-datetime.now()).total_seconds()
   return True,{'seconds_remaining':max(0,int(seconds_left))},"Bản quyền hợp lệ"
  except Exception as e:
   return False,None,f"Lỗi hệ thống: {str(e)}"

class TabContext:
 def __init__(self,handle,chunk_list):
  self.handle=handle
  self.queue=chunk_list
  self.current_chunk=None
  self.status="IDLE"
  self.usage_count=0
  self.retry_count=0
  self.start_time=0

class TranslateThread(QThread):
 started=Signal()
 chunk_sent=Signal(int,int)
 finished=Signal()
 log_signal=Signal(str)
 paused_signal=Signal(bool)
 def __init__(self,parent):
  super().__init__(parent)
  self.parent=parent
  self.stopped=False
  self.is_paused=False
  self.total_rows=0
  self.processed_rows=0
  self.mutex=QMutex()
  self.wait_condition=QWaitCondition()
 def stop(self):
  self.stopped=True
  self.resume()
 def pause(self):
  self.is_paused=True
  self.paused_signal.emit(True)
  self.log("⏸️ Đã tạm dừng...")
 def resume(self):
  if self.is_paused:
   self.is_paused=False
   self.paused_signal.emit(False)
   self.wait_condition.wakeAll()
   self.log("▶️ Tiếp tục...")
 def check_pause(self,driver=None,current_tab_handle=None):
  self.mutex.lock()
  if self.is_paused:
   if driver and current_tab_handle:
    try:
     self.wait_condition.wait(self.mutex)
     if driver.current_window_handle!=current_tab_handle:
      driver.switch_to.window(current_tab_handle)
      time.sleep(0.5)
    except:pass
   else:
    self.wait_condition.wait(self.mutex)
  self.mutex.unlock()
 def log(self,msg):
  self.log_signal.emit(msg)
 def select_model(self,driver,wait):
  try:
   current_model_name=self.parent.cb_model.currentText()
   if current_model_name=="Gemini Flash 3":return
   model_key=MODEL_SELECTOR.get(current_model_name)
   if not model_key:return
   btn=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button.input-area-switch")))
   btn.click()
   selector=f'[data-test-id="bard-mode-option-{model_key}"]'
   opt=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,selector)))
   opt.click()
   time.sleep(1)
  except:pass
 def has_chinese(self,text):
  return bool(re.search(r'[\u4e00-\u9fff]',text))
 def parse_translations(self,text):
  result={}
  if not text:return result
  pattern=r'#(\d+)\s*([\s\S]*?)(?=\s*#\d+|$)'
  for match in re.finditer(pattern,text):
   try:
    trans_id=int(match.group(1))
    trans_text=match.group(2).strip().rstrip(';').strip()
    result[trans_id]=trans_text
   except:continue
  return result
 def validate_response(self,input_text,output_text,check_chinese=True):
  if not output_text:return False,"không nhận được dữ liệu"
  output_data=self.parse_translations(output_text)
  if not output_data:return False,"AI trả về sai cấu trúc"
  input_ids=[int(m.group(1)) for m in re.finditer(r'#(\d+)\b',input_text)]
  if not input_ids:return False,"Lỗi dữ liệu đầu vào"
  first_id=input_ids[0]
  last_id=input_ids[-1]
  missing=set(input_ids)-set(output_data.keys())
  num_missing=len(missing)
  if num_missing>=2:return False,{"type":"missing","ids":list(missing)}
  if num_missing==1:
   missing_id=list(missing)[0]
   if missing_id==first_id or missing_id==last_id:
    return False,f"Thiếu ID biên (#{missing_id})"
  if check_chinese:
   combined_text="".join(output_data.values())
   if combined_text:
    ratio=len(re.findall(r'[\u4e00-\u9fff]',combined_text))/len(combined_text)
    if ratio>0.4:return False,"tỉ lệ tiếng Trung cao"
  return True,output_data
 def wait_until_done_blocking(self,driver):
  while True:
   if self.stopped:return False
   try:
    self.check_pause(driver,driver.current_window_handle)
    if "google.com/sorry/index" in driver.current_url:
     self.log("⚠️ CẢNH BÁO: Bị chặn Captcha! Đang ép mở cửa sổ Chrome...")
     try:
      driver.switch_to.window(driver.current_window_handle)
      driver.maximize_window()
     except:pass
     while "google.com/sorry/index" in driver.current_url:
      if self.stopped:return False
      time.sleep(2)
     self.log("✅ Đã giải xong Captcha!")
     time.sleep(3)
     return False
    check_error_script="""
    return performance.getEntriesByType("resource").some(r =>
    r.name.includes("BardChatUi/jserror") &&
    (r.name.includes("status%20%3D%200") || r.name.includes("batchexecute"))
    );
    """
    if driver.execute_script(check_error_script):
     driver.execute_script("performance.clearResourceTimings();")
     self.log("🚫 Lỗi API. Đang tải lại trang...")
     driver.refresh()
     time.sleep(5)
     if "google.com/sorry/index" not in driver.current_url:
      self.log("🔄 Thử lại chunk...")
      return False
   except Exception as e:
    if "no such window" in str(e).lower() or "target window already closed" in str(e).lower():
     return False
    pass
   try:
    driver.find_element(By.CSS_SELECTOR,"button.send-button.stop")
    time.sleep(1)
   except:return True
 def extract_response(self,driver):
  script=r"""
  return (() => {
  const hosts = document.querySelectorAll('div.markdown.markdown-main-panel[inline-copy-host]');
  if (!hosts.length) return null;
  const lastHost = hosts[hosts.length - 1];
  return lastHost.innerText || lastHost.textContent;
  })();
  """
  try:return driver.execute_script(script)
  except:return None
 def click_restore_button(self,driver):
  if self.stopped:return False
  try:self.check_pause(driver,driver.current_window_handle)
  except:return False
  try:
   btn=driver.find_element(By.CSS_SELECTOR,'button.mat-mdc-icon-button[aria-label="Khôi phục"]')
   if btn.is_displayed():
    driver.execute_script("arguments[0].click();",btn)
    time.sleep(0.15)
    try:
     retry_btn=driver.find_element(By.CSS_SELECTOR,'button.mat-mdc-menu-item mat-icon[data-mat-icon-name="refresh"]')
     retry_btn=retry_btn.find_element(By.XPATH,"ancestor::button")
     driver.execute_script("arguments[0].click();",retry_btn)
    except Exception as e:
     self.log(f"⚠️ Lỗi nút Thử lại: {str(e)}")
    time.sleep(1)
    return True
  except:pass
  try:
   script_open_menu="""
   const btns = document.querySelectorAll('[data-test-id="more-menu-button"]');
   if (btns.length > 0) {
   btns[btns.length - 1].click();
   return true;
   }
   return false;
   """
   if driver.execute_script(script_open_menu):
    time.sleep(0.8)
    btn_restore=driver.find_element(By.CSS_SELECTOR,'button[aria-label="Khôi phục"]')
    driver.execute_script("arguments[0].click();",btn_restore)
    self.log("✅ Đã Khôi phục qua menu")
    time.sleep(1.5)
    return True
  except Exception as e:
   self.log(f"❌ Không thể Khôi phục: {str(e)}")
  return False
 def send_prompt(self,driver,text,wait):
  try:
   input_editor=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"div.ql-editor")))
   input_editor.click()
   input_editor.send_keys(Keys.CONTROL+"a")
   input_editor.send_keys(Keys.DELETE)
   pyperclip.copy(text)
   input_editor.send_keys(Keys.CONTROL+"v")
   time.sleep(0.5)
   send_btn=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button.send-button.submit")))
   send_btn.click()
   time.sleep(1.5)
   return True
  except:return False
 def run(self):
  self.started.emit()
  rows=self.parent.table.rowCount()
  if rows==0:self.finished.emit();return
  current_model=self.parent.cb_model.currentText()
  batch_text=self.parent.ent_chunk.text().strip()
  batch_size=int(batch_text) if batch_text.isdigit() else 200
  all_chunks=[]
  current=0
  chunk_idx=1
  while current<rows:
   end=min(current+batch_size,rows)
   chunk_content=[]
   for r in range(current,end):
    id_item=self.parent.table.item(r,0)
    orig_item=self.parent.table.item(r,2)
    id_text=id_item.text() if id_item else str(r+1)
    orig_text=orig_item.text().replace("\n"," ") if orig_item else ""
    chunk_content.append(f"#{id_text} {orig_text}")
   all_chunks.append({
   'id':chunk_idx,'text':"; ".join(chunk_content),
   'start_row':current,'end_row':end,'count':end-current
   })
   current=end
   chunk_idx+=1
  self.total_rows=rows
  num_threads=self.parent.spin_threads.value()
  self.retry_items=[]
  MAX_CHUNKS_PER_TAB=5
  wave_size=num_threads*MAX_CHUNKS_PER_TAB
  waves=[]
  for i in range(0,len(all_chunks),wave_size):
   waves.append(all_chunks[i:i+wave_size])
  self.log(f"Model: {current_model} | Batch: {batch_size} | Luồng: {num_threads}")
  profile=self.parent.profile_path
  gem_code=self.parent.cb_gem.currentData() or self.parent.cb_gem.currentText().strip()
  link=f"https://gemini.google.com/gem/{gem_code}" if gem_code else "https://gemini.google.com/"
  options=uc.ChromeOptions()
  options.add_argument(f"--user-data-dir={profile}")
  options.add_argument("--disable-background-timer-throttling")
  options.add_argument("--disable-renderer-backgrounding")
  options.add_argument("--disable-backgrounding-occluded-windows")
  options.add_argument("--disable-features=CalculateNativeWinOcclusion")
  options.add_argument("--disable-features=BackForwardCache")
  options.add_argument("--disable-features=RendererCodeIntegrity")
  options.add_argument("--process-per-site")
  options.add_argument("--disable-site-isolation-trials")
  options.add_argument("--disable-gpu-vsync")
  options.add_argument("--disable-frame-rate-limit")
  driver=None
  try:
   try:
    chrome_major=ensure_uc_driver_matches_chrome()
    driver=uc.Chrome(version_main=chrome_major,options=options,use_subprocess=False)
   except Exception as e:
    self.log(f"[WARN] Chrome version fallback: {e}")
    driver=uc.Chrome(options=options,use_subprocess=False)
   driver.set_window_size(1000,800)
   driver.get(link)
   try:
    js_click_login="""
    return (function(){
    const btn = document.querySelector('a[aria-label="Đăng nhập"]');
    if (btn) { btn.click(); return true; }
    return false;
    })();
    """
    if driver.execute_script(js_click_login):time.sleep(1.5)
   except:pass
   wait=WebDriverWait(driver,30)
   base_handle=driver.current_window_handle
   for w_idx,wave_chunks in enumerate(waves):
    if self.stopped:break
    self.log(f"\n🚀 --- ĐỢT {w_idx+1}/{len(waves)} ---")
    chunk_groups=[[] for _ in range(num_threads)]
    for i,chunk in enumerate(wave_chunks):
     chunk_groups[i%num_threads].append(chunk)
    tabs=[]
    for i in range(num_threads):
     if not chunk_groups[i]:continue
     driver.execute_script("window.open('');")
     handle=driver.window_handles[-1]
     driver.switch_to.window(handle)
     driver.get(link)
     self.select_model(driver,wait)
     tab_ctx=TabContext(handle,chunk_groups[i])
     tabs.append(tab_ctx)
     self.check_pause(driver,handle)
     if tab_ctx.queue:
      tab_ctx.current_chunk=tab_ctx.queue.pop(0)
      tab_ctx.start_time=time.time()
      if self.send_prompt(driver,tab_ctx.current_chunk['text'],wait):
       tab_ctx.status="GENERATING"
    active=True
    while active and not self.stopped:
     all_done=True
     for tab in tabs:
      if self.stopped:break
      try:
       current_handles=driver.window_handles
       if tab.handle not in current_handles:
        driver.switch_to.window(base_handle)
        driver.execute_script("window.open('');")
        time.sleep(1)
        tab.handle=driver.window_handles[-1]
        driver.switch_to.window(tab.handle)
        driver.get(link)
        time.sleep(3)
        self.select_model(driver,wait)
        if tab.current_chunk:
         tab.queue.insert(0,tab.current_chunk)
         tab.current_chunk=None
        tab.status="IDLE"
        continue
       driver.switch_to.window(tab.handle)
      except Exception as e:
       self.log(f"❌ Lỗi chuyển tab: {str(e)}")
       continue
      self.check_pause(driver,tab.handle)
      if not tab.queue and tab.status=="IDLE":continue
      all_done=False
      if tab.status=="GENERATING":
       if self.wait_until_done_blocking(driver):
        response=self.extract_response(driver)
        c_id=tab.current_chunk['id']
        if response=="PAGE_LOADING" or response is None:
         while True:
          if self.stopped:break
          time.sleep(2)
          try:
           if "google.com/sorry/index" in driver.current_url:
            driver.switch_to.window(driver.current_window_handle)
            driver.maximize_window()
            while "google.com/sorry/index" in driver.current_url:
             if self.stopped:break
             time.sleep(2)
            break
           if driver.find_elements(By.CSS_SELECTOR,"div.ql-editor"):break
          except:pass
         if self.send_prompt(driver,tab.current_chunk['text'],wait):
          tab.status="GENERATING"
         else:
          tab.queue.insert(0,tab.current_chunk)
          tab.current_chunk=None
          tab.status="IDLE"
         continue
        valid,data=self.validate_response(tab.current_chunk['text'],response,True)
        c_count=tab.current_chunk['count']
        if valid:
         duration=round(time.time()-tab.start_time,1)
         input_ids_in_chunk=[int(m.group(1)) for m in re.finditer(r'#(\d+)\b',tab.current_chunk['text'])]
         for tid in input_ids_in_chunk:
          orig_match=re.search(rf"#{tid}\s+(.*?)(?=\s*#|$)",tab.current_chunk['text'],re.DOTALL)
          orig_text=orig_match.group(1).strip().rstrip(';').strip() if orig_match else ""
          if tid in data:
           ttext=data[tid]
           clean_text=ttext.rstrip(';').strip()
           if clean_text and self.has_chinese(clean_text):
            self.parent.update_table_signal.emit(str(tid),clean_text)
            self.retry_items.append({'id':tid,'text':orig_text})
           else:
            self.parent.update_table_signal.emit(str(tid),clean_text)
          else:
           self.parent.update_table_signal.emit(str(tid),orig_text)
           self.retry_items.append({'id':tid,'text':orig_text})
         self.processed_rows+=c_count
         self.chunk_sent.emit(self.processed_rows,self.total_rows)
         self.log(f"Chunk {c_id} ok ({duration}s)")
         tab.usage_count+=1
         tab.retry_count=0
         tab.current_chunk=None
         time.sleep(random.uniform(2.0,3.0))
         self.check_pause(driver,tab.handle)
         if tab.queue:
          tab.current_chunk=tab.queue.pop(0)
          tab.start_time=time.time()
          if self.send_prompt(driver,tab.current_chunk['text'],wait):
           tab.status="GENERATING"
          else:
           tab.queue.insert(0,tab.current_chunk)
           tab.current_chunk=None
           tab.status="IDLE"
         else:
          tab.status="IDLE"
        else:
         tab.retry_count+=1
         if tab.retry_count<=3:
          if self.click_restore_button(driver):
           time.sleep(3)
           tab.queue.insert(0,tab.current_chunk)
           tab.current_chunk=None
           tab.status="IDLE"
          else:
           driver.switch_to.window(tab.handle)
           driver.get(link)
           time.sleep(3)
           self.select_model(driver,wait)
           tab.queue.insert(0,tab.current_chunk)
           tab.current_chunk=None
           tab.status="IDLE"
         else:
          tab.status="IDLE"
          tab.current_chunk=None
      elif tab.status=="IDLE" and tab.queue:
       tab.current_chunk=tab.queue.pop(0)
       tab.start_time=time.time()
       if self.send_prompt(driver,tab.current_chunk['text'],wait):
        tab.status="GENERATING"
       else:
        tab.queue.insert(0,tab.current_chunk)
        tab.current_chunk=None
        tab.status="IDLE"
     if all_done:active=False
    try:last_active_handle=driver.current_window_handle
    except:last_active_handle=base_handle
    all_handles=driver.window_handles
    if last_active_handle not in all_handles and all_handles:
     last_active_handle=all_handles[-1]
    if last_active_handle:
     try:
      driver.switch_to.window(last_active_handle)
      base_handle=last_active_handle
     except:pass
    for h in all_handles:
     if h!=base_handle:
      try:
       driver.switch_to.window(h)
       driver.close()
       time.sleep(0.5)
      except:pass
    try:driver.switch_to.window(base_handle)
    except:pass
   self.log("Dịch chunk chính xong!")
   if self.retry_items and not self.stopped:
    self.log(f"🚀 Xử lý {len(self.retry_items)} câu lỗi...")
    try:driver.switch_to.window(base_handle)
    except:
     if driver.window_handles:driver.switch_to.window(driver.window_handles[0])
    driver.get(link)
    time.sleep(4)
    self.select_model(driver,wait)
    rescue_chunks=[]
    for i in range(0,len(self.retry_items),batch_size):
     chunk_items=self.retry_items[i:i+batch_size]
     chunk_text="; ".join([f"#{item['id']} {item['text']}" for item in chunk_items])
     rescue_chunks.append({'items':chunk_items,'text':chunk_text})
    for idx,r_chunk in enumerate(rescue_chunks):
     if self.stopped:break
     self.check_pause(driver,base_handle)
     if self.send_prompt(driver,r_chunk['text'],wait):
      if self.wait_until_done_blocking(driver):
       resp=self.extract_response(driver)
       v_valid,v_data=self.validate_response(r_chunk['text'],resp,check_chinese=False)
       if v_valid:
        count_ok=0
        for item in r_chunk['items']:
         tid=item['id']
         if tid in v_data:
          clean_text=v_data[tid].rstrip(';').strip()
          self.parent.update_table_signal.emit(str(tid),clean_text)
          count_ok+=1
       else:pass
     time.sleep(random.uniform(2.0,3.0))
   self.log("Hoàn Thành Toàn Bộ!")
  except Exception as e:
   self.log(f"Lỗi: {e}")
  finally:
   self.finished.emit()
   if driver:driver.quit()

class GemNameDialog(QDialog):
 def __init__(self,parent=None,default_name=""):
  super().__init__(parent)
  self.setWindowTitle("Đặt Tên Gem")
  self.setFixedSize(380,200)
  self.gem_name=None
  self.setStyleSheet("""
  QDialog { background-color: #1e1e2e; border: 1px solid #444466; border-radius: 10px; }
  QLabel#title_label { color: #cdd6f4; font-size: 13px; font-weight: bold; padding: 4px 0px 2px 0px; }
  QLabel#sub_label { color: #a6adc8; font-size: 11px; }
  QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #585b70; border-radius: 6px; padding: 8px 10px; font-size: 13px; selection-background-color: #89b4fa; selection-color: #1e1e2e; }
  QLineEdit:focus { border: 1px solid #89b4fa; }
  QPushButton { border-radius: 6px; padding: 7px 20px; font-size: 12px; font-weight: bold; }
  QPushButton#btn_ok { background-color: #89b4fa; color: #1e1e2e; border: none; }
  QPushButton#btn_ok:hover { background-color: #b4d0fb; }
  QPushButton#btn_cancel { background-color: #45475a; color: #cdd6f4; border: none; }
  QPushButton#btn_cancel:hover { background-color: #585b70; }
  """)
  outer=QVBoxLayout(self)
  outer.setContentsMargins(20,16,20,16)
  outer.setSpacing(10)
  lbl_title=QLabel("💎 Đặt Tên Gem")
  lbl_title.setObjectName("title_label")
  outer.addWidget(lbl_title)
  lbl_sub=QLabel("Tên sẽ hiển thị trong dropdown. Mã code vẫn được lưu nguyên.")
  lbl_sub.setObjectName("sub_label")
  lbl_sub.setWordWrap(True)
  outer.addWidget(lbl_sub)
  self.ent_name=QLineEdit()
  self.ent_name.setText(default_name)
  self.ent_name.selectAll()
  self.ent_name.setPlaceholderText("Nhập tên gem...")
  self.ent_name.returnPressed.connect(self.accept)
  outer.addWidget(self.ent_name)
  btn_row=QHBoxLayout()
  btn_row.addStretch()
  btn_cancel=QPushButton("Hủy")
  btn_cancel.setObjectName("btn_cancel")
  btn_cancel.setFixedWidth(90)
  btn_cancel.clicked.connect(self.reject)
  btn_ok=QPushButton("Xác nhận")
  btn_ok.setObjectName("btn_ok")
  btn_ok.setFixedWidth(100)
  btn_ok.clicked.connect(self.accept)
  btn_row.addWidget(btn_cancel)
  btn_row.addWidget(btn_ok)
  outer.addLayout(btn_row)
 def accept(self):
  self.gem_name=self.ent_name.text().strip()
  super().accept()

class MainWindow(QMainWindow):
 update_log_signal=Signal(str)
 update_table_signal=Signal(str,str)
 def __init__(self):
  super().__init__()
  self.setWindowTitle("Gemini Auto Translator Pro (Licensed)")
  self.resize(1400,850)
  self.license_manager=LicenseManager()
  self.license_info=None
  self.license_valid=False
  self.blink_state=False
  self.is_paused=False
  self.original_srt_path=None
  self.local_profile=os.path.join(os.getcwd(),"chrome_profile")
  self.backup_profile=os.path.join(get_appdata_dir(),"GeminiTranslatorProfile")
  self.gem_file=os.path.join(self.local_profile,"gem.json")
  self.backup_gem_file=os.path.join(self.backup_profile,"gem.json")
  self.profile_path=self.local_profile
  self.is_logged_in=os.path.isdir(self.backup_profile) and os.listdir(self.backup_profile)
  self.update_log_signal.connect(self.log_ui)
  self.update_table_signal.connect(self.update_table_item)
  self.setup_ui()
  self.check_license_status()
  self.license_timer=QTimer(self)
  self.license_timer.timeout.connect(self.update_license_display)
  self.license_timer.start(1000)
  self.restore_profile_from_backup()
  self.load_gems()
  self.update_login_status()
  self.on_model_changed(self.cb_model.currentText())
  self.btn_open.clicked.connect(self.open_srt_file)
  self.btn_save.clicked.connect(self.save_srt_file)
 def format_time(self,seconds):
  if seconds<=0:return "00:00:00:00"
  days=seconds//(24*3600)
  seconds%=(24*3600)
  hours=seconds//3600
  seconds%=3600
  minutes=seconds//60
  seconds%=60
  return f"{int(days):02d}:{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
 def copy_machine_id(self):
  clipboard=QApplication.clipboard()
  clipboard.setText(self.ent_machine_id.text())
  QMessageBox.information(self,"Thông báo","Đã sao chép mã máy!")
 def check_license_status(self):
  is_valid,info,msg=self.license_manager.check_license(self)
  self.license_info=info
  self.license_valid=is_valid
  my_id=self.license_manager.get_machine_id()
  self.ent_machine_id.setText(my_id)
  self.lbl_license_status.setText(msg)
  if not is_valid:
   self.btn_start.setEnabled(False)
   self.btn_start.setToolTip(msg)
   self.lbl_license_time.setText("00:00:00:00")
   self.lbl_license_status.setStyleSheet("color: #ff4d4d; font-weight: bold;")
  else:
   self.btn_start.setEnabled(True)
   self.btn_start.setToolTip("Sẵn sàng dịch")
   self.lbl_license_status.setStyleSheet("color: #2ecc71; font-weight: bold;")
 def update_license_display(self):
  if self.license_valid and self.license_info:
   secs=self.license_info.get('seconds_remaining',0)
   if secs>0:
    self.license_info['seconds_remaining']=secs-1
    remaining=self.license_info['seconds_remaining']
    if remaining>3153600000:
     self.lbl_license_time.setText("Vĩnh Viễn")
    else:
     self.lbl_license_time.setText(self.format_time(remaining))
    if secs<86400:self.lbl_license_time.setStyleSheet("color: #f1c40f; font-weight: bold;")
    else:self.lbl_license_time.setStyleSheet("color: #2ecc71; font-weight: bold;")
   else:
    self.license_valid=False
    self.check_license_status()
  else:
   self.btn_start.setEnabled(False)
   self.blink_state=not self.blink_state
   color="#ff4d4d" if self.blink_state else "#333"
   self.lbl_license_status.setStyleSheet(f"color: {color}; font-weight: bold;")
 def restore_profile_from_backup(self):
  if os.path.exists(self.backup_profile):
   if os.path.exists(self.local_profile):shutil.rmtree(self.local_profile,ignore_errors=True)
   shutil.copytree(self.backup_profile,self.local_profile)
 def save_profile_backup(self):
  if os.path.exists(self.local_profile):
   if os.path.exists(self.backup_profile):shutil.rmtree(self.backup_profile,ignore_errors=True)
   shutil.copytree(self.local_profile,self.backup_profile)
 def setup_ui(self):
  self.setStyleSheet("""
  QMainWindow { background-color: #333333; color: white; }
  QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #e0e0e0; }
  QFrame#Sidebar { background-color: #252525; border-right: 1px solid #444; }
  QFrame#LogPanel { background-color: #252525; border-top: 1px solid #444; }
  QPushButton { background-color: #444444; color: white; border: 1px solid #555; padding: 8px 15px; border-radius: 4px; font-weight: bold; }
  QPushButton:hover { background-color: #555555; }
  QPushButton#BtnPrimary { background-color: #007acc; border: none; }
  QPushButton#BtnSuccess { background-color: #2ecc71; border: none; }
  QPushButton#BtnSuccess:disabled { background-color: #444; color: #888; }
  QPushButton#BtnDanger { background-color: #e74c3c; border: none; }
  QPushButton#BtnWarning { background-color: #f39c12; border: none; }
  QLineEdit, QSpinBox, QComboBox { background-color: #2d2d2d; color: white; border: 1px solid #444; padding: 5px; border-radius: 3px; }
  QComboBox:on { border: 1px solid #666; }
  QComboBox QAbstractItemView { background-color: #2d2d2d; color: #e0e0e0; border: 1px solid #555; selection-background-color: #007acc; selection-color: white; outline: none; padding: 2px; }
  QComboBox QAbstractItemView::item { min-height: 26px; padding: 3px 8px; }
  QComboBox QAbstractItemView::item:hover { background-color: #3a3a3a; }
  QComboBox QAbstractItemView QScrollBar:vertical { background: #2d2d2d; width: 8px; border: none; }
  QComboBox QAbstractItemView QScrollBar::handle:vertical { background: #555; border-radius: 4px; min-height: 20px; }
  QComboBox QAbstractItemView QScrollBar::add-line:vertical, QComboBox QAbstractItemView QScrollBar::sub-line:vertical { height: 0px; }
  QTableWidget { background-color: #252525; alternate-background-color: #2d2d2d; gridline-color: #444; color: #e0e0e0; border: none; }
  QHeaderView::section { background-color: #1e1e1e; color: #bbb; padding: 6px; border: none; border-bottom: 1px solid #444; }
  QTextEdit { background-color: #333333; color: #ffffff; border: 1px solid #444; }
  QGroupBox { border: 1px solid #444; border-radius: 5px; margin-top: 20px; font-weight: bold; }
  QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; color: #bbb; }
  QProgressBar { background-color: #1a1a1a; border: 1px solid #555; border-radius: 8px; text-align: center; color: #000000; font-weight: bold; font-size: 14px; }
  QProgressBar::chunk { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #FF00FF, stop:0.5 #FFFF00, stop:1 #00FFFF); border-radius: 7px; }
  """)
  central=QWidget();self.setCentralWidget(central)
  main_layout=QHBoxLayout(central);main_layout.setContentsMargins(0,0,0,0);main_layout.setSpacing(0)
  sidebar=QFrame();sidebar.setObjectName("Sidebar");sidebar.setFixedWidth(300)
  side_layout=QVBoxLayout(sidebar)
  lbl_title=QLabel("GEMINI TRANSLATOR");lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
  lbl_title.setFont(QFont("Segoe UI",16,QFont.Weight.Bold))
  side_layout.addWidget(lbl_title)
  grp_license=QGroupBox("Thông Tin Bản Quyền");lic_layout=QVBoxLayout()
  h1=QHBoxLayout();h1.addWidget(QLabel("Mã máy:"));self.ent_machine_id=QLineEdit();self.ent_machine_id.setReadOnly(True);h1.addWidget(self.ent_machine_id)
  btn_copy=QPushButton("Copy");btn_copy.setFixedWidth(70);btn_copy.clicked.connect(self.copy_machine_id);h1.addWidget(btn_copy)
  lic_layout.addLayout(h1)
  h2=QHBoxLayout();h2.addWidget(QLabel("Trạng thái:"));self.lbl_license_status=QLabel("Kiểm tra...");h2.addWidget(self.lbl_license_status);lic_layout.addLayout(h2)
  h3=QHBoxLayout();h3.addWidget(QLabel("Thời hạn:"));self.lbl_license_time=QLabel("00:00:00:00");h3.addWidget(self.lbl_license_time);lic_layout.addLayout(h3)
  grp_license.setLayout(lic_layout);side_layout.addWidget(grp_license)
  self.btn_login=QPushButton("Đăng nhập Google");self.btn_login.clicked.connect(self.handle_login_logout)
  side_layout.addWidget(self.btn_login)
  grp_ai=QGroupBox("Cấu Hình AI");ai_layout=QVBoxLayout()
  ai_layout.addWidget(QLabel("Model:"));self.cb_model=QComboBox();self.cb_model.addItems(MODEL_DISPLAY)
  self.cb_model.currentTextChanged.connect(self.on_model_changed);ai_layout.addWidget(self.cb_model)
  row_cfg=QHBoxLayout()
  v1=QVBoxLayout();v1.addWidget(QLabel("Batch:"));self.ent_chunk=QLineEdit();v1.addWidget(self.ent_chunk);row_cfg.addLayout(v1)
  self.ent_chunk.textChanged.connect(self.update_chunk_stats)
  v2=QVBoxLayout();v2.addWidget(QLabel("Số Luồng:"));self.spin_threads=QSpinBox();self.spin_threads.setRange(1,10);self.spin_threads.setValue(6);self.spin_threads.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons);v2.addWidget(self.spin_threads);row_cfg.addLayout(v2)
  ai_layout.addLayout(row_cfg);grp_ai.setLayout(ai_layout);side_layout.addWidget(grp_ai)
  grp_link=QGroupBox("Kết Nối Gemini");l_layout=QVBoxLayout()
  self.cb_gem=QComboBox()
  self.cb_gem.setPlaceholderText("-- Chọn Gem --")
  l_layout.addWidget(self.cb_gem)
  self.ent_add_gem=QLineEdit()
  self.ent_add_gem.setPlaceholderText("Dán mã / URL gem rồi nhấn Enter...")
  self.ent_add_gem.setVisible(False)
  self.ent_add_gem.returnPressed.connect(self._confirm_add_gem)
  l_layout.addWidget(self.ent_add_gem)
  gem_btn_row=QHBoxLayout()
  self.btn_add_gem=QPushButton("+ Thêm Gem");self.btn_add_gem.clicked.connect(self._open_add_gem_input);gem_btn_row.addWidget(self.btn_add_gem)
  self.btn_rename_gem=QPushButton("Sửa tên");self.btn_rename_gem.clicked.connect(self._rename_current_gem);gem_btn_row.addWidget(self.btn_rename_gem)
  self.btn_del_gem=QPushButton("Xóa");self.btn_del_gem.clicked.connect(self._delete_current_gem);self.btn_del_gem.setObjectName("BtnDanger");gem_btn_row.addWidget(self.btn_del_gem)
  l_layout.addLayout(gem_btn_row)
  grp_link.setLayout(l_layout);side_layout.addWidget(grp_link)
  grp_gem=QGroupBox("Quản Lý Gem");gem_layout=QVBoxLayout()
  lang_row=QHBoxLayout()
  self.ent_lang_src=QLineEdit("Tiếng Trung");self.ent_lang_src.setAlignment(Qt.AlignmentFlag.AlignCenter);lang_row.addWidget(self.ent_lang_src)
  lbl_arrow=QLabel("→");lbl_arrow.setAlignment(Qt.AlignmentFlag.AlignCenter);lang_row.addWidget(lbl_arrow)
  self.ent_lang_dst=QLineEdit("Tiếng Việt");self.ent_lang_dst.setAlignment(Qt.AlignmentFlag.AlignCenter);lang_row.addWidget(self.ent_lang_dst)
  gem_layout.addLayout(lang_row)
  self.btn_create_gem=QPushButton("Tạo Gem Mới");self.btn_create_gem.clicked.connect(self.start_create_gem);gem_layout.addWidget(self.btn_create_gem)
  self.btn_update_gem=QPushButton("Cập nhật ngôn ngữ Gem hiện tại");self.btn_update_gem.clicked.connect(self.start_update_gem);gem_layout.addWidget(self.btn_update_gem)
  grp_gem.setLayout(gem_layout);side_layout.addWidget(grp_gem)
  side_layout.addSpacing(10)
  self.btn_open=QPushButton("Mở File SRT");side_layout.addWidget(self.btn_open)
  self.btn_save=QPushButton("Lưu File SRT");side_layout.addWidget(self.btn_save)
  self.lbl_stats=QLabel("Tổng dòng: 0");side_layout.addWidget(self.lbl_stats)
  self.lbl_chunk_stats=QLabel("Tổng chunk: 0");side_layout.addWidget(self.lbl_chunk_stats)
  side_layout.addStretch()
  self.btn_start=QPushButton("BẮT ĐẦU DỊCH");self.btn_start.setObjectName("BtnSuccess");self.btn_start.setFixedHeight(45);self.btn_start.clicked.connect(self.start_translate)
  btn_control_layout=QHBoxLayout()
  self.btn_pause=QPushButton("TẠM DỪNG");self.btn_pause.setObjectName("BtnWarning");self.btn_pause.setFixedHeight(45);self.btn_pause.setEnabled(False);self.btn_pause.clicked.connect(self.toggle_pause)
  self.btn_stop=QPushButton("HỦY");self.btn_stop.setObjectName("BtnDanger");self.btn_stop.setFixedHeight(45);self.btn_stop.setEnabled(False);self.btn_stop.clicked.connect(self.stop_translate)
  btn_control_layout.addWidget(self.btn_pause);btn_control_layout.addWidget(self.btn_stop)
  side_layout.addWidget(self.btn_start);side_layout.addLayout(btn_control_layout)
  content_widget=QWidget();content_layout=QVBoxLayout(content_widget);content_layout.setContentsMargins(0,0,0,0)
  splitter=QSplitter(Qt.Orientation.Vertical);splitter.setHandleWidth(1);splitter.setStyleSheet("QSplitter::handle { background-color: #444; }")
  self.table=QTableWidget();self.table.setColumnCount(4);self.table.setHorizontalHeaderLabels(["STT","Timeline","Gốc","Bản dịch"])
  self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn);self.table.setAlternatingRowColors(True)
  self.table.setCornerButtonEnabled(False);self.table.verticalHeader().setVisible(False)
  header=self.table.horizontalHeader();self.table.setColumnWidth(0,45);self.table.setColumnWidth(1,220)
  header.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch);header.setSectionResizeMode(3,QHeaderView.ResizeMode.Stretch)
  splitter.addWidget(self.table)
  log_container=QFrame();log_container.setObjectName("LogPanel");log_layout=QVBoxLayout(log_container);log_layout.setContentsMargins(10,8,10,8)
  status_row=QHBoxLayout()
  self.lbl_status=QLabel("Sẵn sàng");self.lbl_status.setStyleSheet("font-weight:bold; color:#007acc;");status_row.addWidget(self.lbl_status)
  self.progress=QProgressBar();self.progress.setFixedHeight(30);self.progress.setTextVisible(True);self.progress.setFormat("%p% (%v/%m)")
  status_row.addWidget(self.progress);log_layout.addLayout(status_row)
  self.log_box=QTextEdit();self.log_box.setReadOnly(True);log_layout.addWidget(self.log_box)
  splitter.addWidget(log_container);splitter.setSizes([550,300])
  content_layout.addWidget(splitter);main_layout.addWidget(sidebar);main_layout.addWidget(content_widget,1)
 def log_ui(self,msg):
  self.log_box.append(msg);self.log_box.moveCursor(self.log_box.textCursor().MoveOperation.End)
 def update_table_item(self,target_id,text):
  for row in range(self.table.rowCount()):
   id_item=self.table.item(row,0)
   if id_item and id_item.text()==target_id:
    self.table.setItem(row,3,QTableWidgetItem(text))
    return
 def open_srt_file(self):
  file,_=QFileDialog.getOpenFileName(self,"Chọn file SRT","","Subtitle files (*.srt)")
  if not file:return
  self.original_srt_path=file
  if not self.license_valid:
   QMessageBox.warning(self,"Bản quyền","Vui lòng kích hoạt bản quyền!")
   return
  try:
   with open(file,"r",encoding="utf-8") as f:content=f.read().replace('\ufeff','')
   blocks=re.split(r'\n\s*\n',content.strip())
   self.table.setRowCount(0);row=0
   for block in blocks:
    lines=[l.strip() for l in block.split('\n') if l.strip()]
    if len(lines)>=2 and "-->" in lines[1]:
     timeline_text=lines[1]
     content_text=" ".join(lines[2:])
     self.table.insertRow(row)
     self.table.setItem(row,0,QTableWidgetItem(str(row+1)))
     self.table.setItem(row,1,QTableWidgetItem(timeline_text))
     self.table.setItem(row,2,QTableWidgetItem(content_text))
     row+=1
   self.lbl_stats.setText(f"Tổng dòng: {row}")
   self.update_chunk_stats()
   self.log_ui(f"Đã mở: {file} (Đã xử lý {row} câu, ID được đánh số lại)")
   self.original_srt_path=file
  except Exception as e:
   self.log_ui(f"Lỗi mở file: {e}")
   self.original_srt_path=None
 def update_chunk_stats(self):
  rows=self.table.rowCount()
  if rows==0:self.lbl_chunk_stats.setText("Tổng chunk: 0");return
  try:
   b=self.ent_chunk.text().strip()
   if b.isdigit() and int(b)>0:
    self.lbl_chunk_stats.setText(f"Tổng chunk: {math.ceil(rows/int(b))}")
   else:self.lbl_chunk_stats.setText("Tổng chunk: (lỗi batch)")
  except:self.lbl_chunk_stats.setText("Tổng chunk: (lỗi)")
 def save_srt_file(self):
  if not self.license_valid:
   self.log_ui("Lỗi: Cần có bản quyền để lưu file.")
   QMessageBox.warning(self,"Bản quyền","Vui lòng kích hoạt bản quyền để lưu file!")
   return
  if not self.original_srt_path:
   self.log_ui("Lỗi: Chưa mở file SRT nào để lưu.")
   QMessageBox.warning(self,"Lỗi","Vui lòng mở một file SRT trước khi lưu.")
   return
  try:
   with open(self.original_srt_path,"w",encoding="utf-8") as f:
    for r in range(self.table.rowCount()):
     idx=self.table.item(r,0)
     time_item=self.table.item(r,1)
     orig=self.table.item(r,2)
     trans=self.table.item(r,3)
     if not (idx and time_item and orig):continue
     text_to_write=trans.text() if trans and trans.text() else orig.text()
     f.write(f"{idx.text()}\n{time_item.text()}\n{text_to_write}\n\n")
   self.log_ui(f"✅ Đã lưu thành công: {self.original_srt_path}")
  except Exception as e:
   self.log_ui(f"❌ Lỗi lưu file: {e}")
   QMessageBox.critical(self,"Lỗi",f"Không thể lưu file:\n{e}")
 def start_translate(self):
  if not self.license_valid:
   QMessageBox.critical(self,"Lỗi","Bản quyền không hợp lệ!")
   return
  self.log_ui("Bắt đầu dịch...")
  self.is_paused=False
  self.btn_pause.setText("TẠM DỪNG")
  self.btn_pause.setObjectName("BtnWarning")
  self.btn_pause.style().unpolish(self.btn_pause);self.btn_pause.style().polish(self.btn_pause)
  self.translate_thread=TranslateThread(self)
  self.translate_thread.started.connect(self.on_started)
  self.translate_thread.finished.connect(self.on_finished)
  self.translate_thread.chunk_sent.connect(lambda s,t:self.progress.setValue(s))
  self.translate_thread.log_signal.connect(self.log_ui)
  self.translate_thread.start()
 def on_started(self):
  self.btn_start.setEnabled(False)
  self.btn_stop.setEnabled(True)
  self.btn_pause.setEnabled(True)
  self.progress.setMaximum(self.table.rowCount())
  self.lbl_status.setText("Đang chạy...")
 def on_finished(self):
  self.btn_start.setEnabled(True if self.license_valid else False)
  self.btn_stop.setEnabled(False)
  self.btn_pause.setEnabled(False)
  self.lbl_status.setText("Hoàn tất" if self.license_valid else "Dừng")
 def toggle_pause(self):
  if not hasattr(self,'translate_thread') or not self.translate_thread.isRunning():return
  if self.is_paused:
   self.translate_thread.resume()
   self.is_paused=False
   self.btn_pause.setText("TẠM DỪNG")
   self.btn_pause.setObjectName("BtnWarning")
  else:
   self.translate_thread.pause()
   self.is_paused=True
   self.btn_pause.setText("TIẾP TỤC")
   self.btn_pause.setObjectName("BtnSuccess")
  self.btn_pause.style().unpolish(self.btn_pause)
  self.btn_pause.style().polish(self.btn_pause)
 def stop_translate(self):
  if hasattr(self,'translate_thread') and self.translate_thread.isRunning():
   self.translate_thread.stop()
   self.log_ui("Đang dừng...")
 def closeEvent(self,event):
  if hasattr(self,'translate_thread') and self.translate_thread.isRunning():
   self.translate_thread.stop()
   self.translate_thread.wait()
  event.accept()
 def on_model_changed(self,name):
  self.ent_chunk.setText(str(MODEL_CHUNK_SIZE.get(name,200)))
 def _extract_gem_code(self,raw):
  raw=raw.strip()
  m=re.search(r"gem(?:ini\.google\.com/gem(?:s/[^/]+)?)?/([a-zA-Z0-9]+)",raw)
  if m:return m.group(1)
  if raw.startswith("http"):return raw.rstrip("/").split("/")[-1] if raw.split("/") else raw
  return raw
 def _read_gem_json(self):
  for path in (self.gem_file,self.backup_gem_file):
   if os.path.exists(path):
    try:
     with open(path,"r",encoding="utf-8") as f:
      data=json.load(f)
     if isinstance(data,list):
      result=[]
      for g in data:
       if isinstance(g,dict) and g.get("code"):
        result.append({"name":g.get("name",g["code"]),"code":g["code"]})
       elif isinstance(g,str) and g:
        result.append({"name":g,"code":g})
      return result
    except:pass
  return []
 def _write_gem_json(self,gems:list):
  os.makedirs(self.local_profile,exist_ok=True)
  with open(self.gem_file,"w",encoding="utf-8") as f:
   json.dump(gems,f,ensure_ascii=False,indent=2)
  if os.path.exists(self.backup_profile):
   os.makedirs(self.backup_profile,exist_ok=True)
   with open(self.backup_gem_file,"w",encoding="utf-8") as f:
    json.dump(gems,f,ensure_ascii=False,indent=2)
 def load_gems(self):
  gems=self._read_gem_json()
  self.cb_gem.blockSignals(True)
  self.cb_gem.clear()
  for g in gems:
   self.cb_gem.addItem(g["name"],userData=g["code"])
  self.cb_gem.blockSignals(False)
  if self.cb_gem.count()>0:
   self.cb_gem.setCurrentIndex(0)
 def save_gem(self,code:str,name:str=""):
  code=self._extract_gem_code(code)
  if not code:return
  if not name:name=code
  gems=self._read_gem_json()
  existing_codes=[g["code"] for g in gems]
  if code not in existing_codes:
   gems.append({"name":name,"code":code})
   self._write_gem_json(gems)
  self.cb_gem.blockSignals(True)
  current_codes=[self.cb_gem.itemData(i) for i in range(self.cb_gem.count())]
  if code not in current_codes:
   self.cb_gem.addItem(name,userData=code)
  idx=next((i for i in range(self.cb_gem.count()) if self.cb_gem.itemData(i)==code),0)
  self.cb_gem.setCurrentIndex(idx)
  self.cb_gem.blockSignals(False)
 def _open_add_gem_input(self):
  self.ent_add_gem.clear()
  self.ent_add_gem.setVisible(True)
  self.ent_add_gem.setFocus()
 def _confirm_add_gem(self):
  raw=self.ent_add_gem.text().strip()
  if not raw:
   self.ent_add_gem.setVisible(False)
   return
  code=self._extract_gem_code(raw)
  dialog=GemNameDialog(self,default_name=code)
  if dialog.exec():
   name=dialog.gem_name or code
   self.save_gem(code,name)
   self.log_ui(f"✅ Đã thêm Gem: {name} ({code})")
  self.ent_add_gem.clear()
  self.ent_add_gem.setVisible(False)
 def _rename_current_gem(self):
  idx=self.cb_gem.currentIndex()
  if idx<0:return
  code=self.cb_gem.itemData(idx)
  old_name=self.cb_gem.itemText(idx)
  dialog=GemNameDialog(self,default_name=old_name)
  if dialog.exec():
   new_name=dialog.gem_name.strip()
   if not new_name or new_name==old_name:return
   gems=self._read_gem_json()
   for g in gems:
    if g["code"]==code:
     g["name"]=new_name
     break
   self._write_gem_json(gems)
   self.cb_gem.setItemText(idx,new_name)
   self.log_ui(f"✏️ Đã đổi tên Gem: {old_name} ➔ {new_name}")
 def _delete_current_gem(self):
  idx=self.cb_gem.currentIndex()
  if idx<0:return
  code=self.cb_gem.itemData(idx)
  name=self.cb_gem.itemText(idx)
  gems=self._read_gem_json()
  gems=[g for g in gems if g["code"]!=code]
  self._write_gem_json(gems)
  self.cb_gem.removeItem(idx)
  self.log_ui(f"🗑️ Đã xóa Gem: {name} ({code})")
 def update_login_status(self):
  self.btn_login.setText("Đăng xuất Google" if self.is_logged_in else "Đăng nhập Google")
  self.btn_login.setObjectName("BtnDanger" if self.is_logged_in else "BtnPrimary")
  self.btn_login.style().unpolish(self.btn_login);self.btn_login.style().polish(self.btn_login)
 def handle_login_logout(self):
  if self.is_logged_in:
   reply=QMessageBox.question(self,"Xác nhận","Đăng xuất và xóa profile?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
   if reply==QMessageBox.StandardButton.Yes:
    shutil.rmtree(self.backup_profile,ignore_errors=True)
    shutil.rmtree(self.local_profile,ignore_errors=True)
    self.is_logged_in=False
    self.log_ui("Profile đã xóa")
  else:
   o=uc.ChromeOptions()
   o.add_argument(f"--user-data-dir={self.local_profile}")
   try:
    chrome_major=ensure_uc_driver_matches_chrome()
    self.update_log_signal.emit(f"[INFO] Chrome major detected: {chrome_major}")
    d=uc.Chrome(version_main=chrome_major,options=o,use_subprocess=False)
   except Exception as e:
    self.update_log_signal.emit(f"[WARN] Không detect được Chrome version: {e}. Dùng uc mặc định.")
    d=uc.Chrome(options=o,use_subprocess=False)
   d.get("https://accounts.google.com/")
   QMessageBox.information(self,"Login","Đăng nhập xong thì bấm OK")
   d.quit()
   self.save_profile_backup()
   self.is_logged_in=True
  self.update_login_status()
 def get_hidden_driver(self):
  options=uc.ChromeOptions()
  options.add_argument(f"--user-data-dir={self.local_profile}")
  options.add_argument('--headless=new')
  options.add_argument('--disable-gpu')
  try:
   chrome_major=ensure_uc_driver_matches_chrome()
   return uc.Chrome(version_main=chrome_major,options=options,headless=True,use_subprocess=False)
  except Exception as e:
   try:return uc.Chrome(options=options,headless=True,use_subprocess=False)
   except Exception as e2:
    self.log_ui(f"Lỗi khởi tạo Chrome: {e2}")
    return None
 def start_create_gem(self):
  if not self.is_logged_in:
   QMessageBox.warning(self,"Lỗi","Vui lòng đăng nhập Google trước!")
   return
  src_lang=self.ent_lang_src.text().strip().lower()
  dst_lang=self.ent_lang_dst.text().strip().lower()
  gem_name=f"dich {random.randint(100,999)}"
  prompt=f"""Dịch đối thoại {src_lang} sang {dst_lang}, không bình luận bất kể lý do. 
Nhiệm vụ chính: Dịch từng khối riêng lẻ, giữ nghiêm ngặt ánh xạ 1:1 (cấm gộp/tách khối) để bảo toàn timing. 
Chỉ dịch dựa trên nội dung khối hiện tại, không hợp nhất câu cắt dở. 
Đầu ra ví dụ: #1 Dịch ; #2 Dịch ; ... ; #N Dịch. 
Chú Giải: #? là số khối gốc, Dịch là văn bản đã dịch, ngăn cách mỗi khối bằng ;  
Trả đầy đủ tất cả [x-y] đã đưa vào, không thiếu không thừa.
Phong cách hài hước và Tự nhiên, ngắn gọn, mượt mà, hiện đại. (áp dụng trong ràng buộc 1:1): 
- Giữ nguyên cấu trúc và dấu câu gốc. 
- Chỉ dịch lời thoại nói, bỏ qua mô tả/ghi chú. 
- Xóa filler vô nghĩa (ah, um, hmm, ha ha, ơ, à…) trừ khi là nội dung duy nhất của khối. 
- Khẩu ngữ phù hợp ngữ cảnh, chọn xưng hô/sắc thái đúng nhân vật. 
- Điều chỉnh cú pháp cho lưu loát, dễ hiểu ngay khi đọc lướt, nhưng không thay đổi ý nghĩa cốt lõi. 
- Xem trước nội dung văn bản để hiểu ngữ cảnh cốt truyện tốt nhất ."""
  self.log_ui("Đang khởi tạo Gem mới...")
  QApplication.processEvents()
  driver=self.get_hidden_driver()
  if not driver:return
  try:
   driver.get("https://gemini.google.com/gems/create")
   time.sleep(3)
   try:
    js_click_login="""
    return (function(){
    const btn = document.querySelector('a[aria-label="Đăng nhập"]');
    if (btn) { btn.click(); return true; }
    return false;
    })();
    """
    if driver.execute_script(js_click_login):
     self.log_ui("Phát hiện nút Đăng nhập, đang thực hiện click...")
     time.sleep(2)
   except:pass
   try:
    js_name=f"""
    const input = document.querySelector('#gem-name-input');
    if(input) {{
    input.value = {json.dumps(gem_name)};
    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
    }}
    """
    driver.execute_script(js_name)
   except:pass
   safe_prompt=json.dumps(prompt)
   js_inject_prompt=f"""
   const editor = document.querySelector('.ql-editor[contenteditable="true"]');
   if (editor) {{
   editor.focus();
   editor.textContent = {safe_prompt};
   editor.dispatchEvent(new InputEvent('input', {{
   bubbles: true, cancelable: true,
   inputType: 'insertText', data: {safe_prompt}
   }}));
   }}
   """
   driver.execute_script(js_inject_prompt)
   time.sleep(1)
   try:driver.execute_script("document.querySelector('[data-test-id=\"create-button\"]').click();")
   except:pass
   self.log_ui("Đang chờ xác nhận tạo Gem...")
   dialog_found=False
   for _ in range(15):
    try:
     btn_chat=driver.find_element(By.CSS_SELECTOR,'[data-test-id="new-conversation-button"]')
     if btn_chat.is_displayed():
      driver.execute_script("arguments[0].click();",btn_chat)
      dialog_found=True
      break
    except:time.sleep(1)
   if dialog_found:
    time.sleep(3)
    current_url=driver.current_url
    match=re.search(r"gem/([a-zA-Z0-9]+)",current_url)
    if match:
     gem_code=match.group(1)
     self.save_gem(gem_code,gem_name)
     self.log_ui(f"✅ Đã tạo thành công Gem! Mã: {gem_code}")
     try:driver.quit()
     except:pass
     QMessageBox.information(self,"Thành công",f"Đã tạo Gem mới với mã: {gem_code}")
    else:
     self.log_ui("⚠️ Không trích xuất được mã Gem từ URL.")
   else:
    self.log_ui("❌ Quá thời gian chờ, không thấy popup xác nhận tạo Gem.")
  except Exception as e:
   self.log_ui(f"Lỗi tạo Gem: {str(e)}")
 def start_update_gem(self):
  gem_code=self.cb_gem.currentData() or ""
  if not gem_code:
   QMessageBox.warning(self,"Lỗi","Vui lòng chọn Gem ở dropdown Kết Nối trước!")
   return
  src_lang=self.ent_lang_src.text().strip().lower()
  dst_lang=self.ent_lang_dst.text().strip().lower()
  self.log_ui(f"Đang cập nhật Gem {gem_code}: {src_lang} → {dst_lang}...")
  driver=self.get_hidden_driver()
  if not driver:return
  try:
   driver.get(f"https://gemini.google.com/gems/edit/{gem_code}")
   time.sleep(5)
   safe_src=json.dumps(src_lang)
   safe_dst=json.dumps(dst_lang)
   js_update=f"""
   return (function() {{
   let editor = document.querySelector('.ql-editor') || document.querySelector('[aria-label*="Hướng dẫn"]') || document.querySelector('[aria-label*="Instructions"]') || document.querySelector('textarea:not([aria-hidden="true"])') || document.querySelector('[contenteditable="true"]');
   if (!editor) return false;
   const newSrc = {safe_src};
   const newDst = {safe_dst};
   let currentText = editor.value || editor.innerText || editor.textContent || "";
   currentText = currentText.replace(/\\n\\s*\\n/g, '\\n');
   let newText = currentText;
   const match = currentText.match(/Dịch đối thoại (.+?) sang (.+?),/i);
   if (match) {{
   newText = currentText.replace(match[0], `Dịch đối thoại ${{newSrc}} sang ${{newDst}},`);
   }} else {{
   newText = `Dịch đối thoại ${{newSrc}} sang ${{newDst}}, không bình luận bất kể lý do.\\n` + currentText;
   }}
   editor.focus();
   if (editor.tagName && (editor.tagName.toLowerCase() === 'textarea' || editor.tagName.toLowerCase() === 'input')) {{
   let nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
   if(nativeSetter) nativeSetter.call(editor, newText);
   else editor.value = newText;
   }} else {{
   document.execCommand('selectAll', false, null);
   document.execCommand('insertText', false, newText);
   editor.querySelectorAll('p').forEach(p => {{
   if (p.innerHTML.trim() === '<br>' || p.textContent.trim() === '') p.remove();
   }});
   }}
   editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
   editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
   editor.blur();
   return true;
   }})();
   """
   time.sleep(3)
   success=driver.execute_script(js_update)
   if success:
    clicked=False
    for _ in range(20):
     time.sleep(0.5)
     try:
      js_click="""
      let btn = document.querySelector('[data-test-id="create-button"]') || document.querySelector('[data-test-id="save-button"]');
      if (!btn) {
      const btns = Array.from(document.querySelectorAll('button'));
      btn = btns.find(b => {
      const t = b.textContent.toLowerCase();
      return t.includes('lưu') || t.includes('save') || t.includes('cập nhật') || t.includes('update');
      });
      }
      if(btn) {
      if(btn.disabled || btn.getAttribute('aria-disabled') === 'true') {
      btn.removeAttribute('disabled');
      btn.setAttribute('aria-disabled', 'false');
      }
      btn.click();
      return true;
      }
      return false;
      """
      if driver.execute_script(js_click):
       clicked=True
       break
     except:pass
    if clicked:
     time.sleep(1.5)
     self.log_ui("✅ Đã cập nhật ngôn ngữ Gem thành công!")
    else:
     self.log_ui("❌ Đã sửa text nhưng không tìm thấy nút Lưu/Cập nhật để click.")
   else:
    self.log_ui("❌ Script chạy xong nhưng không tìm thấy ô nhập nội dung Gem. (Google có thể đã đổi giao diện)")
  except Exception as e:
   self.log_ui(f"Lỗi cập nhật Gem: {str(e)}")

if __name__=="__main__":
 app=QApplication(sys.argv)
 win=MainWindow()
 win.show()
 sys.exit(app.exec())
