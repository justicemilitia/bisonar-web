import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json

class KommoScraper:
    def __init__(self):
        # Chrome options
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Test sırasında kapatın
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 20)
        
    def login(self):
        """Manuel login yapılacak, sadece sayfayı açar"""
        print("Lütfen manuel olarak giriş yapın...")
        self.driver.get("https://barancanaydin.kommo.com/settings/ai-agent/")
        input("Giriş yaptıktan sonra Enter'a basın...")
    
    def navigate_to_main_page(self):
        """Ana sayfaya döner"""
        try:
            self.driver.get("https://barancanaydin.kommo.com/settings/ai-agent/")
            print("Ana sayfaya dönüldü")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Ana sayfaya dönülemedi: {e}")
            return False
    
    def click_template_library(self):
        """Şablon kitaplığı linkine tıklar"""
        try:
            template_library_link = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@class, 'a449aeebc') and contains(text(), 'şablon kitaplığı')]")
            ))
            template_library_link.click()
            print("Şablon kitaplığı açıldı")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Şablon kitaplığı açılamadı: {e}")
            return False
    
    def select_specific_template(self, template_name):
        """Belirtilen isimdeki şablonu seçer"""
        try:
            template_xpath = f"//div[contains(@class, 'a4bd11230')]//span[contains(text(), '{template_name}')]"
            template_element = self.wait.until(EC.element_to_be_clickable((By.XPATH, template_xpath)))
            template_element.click()
            print(f"{template_name} şablonu seçildi")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"{template_name} şablonu seçilemedi: {e}")
            return False
    
    def click_use_template(self):
        """Şablonu kullan butonuna tıklar"""
        try:
            use_template_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[contains(text(), 'Şablonu kullan')]]")
            ))
            use_template_btn.click()
            print("Şablonu kullan butonuna tıklandı")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Şablonu kullan butonuna tıklanamadı: {e}")
            return False
    
    def click_understand(self):
        """Anladım butonuna tıklar"""
        try:
            understand_btn = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[.//span[contains(text(), 'Anladım')]]")
            ))
            understand_btn.click()
            print("Anladım butonuna tıklandı")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Anladım butonuna tıklanamadı: {e}")
            return False
    
    def click_actions_tab(self):
        """Eylemler tab'ına tıklar"""
        try:
            actions_tab = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Eylemler')]")
            ))
            actions_tab.click()
            print("Eylemler tab'ına tıklandı")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Eylemler tab'ına tıklanamadı: {e}")
            return False
    
    def click_personality_tab(self):
        """Kişilik tab'ına tıklar"""
        try:
            personality_tab = self.wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Kişilik')]")
            ))
            personality_tab.click()
            print("Kişilik tab'ına tıklandı")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"Kişilik tab'ına tıklanamadı: {e}")
            return False
    
    def extract_actions_data(self):
        """Zaman ve Yap bilgilerini çıkarır"""
        actions_data = []
        
        try:
            # Tüm action container'larını bul
            action_containers = self.driver.find_elements(By.CSS_SELECTOR, ".a79270358")
            print(f"Bulunan action container sayısı: {len(action_containers)}")
            
            for i, container in enumerate(action_containers):
                try:
                    # Zaman bilgisini al
                    zaman_element = container.find_element(By.CSS_SELECTOR, ".b335039c .a165d5ef4")
                    zaman_text = zaman_element.text.strip()
                    
                    # Yap bilgilerini al - tümünü birleştir
                    yap_container = container.find_element(By.XPATH, ".//div[contains(@class, 'a962f4668') and not(contains(@class, 'b335039c'))]")
                    yap_elements = yap_container.find_elements(By.CSS_SELECTOR, ".a165d5ef4")
                    yap_texts = [yap.text.strip() for yap in yap_elements if yap.text.strip()]
                    
                    # Yap maddelerini birleştir
                    yap_combined = " ".join(yap_texts)
                    
                    action_info = {
                        "zaman": zaman_text,
                        "yap": yap_combined
                    }
                    
                    actions_data.append(action_info)
                    print(f"Aksiyon {i+1} çıkarıldı:")
                    print(f"  Zaman: {zaman_text}")
                    print(f"  Yap: {yap_combined}")
                    
                except Exception as e:
                    print(f"Aksiyon {i+1} çıkarılırken hata: {e}")
                    continue
                    
        except Exception as e:
            print(f"Aksiyon verileri çıkarılırken hata: {e}")
        
        return actions_data
  
    def extract_personality_data(self):
        """Kişilik tab'ındaki tüm bilgileri çıkarır"""
        personality_data = {}
        
        try:
            # 1. Rol ve kişilik alanını al
            role_textarea = self.driver.find_element(By.CSS_SELECTOR, "textarea._textarea_1afq7_7")
            role_text = role_textarea.get_attribute("value")
            personality_data["rol_ve_kisilik"] = role_text
            print("Rol ve kişilik metni çıkarıldı")
            
            # 2. Ses tonu bilgisini al
            try:
                # "Ses tonu" label'ını takip eden butondaki değeri al
                voice_tone_button = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Ses tonu')]/following::button[contains(@class, '_button_14jv2_1')][1]")
                voice_tone_span = voice_tone_button.find_element(By.CSS_SELECTOR, "span._text_1thgf_1")
                personality_data["ses_tonu"] = voice_tone_span.text
                print(f"Ses tonu çıkarıldı: {voice_tone_span.text}")
            except Exception as e:
                print(f"Ses tonu çıkarılamadı: {e}")
                personality_data["ses_tonu"] = "Bulunamadı"
            
            # 3. Cevapların uzunluğu bilgisini al
            try:
                response_length_button = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Cevapların uzunluğu')]/following::button[contains(@class, '_button_14jv2_1')][1]")
                response_length_span = response_length_button.find_element(By.CSS_SELECTOR, "span._text_1thgf_1")
                personality_data["cevaplarin_uzunlugu"] = response_length_span.text
                print(f"Cevapların uzunluğu çıkarıldı: {response_length_span.text}")
            except Exception as e:
                print(f"Cevapların uzunluğu çıkarılamadı: {e}")
                personality_data["cevaplarin_uzunlugu"] = "Bulunamadı"
            
            # 4. Cevap dili bilgisini al
            try:
                response_language_button = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Cevap dili')]/following::button[contains(@class, '_button_14jv2_1')][1]")
                response_language_span = response_language_button.find_element(By.CSS_SELECTOR, "span._text_1thgf_1")
                personality_data["cevap_dili"] = response_language_span.text
                print(f"Cevap dili çıkarıldı: {response_language_span.text}")
            except Exception as e:
                print(f"Cevap dili çıkarılamadı: {e}")
                personality_data["cevap_dili"] = "Bulunamadı"
            
            # 5. Gecikme süresini al
            try:
                delay_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='seconds (Agent)']")
                delay_value = delay_input.get_attribute("value")
                personality_data["gecikme_suresi_saniye"] = delay_value
                print(f"Gecikme süresi çıkarıldı: {delay_value} saniye")
            except Exception as e:
                print(f"Gecikme süresi çıkarılamadı: {e}")
                personality_data["gecikme_suresi_saniye"] = "Bulunamadı"
            
            # 6. Kılavuzları al
            guidelines = []
            guideline_elements = self.driver.find_elements(By.CSS_SELECTOR, ".a7b6f224e ._input_x5289_1")
            
            for i, guideline_element in enumerate(guideline_elements):
                guideline_text = guideline_element.get_attribute("value")
                if guideline_text.strip():
                    guidelines.append(guideline_text)
                    print(f"Kılavuz {i+1} çıkarıldı: {guideline_text[:50]}...")
            
            personality_data["kilavuzlar"] = guidelines
            personality_data["toplam_kilavuz_sayisi"] = len(guidelines)
            
        except Exception as e:
            print(f"Kişilik verileri çıkarılırken hata: {e}")
        
        return personality_data
    
    def scrape_all_templates(self, template_names):
        """Birden fazla şablonu scrape eder - HER ŞABLON İÇİN ANA SAYFAYA DÖNER"""
        all_data = {}
        
        for template_name in template_names:
            print(f"\n{'='*50}")
            print(f"Şablon işleniyor: {template_name}")
            print(f"{'='*50}")
            
            # ÖNCE ANA SAYFAYA DÖN
            if not self.navigate_to_main_page():
                print(f"Ana sayfaya dönülemedi, {template_name} atlanıyor")
                continue
            
            # Şablon kitaplığını aç
            if not self.click_template_library():
                print(f"{template_name} için şablon kitaplığı açılamadı")
                continue
            
            # Belirtilen şablonu seç
            if not self.select_specific_template(template_name):
                print(f"{template_name} şablonu bulunamadı")
                continue
            
            # Şablonu kullan
            if not self.click_use_template():
                continue
            
            # Anladım butonu
            if not self.click_understand():
                continue
            
            # Eylemler tab'ına tıkla ve verileri çıkar
            if self.click_actions_tab():
                actions_data = self.extract_actions_data()
            else:
                actions_data = []
            
            # Kişilik tab'ına tıkla ve verileri çıkar
            if self.click_personality_tab():
                personality_data = self.extract_personality_data()
            else:
                personality_data = {}
            
            # Tüm verileri birleştir
            template_data = {
                "sablon_adi": template_name,  # Şablon adını ekle
                "aksiyonlar": actions_data,
                "kisilik": personality_data
            }
            
            all_data[template_name] = template_data
            
            print(f"{template_name} işlemi tamamlandı")
            print(f"  - {len(actions_data)} aksiyon bulundu")
            print(f"  - {personality_data.get('toplam_kilavuz_sayisi', 0)} kılavuz bulundu")
            print(f"  - Rol ve kişilik: {personality_data.get('rol_ve_kisilik', '')[:50]}...")
            
        return all_data
    
    def get_available_templates(self):
        """Mevcut tüm şablonları listeler"""
        templates = []
        try:
            # Ana sayfaya dön
            self.navigate_to_main_page()
            
            # Şablon kitaplığını aç
            if self.click_template_library():
                # Tüm şablon elementlerini bul
                template_elements = self.driver.find_elements(By.CSS_SELECTOR, ".a4bd11230 span")
                
                for element in template_elements:
                    if element.text.strip():
                        templates.append(element.text.strip())
                
                print(f"Bulunan şablonlar: {templates}")
                
                # Popup'ı kapat (herhangi bir yere tıklayarak)
                self.driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(1)
                
            return templates
        except Exception as e:
            print(f"Şablonlar listelenirken hata: {e}")
            return []
    
    def scrape_single_template(self, template_name=None):
        """Tek şablon için scraping işlemini yönetir"""
        if template_name is None:
            template_name = "Teknoloji mağazası satış danışmanı"
            
        print(f"Scraping işlemi başlatılıyor: {template_name}")
        
        # Ana sayfaya dön
        if not self.navigate_to_main_page():
            return None
        
        # Şablon kitaplığını aç
        if not self.click_template_library():
            return None
        
        # Şablon seç
        if not self.select_specific_template(template_name):
            return None
        
        # Şablonu kullan
        if not self.click_use_template():
            return None
        
        # Anladım butonu
        if not self.click_understand():
            return None
        
        # Eylemler tab'ına tıkla ve verileri çıkar
        if not self.click_actions_tab():
            actions_data = []
        else:
            actions_data = self.extract_actions_data()
        
        # Kişilik tab'ına tıkla ve verileri çıkar
        if not self.click_personality_tab():
            personality_data = {}
        else:
            personality_data = self.extract_personality_data()
        
        # Tüm verileri birleştir
        template_data = {
            "sablon_adi": template_name,  # Şablon adını ekle
            "aksiyonlar": actions_data,
            "kisilik": personality_data
        }
        
        return template_data
    
    def save_to_json(self, data, filename="kommo_verileri.json"):
        """Veriyi JSON dosyasına kaydeder"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Veriler {filename} dosyasına kaydedildi")
    
    def close(self):
        """Driver'ı kapatır"""
        self.driver.quit()

def main():
    scraper = KommoScraper()
    
    try:
        # Manuel login
        scraper.login()
        
        # Kullanıcı seçim yapsın
        print("\nSeçenekler:")
        print("1 - Tek şablon scrape et (Teknoloji mağazası satış danışmanı)")
        print("2 - Çoklu şablon scrape et")
        print("3 - Tüm şablonları otomatik bul ve scrape et")
        
        choice = input("Seçiminiz (1/2/3): ").strip()
        
        if choice == "1":
            # Tek şablon scraping
            template_data = scraper.scrape_single_template()
            
            if template_data:
                print("\nÇıkarılan Veriler:")
                print("=" * 60)
                
                # Aksiyonları göster
                print(f"\nAKSİYONLAR ({len(template_data['aksiyonlar'])} adet):")
                for aksiyon in template_data['aksiyonlar']:
                    print(f"\nZaman: {aksiyon['zaman']}")
                    print(f"Yap: {aksiyon['yap']}")
                
                # Kişilik bilgilerini göster
                print(f"\nKİŞİLİK BİLGİLERİ:")
                personality = template_data['kisilik']
                print(f"Rol ve Kişilik: {personality.get('rol_ve_kisilik', 'Bulunamadı')[:100]}...")
                print(f"Ses Tonu: {personality.get('ses_tonu', 'Bulunamadı')}")
                print(f"Cevapların Uzunluğu: {personality.get('cevaplarin_uzunlugu', 'Bulunamadı')}")
                print(f"Cevap Dili: {personality.get('cevap_dili', 'Bulunamadı')}")
                print(f"Gecikme Süresi: {personality.get('gecikme_suresi_saniye', 'Bulunamadı')} saniye")
                print(f"Kılavuzlar ({personality.get('toplam_kilavuz_sayisi', 0)} adet):")
                for i, kilavuz in enumerate(personality.get('kilavuzlar', []), 1):
                    print(f"  {i}. {kilavuz}")
                
                # JSON'a kaydet
                scraper.save_to_json(template_data, "tek_sablon_verileri.json")
            else:
                print("Veri çıkarılamadı")
                
        elif choice == "2":
            # Çoklu şablon scraping - Kullanıcı şablon isimlerini girer
            template_names_input = input("Scrape edilecek şablon isimlerini virgülle ayırarak girin: ")
            template_names = [name.strip() for name in template_names_input.split(",") if name.strip()]
            
            if template_names:
                all_data = scraper.scrape_all_templates(template_names)
                
                if all_data:
                    print("\nTüm Şablonlardan Çıkarılan Veriler:")
                    print("=" * 60)
                    
                    for template_name, template_data in all_data.items():
                        print(f"\n{template_name}:")
                        print(f"  - {len(template_data['aksiyonlar'])} aksiyon")
                        personality = template_data['kisilik']
                        print(f"  - {personality.get('toplam_kilavuz_sayisi', 0)} kılavuz")
                        print(f"  - Ses Tonu: {personality.get('ses_tonu', 'Bulunamadı')}")
                        print(f"  - Rol ve Kişilik: {personality.get('rol_ve_kisilik', '')[:50]}...")
                    
                    # JSON'a kaydet
                    scraper.save_to_json(all_data, "tum_sablonlar_verileri.json")
                else:
                    print("Hiçbir şablondan veri çıkarılamadı")
            else:
                print("Geçerli şablon ismi girilmedi")
                
        elif choice == "3":
            # Otomatik tüm şablonları bul ve scrape et
            print("Mevcut şablonlar taranıyor...")
            all_templates = scraper.get_available_templates()
            
            if all_templates:
                print(f"Bulunan şablonlar: {all_templates}")
                confirm = input(f"{len(all_templates)} şablon bulundu. Hepsi scrape edilsin mi? (e/h): ").strip().lower()
                
                if confirm == 'e':
                    all_data = scraper.scrape_all_templates(all_templates)
                    
                    if all_data:
                        print("\nTüm Şablonlardan Çıkarılan Veriler:")
                        print("=" * 60)
                        for template_name, template_data in all_data.items():
                            print(f"\n{template_name}:")
                            print(f"  - {len(template_data['aksiyonlar'])} aksiyon")
                            print(f"  - {template_data['kisilik'].get('toplam_kilavuz_sayisi', 0)} kılavuz")
                            print(f"  - Ses Tonu: {template_data['kisilik'].get('ses_tonu', 'Bulunamadı')}")
                        
                        # JSON'a kaydet
                        scraper.save_to_json(all_data, "tum_sablonlar_otomatik_verileri.json")
                    else:
                        print("Hiçbir şablondan veri çıkarılamadı")
                else:
                    print("İşlem iptal edildi")
            else:
                print("Hiç şablon bulunamadı")
        else:
            print("Geçersiz seçim")
            
    except Exception as e:
        print(f"Scraping sırasında hata oluştu: {e}")
    
    finally:
        # Kullanıcı çıkmak için Enter'a bassın
        input("\nScraping tamamlandı. Çıkmak için Enter'a basın...")
        scraper.close()

if __name__ == "__main__":
    main()