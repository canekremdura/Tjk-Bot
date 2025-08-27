from bs4 import BeautifulSoup
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import os

# Selenium
try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    import undetected_chromedriver as uc
except Exception:
    uc = None


class TJKScraper:
    BASE_URL = "https://www.tjk.org"

    def __init__(self, use_selenium: bool = True, headless: bool = True):
        # --- Logging ---
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # --- Selenium ---
        self.use_selenium = bool(use_selenium and uc is not None)
        self.driver = None
        if self.use_selenium:
            self._setup_selenium(headless=headless)

    # -------------------- Setup --------------------
    def _setup_selenium(self, headless: bool = True) -> None:
        try:
            options = uc.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")

            self.driver = uc.Chrome(options=options, version_main=None)
            self.driver.implicitly_wait(10)
            self.logger.info("Selenium başarıyla kuruldu")
        except Exception as e:
            self.logger.error(f"Selenium kurulum hatası: {e}")
            self.use_selenium = False
            self.driver = None

    # -------------------- Utilities --------------------
    @staticmethod
    def _normalize_text(text: Optional[str]) -> str:
        if not text:
            return ""
        text = text.strip()
        return re.sub(r"\s+", " ", text)

    # -------------------- Input --------------------
    def ask_date(self) -> str:
        print("\n=== TJK Yarış Sonuçları Çekici ===\n")
        while True:
            print("Tarih seçenekleri:\n1. Bugün\n2. Dün\n3. Özel tarih gir")
            choice = input("\nSeçiminizi yapın (1-3): ").strip()
            if choice == "1":
                return datetime.now().strftime("%d/%m/%Y")
            if choice == "2":
                return (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
            if choice == "3":
                date_input = input("Tarih (GG/AA/YYYY): ").strip()
                try:
                    datetime.strptime(date_input, "%d/%m/%Y")
                    return date_input
                except ValueError:
                    print("❌ Geçersiz tarih! Tekrar deneyin.")
            else:
                print("❌ Geçersiz seçim! 1-3 arası.")

    # -------------------- Fetch --------------------
    def _candidate_urls(self, date_str: str) -> List[str]:
        return [
            f"{self.BASE_URL}/TR/YarisSever/Info/Page/GunlukYarisSonuclari?QueryParameter_Tarih={date_str}",
            f"{self.BASE_URL}/TR/YarisSever/Info/Page/GunlukYarisProgrami?QueryParameter_Tarih={date_str}",
            f"{self.BASE_URL}/TR/YarisSonuclari?tarih={date_str}",
        ]

    def get_daily_races(self, date_str: str) -> Optional[List[Dict[str, Any]]]:
        """Sadece Selenium ile veri çeker."""
        self.logger.info(f"🏇 {date_str} için TJK verileri çekiliyor...")
        if self.use_selenium:
            return self._get_daily_races_selenium(date_str)
        return None

    def _get_daily_races_selenium(self, date_str: str) -> Optional[List[Dict[str, Any]]]:
        if not self.driver:
            return None
        for url in self._candidate_urls(date_str)[:2]:
            try:
                self.logger.info(f"Selenium ile açılıyor: {url}")
                self.driver.get(url)
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                time.sleep(1)  # JS sonrası kısa bekleme
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                races = self._extract_tjk_races(soup, date_str)
                if races:
                    self.logger.info(f"✅ Selenium başarılı: {len(races)} yarış")
                    return races
            except Exception as e:
                self.logger.warning(f"Selenium hata: {e}")
        return None

    # -------------------- Parse --------------------
    def _extract_tjk_races(self, soup: BeautifulSoup, date_str: str) -> List[Dict[str, Any]]:
        races: List[Dict[str, Any]] = []
        try:
            all_tables = soup.find_all("table")
            race_tables = self._identify_race_tables(all_tables)
            if not race_tables:
                self.logger.warning("Yarış tablosu bulunamadı")
                return []

            # Sayfa genel bilgiler
            page_info = self._extract_additional_race_info(soup)

            for idx, (orig_i, table) in enumerate(race_tables, start=1):
                try:
                    table_text = table.get_text(" ")
                    # distance ve surface değerlerini page_info'dan al
                    # Eğer page_info'da yoksa, tablodan çıkar
                    distance_from_page = page_info.get("distance", 0)
                    surface_from_page = page_info.get("surface", "Bilinmiyor")
                    
                    # Eğer page_info'dan gelen değerler geçerliyse kullan, değilse tablodan çıkar
                    if distance_from_page > 0:
                        distance = distance_from_page
                    else:
                        distance, _ = self._extract_race_details(table_text)
                    
                    if surface_from_page != "Bilinmiyor":
                        surface = surface_from_page
                    else:
                        _, surface = self._extract_race_details(table_text)

                    horses = self._extract_horses_from_tjk_table(table)

                    race_info: Dict[str, Any] = {
                        "race_number": idx,
                        "date": date_str,
                        "distance": distance,
                        "surface": surface,
                        "race_level": page_info.get("race_level", "Bilinmiyor"),
                        "race_description": page_info.get("race_description", ""),
                        "total_prize": page_info.get("total_prize", 0.0),
                        "detailed_surface_condition": page_info.get(
                            "detailed_surface_condition", "Bilinmiyor"
                        ),
                        "horses": horses,
                        "participant_count": len(horses),
                    }
                    if horses:
                        races.append(race_info)
                        self.logger.info(
                            f"🏇 Yarış {idx}: {len(horses)} at, {distance}m, {surface}"
                        )
                except Exception as e:
                    self.logger.error(f"Yarış {idx} işlenemedi: {e}")
        except Exception as e:
            self.logger.error(f"Yarış çıkarma hatası: {e}")
        return races

    def _identify_race_tables(self, all_tables: List[BeautifulSoup]) -> List[Tuple[int, BeautifulSoup]]:
        race_tables: List[Tuple[int, BeautifulSoup]] = []
        for i, table in enumerate(all_tables):
            try:
                rows = table.find_all("tr")
                if len(rows) < 3:
                    continue
                text = table.get_text(" ").lower()
                keywords = [
                    "koşu",
                    "yarış",
                    "safkan",
                    "jokey",
                    "antrenör",
                    "ganyan",
                    "kilo",
                    "yaş",
                    "derece",
                ]
                kw_count = sum(1 for k in keywords if k in text)
                has_numbers = bool(re.search(r"\b\d{1,3}\b", text))
                cell_count = len(table.find_all(["td", "th"]))
                score = (3 if kw_count >= 3 else 0) + (2 if has_numbers else 0) + (2 if cell_count > 20 else 0) + (1 if len(rows) > 5 else 0)
                if score >= 5:
                    race_tables.append((i, table))
            except Exception:
                continue
        return race_tables

    def _extract_race_details(self, text: str) -> Tuple[int, str]:
        distance = 0
        surface = "Bilinmiyor"
        distance_patterns = [
            r"(\d{3,4})\s*(?:m|metre|mt|meter)",
            r"mesafe[:\s]*(\d{3,4})",
            r"\b(\d{3,4})(?=\s*(?:metre|m\b))",
        ]
        for p in distance_patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                try:
                    distance = int(m.group(1))
                    break
                except Exception:
                    pass
        t = text.lower()
        if any(w in t for w in ["çim", "turf", "grass", "çimen"]):
            surface = "Çim"
        elif any(w in t for w in ["kum", "dirt", "toprak", "toz"]):
            surface = "Kum"
        elif any(w in t for w in ["sentetik", "polytrack", "yapay", "all weather"]):
            surface = "Sentetik"
        return distance, surface

    # --------- Horse row parsing ---------
    def _extract_horses_from_tjk_table(self, table: BeautifulSoup) -> List[Dict[str, Any]]:
        horses: List[Dict[str, Any]] = []
        rows = table.find_all("tr")
        if len(rows) < 2:
            return horses
        header_cells = rows[0].find_all(["th", "td"])  # bazı sayfalarda td olabiliyor
        column_map = self._analyze_tjk_headers(header_cells)
        for row_idx, row in enumerate(rows[1:], start=1):
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            cell_texts = [self._normalize_text(c.get_text()) for c in cells]
            horse = self._extract_single_horse_row(cells, column_map, cell_texts)
            if horse:
                horses.append(horse)
        return horses

    def _analyze_tjk_headers(self, header_cells: List[BeautifulSoup]) -> Dict[int, str]:
        column_map: Dict[int, str] = {}
        keywords = {
            "start_number": ["no", "sıra", "kapı", "start", "numara", "#"],
            "horse_name": ["at", "safkan", "isim", "ad", "horse", "name", "adı"],
            "horse_age": ["yaş", "yas", "age"],
            "weight": ["kilo", "ağırlık", "weight", "kg"],
            "jockey_name": ["jokey", "joki", "jockey"],
            "trainer_name": ["antrenör", "trainer", "coach"],
            "odds": ["ganyan", "oran", "odds", "pay"],
            "finish_position": ["derece", "sıralama", "position", "finish", "sonuç"],
            "finish_time": ["süre", "zaman", "time", "dk"],
        }
        for i, cell in enumerate(header_cells):
            h = self._normalize_text(cell.get_text()).lower()
            best, score = None, 0
            for field, kws in keywords.items():
                s = sum(len(k) for k in kws if k in h)
                if s > score:
                    best, score = field, s
            if best and score > 1:
                column_map[i] = best
        return column_map

    def _extract_single_horse_row(
        self,
        cells: List[BeautifulSoup],
        column_map: Dict[int, str],
        cell_texts: List[str],
    ) -> Optional[Dict[str, Any]]:
        horse: Dict[str, Any] = {
            "start_number": 0,
            "horse_name": "",
            "horse_age": 0,
            "weight": 0.0,
            "jockey_name": "",
            "trainer_name": "",
            "odds": 0.0,
            "finish_position": None,
            "finish_time": "",
            "jockey_equipment": [],
        }
        # Önce header eşleşmesiyle doldur
        for i, txt in enumerate(cell_texts):
            if i in column_map and txt:
                field = column_map[i]
                horse[field] = self._parse_field_value(txt, field)
        # Donanım ayrıştır, isim temizle
        if horse.get("horse_name"):
            eq_list, clean_name = self._extract_jockey_equipment(horse["horse_name"])
            horse["jockey_equipment"], horse["horse_name"] = eq_list, clean_name
        # Eksikler için otomatik tespit (nazikçe)
        for txt in cell_texts:
            self._fill_missing_fields_heuristic(horse, txt)
        # Basit doğrulama
        if not self._validate_horse(horse):
            return None
        return horse

    def _fill_missing_fields_heuristic(self, horse: Dict[str, Any], txt: str) -> None:
        def empty(v):
            return (isinstance(v, (int, float)) and v == 0) or (isinstance(v, str) and not v)

        if empty(horse.get("start_number")):
            cand = self._parse_field_value(txt, "start_number")
            if isinstance(cand, int) and 1 <= cand <= 30:
                horse["start_number"] = cand
        if empty(horse.get("weight")):
            cand = self._parse_field_value(txt, "weight")
            if isinstance(cand, (int, float)) and 40 <= cand <= 80:
                horse["weight"] = float(cand)
        if empty(horse.get("odds")):
            cand = self._parse_field_value(txt, "odds")
            if isinstance(cand, (int, float)) and cand > 0:
                horse["odds"] = float(cand)
        if empty(horse.get("finish_time")):
            cand = self._parse_field_value(txt, "finish_time")
            if isinstance(cand, str) and cand:
                horse["finish_time"] = cand
        if empty(horse.get("horse_age")):
            cand = self._parse_field_value(txt, "horse_age")
            if isinstance(cand, int) and 2 <= cand <= 25:
                horse["horse_age"] = cand
        if empty(horse.get("jockey_name")):
            cand = self._parse_field_value(txt, "jockey_name")
            if isinstance(cand, str) and cand:
                horse["jockey_name"] = cand
        if empty(horse.get("trainer_name")):
            cand = self._parse_field_value(txt, "trainer_name")
            if isinstance(cand, str) and cand:
                horse["trainer_name"] = cand

    def _parse_field_value(self, text: str, field: str):
        try:
            if field == "start_number":
                for num in re.findall(r"\b(\d{1,2})\b", text):
                    n = int(num)
                    if 1 <= n <= 30:
                        return n
                return 0
            if field == "horse_name":
                name = text.strip()
                return name if len(name) >= 2 else ""
            if field == "horse_age":
                m = re.search(r"(\d+)\s*y", text, re.IGNORECASE)
                if m:
                    age = int(m.group(1))
                    return age if 2 <= age <= 25 else 0
                for num in re.findall(r"\b(\d{1,2})\b", text):
                    age = int(num)
                    if 2 <= age <= 25:
                        return age
                return 0
            if field == "weight":
                m = re.search(r"(\d+(?:[.,]\d+)?)", text.replace(",", "."))
                if m:
                    w = float(m.group(1))
                    return w if 40 <= w <= 80 else 0
                return 0
            if field in {"jockey_name", "trainer_name"}:
                name = text.strip()
                return name if re.search(r"[a-zA-ZçğıiöşüÇĞIİÖŞÜ]", name) else ""
            if field == "odds":
                m = re.search(r"(\d+(?:[.,]\d+)?)", text.replace(",", "."))
                if m:
                    return float(m.group(1))
                nums = re.findall(r"\b(\d+)\b", text)
                return float(nums[0]) if nums else 0.0
            if field == "finish_position":
                for num in re.findall(r"\b(\d{1,2})\b", text):
                    p = int(num)
                    if 1 <= p <= 20:
                        return p
                return None
            if field == "finish_time":
                for pat in [r"(\d{1,2}[.:]\d{2}[.:]\d{2})", r"(\d{1,2}[.:]\d{2})"]:
                    m = re.search(pat, text.replace(",", "."))
                    if m:
                        return m.group(1).replace(".", ":")
                return ""
            return text.strip()
        except Exception:
            return "" if field in {"horse_name", "jockey_name", "trainer_name", "finish_time"} else 0

    def _validate_horse(self, h: Dict[str, Any]) -> bool:
        if not h.get("horse_name") or not re.search(r"[a-zA-ZçğıiöşüÇĞIİÖŞÜ]", h["horse_name"]):
            return False
        return True

    # --------- Page-level info ---------
    def _extract_additional_race_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        info = {
            "race_level": "Bilinmiyor",
            "race_description": "",
            "total_prize": 0.0,
            "detailed_surface_condition": "Bilinmiyor",
            "distance": 0,
            "surface": "Bilinmiyor"
        }
        try:
            # 1. Yarış Seviyesi ve Açıklama
            cfg = soup.find("h3", class_="race-config")
            if cfg:
                acik = cfg.find("a", class_="aciklamaFancy")
                if acik:
                    info["race_level"] = self._normalize_text(acik.get_text())
                full = self._normalize_text(cfg.get_text())
                if info["race_level"] and info["race_level"] in full:
                    info["race_description"] = full.replace(info["race_level"], "").strip(", ")
                else:
                    info["race_description"] = full

            # 2. Toplam Ödül
            share = soup.find("div", class_="race-share")
            if share:
                total = 0.0
                for dl in share.find_all("dl"):
                    dd = dl.find("dd")
                    if not dd:
                        continue
                    txt = self._normalize_text(dd.get_text()).lower().replace(",", ".")
                    m = re.search(r"([\d\.,]+)\s*t", txt)
                    if m:
                        try:
                            val = float(m.group(1).replace(".", "").replace(",", "."))
                            total += val
                        except Exception:
                            pass
                info["total_prize"] = round(total, 2)

            # 3. Detaylı Zemin Durumu ve Mesafe
            # conditions-race div'ini bul
            conditions_race_div = soup.find("div", class_="conditions-race")
            if conditions_race_div:
                conditions_text = self._normalize_text(conditions_race_div.get_text())
                
                # Zemin durumu - conditions-race div'inden
                if "çim" in conditions_text.lower():
                    info["surface"] = "Çim"
                elif "kum" in conditions_text.lower():
                    info["surface"] = "Kum"
                elif "sentetik" in conditions_text.lower():
                    info["surface"] = "Sentetik"
                
                # Mesafe - conditions-race div'inden veya genel metinden
                # Önce conditions-race div'ine bak
                # 1. 3 veya 4 basamaklı sayılar için pattern
                distance_match = re.search(r"(\d{3,4})\s*(?:m|metre|mt|meter)", conditions_text, re.IGNORECASE)
                if not distance_match:
                    # 2. Virgüllü sayılar için pattern (örnek: 3,3 -> 33)
                    decimal_distance_match = re.search(r"(\d+)[,.](\d+)\s*(?:m|metre|mt|meter)", conditions_text, re.IGNORECASE)
                    if decimal_distance_match:
                        try:
                            # 3,3 -> 33
                            meters = int(decimal_distance_match.group(1)) * 10 + int(decimal_distance_match.group(2))
                            distance_match = type('', (), {'group': lambda x: str(meters)})()
                        except Exception:
                            pass
                    else:
                        # 3. "Normal 3,3" gibi ifadeleri bul
                        normal_decimal_match = re.search(r"normal\s+(\d+)[,.](\d+)", conditions_text, re.IGNORECASE)
                        if normal_decimal_match:
                            try:
                                # Normal 3,3 -> 33
                                meters = int(normal_decimal_match.group(1)) * 10 + int(normal_decimal_match.group(2))
                                distance_match = type('', (), {'group': lambda x: str(meters)})()
                            except Exception:
                                pass
                        else:
                            # Eğer conditions-race div'inde yoksa, tüm sayfa metnine bak
                            page_text = soup.get_text()
                            distance_patterns = [
                                r"(\d{3,4})\s*(?:m|metre|mt|meter)",
                                r"mesafe[:\s]*(\d{3,4})",
                                r"(\d{4})\s*m\b",  # 1200 m gibi
                                r"\b(\d{3,4})(?=\s*(?:metre|m\b))"  # Lookahead ile
                            ]
                            
                            for pattern in distance_patterns:
                                distance_match = re.search(pattern, page_text, re.IGNORECASE)
                                if distance_match:
                                    break
                
                if distance_match:
                    try:
                        info["distance"] = int(distance_match.group(1))
                    except Exception:
                        pass
            else:
                # conditions-race div'i yoksa, tüm sayfa metnine bak
                page_text = soup.get_text()
                
                # Mesafe - daha esnek pattern'ler
                distance_patterns = [
                    r"(\d{3,4})\s*(?:m|metre|mt|meter)",
                    r"mesafe[:\s]*(\d{3,4})",
                    r"(\d{4})\s*m\b",  # 1200 m gibi
                    r"\b(\d{3,4})(?=\s*(?:metre|m\b))"  # Lookahead ile
                ]
                
                for pattern in distance_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        try:
                            info["distance"] = int(match.group(1))
                            break
                        except Exception:
                            pass
                
                # Zemin - daha kapsamlı
                text_lower = page_text.lower()
                if any(word in text_lower for word in ["çim", "turf", "grass", "çimen"]):
                    info["surface"] = "Çim"
                elif any(word in text_lower for word in ["kum", "dirt", "toprak", "toz"]):
                    info["surface"] = "Kum"
                elif any(word in text_lower for word in ["sentetik", "polytrack", "yapay", "all weather"]):
                    info["surface"] = "Sentetik"

            # 4. Detaylı Zemin Durumu (varsa)
            details = soup.find("div", class_="race-details")
            if details:
                dtxt = self._normalize_text(details.get_text())
                m = re.search(r"(çim|kum|sentetik).*?(:\s*[^\s,]+)", dtxt, re.IGNORECASE)
                if m:
                    info["detailed_surface_condition"] = m.group(0).strip()

        except Exception as e:
            self.logger.warning(f"Ek yarış bilgisi hatası: {e}")
        return info

    @staticmethod
    def _extract_jockey_equipment(raw_name: str) -> Tuple[List[str], str]:
        equipment = []
        for code in ["KG", "SK", "DB", "KK", "GK", "SR"]:
            if code in raw_name:
                equipment.append(code)
        m = re.search(r"^([^(]+)", raw_name)
        clean = m.group(1).strip() if m else raw_name.strip()
        return equipment, clean

    # -------------------- Output --------------------
    def display_results(self, data: List[Dict[str, Any]]) -> None:
        if not data:
            print("❌ Gösterilecek veri yok!")
            return
        print(f"\n🏁 TOPLAM {len(data)} YARIŞ BULUNDU\n")
        print("=" * 80)
        total_horses = 0
        for race in data:
            horses = race.get("horses", [])
            total_horses += len(horses)
            print(f"\n🏇 YARIŞ {race['race_number']}")
            print(f"📅 Tarih: {race['date']}")
            print(f"📏 Mesafe: {race['distance']}m")
            print(f"🏛️ Zemin: {race['surface']}")
            print(f"🐎 Atlar: {len(horses)}")
            print("-" * 40)
            for i, h in enumerate(horses[:5], 1):
                print(
                    f"{i:2d}. {h.get('horse_name','N/A'):25s} | No: {int(h.get('start_number',0)):2d} "
                    f"| Yaş: {int(h.get('horse_age',0)):2d} | Kilo: {h.get('weight',0):5.1f} "
                    f"| Oran: {h.get('odds',0):5.2f}"
                )
                if h.get("jockey_name"):
                    print(f"    Jokey: {h['jockey_name']}")
                if h.get("trainer_name"):
                    print(f"    Antrenör: {h['trainer_name']}")
                if h.get("jockey_equipment"):
                    print(f"    Donanım: {', '.join(h['jockey_equipment'])}")
        print("=" * 80)
        print(f"📊 ÖZET: {len(data)} yarış, {total_horses} at")

    def create_monthly_folder(self, date_str: str) -> str:
        """Verilen tarihe göre YYYY/MM formatında klasör oluşturur."""
        try:
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m")
            folder_path = os.path.join(year, month)
            os.makedirs(folder_path, exist_ok=True)
            return folder_path
        except ValueError as e:
            self.logger.error(f"Geçersiz tarih formatı: {date_str} - {e}")
            # Varsayılan olarak mevcut dizinde oluştur
            return "."

    def save_results_monthly(self, data: List[Dict[str, Any]], date_str: str) -> Tuple[str, Optional[str]]:
        """Veriyi aylık JSON dosyasına ekler ve ayrıca günlük CSV oluşturur."""
        if not data:
            raise ValueError("Kaydedilecek veri yok")
            
        # Aylık klasörü oluştur
        folder_path = self.create_monthly_folder(date_str)
        
        # Aylık JSON dosya adı
        date_obj = datetime.strptime(date_str, "%d/%m/%Y")
        monthly_filename = f"{date_obj.strftime('%Y-%m')}.json"
        monthly_path = os.path.join(folder_path, monthly_filename)
        
        # Günlük CSV için eski isimlendirme
        date_token = date_str.replace("/", "")
        ts = datetime.now().strftime("%H%M%S")
        csv_path = None
        
        # Aylık JSON'a yazma
        daily_entry = {
            "date": date_str,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        # Eğer aylık dosya varsa, mevcut veriyi oku
        monthly_data = []
        if os.path.exists(monthly_path):
            try:
                with open(monthly_path, "r", encoding="utf-8") as f:
                    monthly_data = json.load(f)
            except json.JSONDecodeError:
                self.logger.warning(f"Mevcut aylık dosya bozuk: {monthly_path}")
                monthly_data = []
        
        # Aynı tarihte veri varsa, üzerine yazmak yerine güncelleme yapmak daha iyi olur
        # Ancak burada basitçe ekliyoruz. İsterseniz daha sofistike bir kontrol ekleyebiliriz.
        # Şimdilik aynı tarihte veri varsa, yeni veriyle değiştiriyoruz.
        existing_dates = {entry["date"] for entry in monthly_data}
        if date_str in existing_dates:
            # Tarihi olan entry'leri filtrele
            monthly_data = [entry for entry in monthly_data if entry["date"] != date_str]
        
        monthly_data.append(daily_entry)
        
        # Aylık JSON'a yaz
        with open(monthly_path, "w", encoding="utf-8") as f:
            json.dump(monthly_data, f, ensure_ascii=False, indent=2, default=str)
            
        # Günlük CSV oluşturma (isteğe bağlı, eski davranışın korunması için)
        rows = []
        for race in data:
            for h in race.get("horses", []):
                rows.append(
                    {
                        "race_number": race["race_number"],
                        "date": race["date"],
                        "distance": race.get("distance", 0),
                        "surface": race.get("surface", ""),
                        **h,
                    }
                )
        if rows:
            df = pd.DataFrame(rows)
            daily_csv_path = os.path.join(folder_path, f"tjk_data_{date_token}_{ts}.csv")
            df.to_csv(daily_csv_path, index=False, encoding="utf-8")
            csv_path = daily_csv_path
            
        return monthly_path, csv_path

    def save_results(self, data: List[Dict[str, Any]], date_str: str) -> Tuple[str, Optional[str]]:
        """Eski save_results fonksiyonu, geriye dönük uyumluluk için korunuyor."""
        if not data:
            raise ValueError("Kaydedilecek veri yok")
        date_token = date_str.replace("/", "")
        ts = datetime.now().strftime("%H%M%S")
        json_path = f"tjk_data_{date_token}_{ts}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        csv_path = None
        rows = []
        for race in data:
            for h in race.get("horses", []):
                rows.append(
                    {
                        "race_number": race["race_number"],
                        "date": race["date"],
                        "distance": race.get("distance", 0),
                        "surface": race.get("surface", ""),
                        **h,
                    }
                )
        if rows:
            df = pd.DataFrame(rows)
            csv_path = f"tjk_data_{date_token}_{ts}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8")
        return json_path, csv_path

    # -------------------- Cleanup --------------------
    def __del__(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass


# -------------------- CLI --------------------

def main():
    print("🏇 TJK Yarış Sonuçları Çekici Başlatılıyor...")
    scraper = TJKScraper(use_selenium=True, headless=True)
    try:
        selected_date = scraper.ask_date()
        print(f"\n📡 {selected_date} için veri çekiliyor...\n")
        data = scraper.get_daily_races(selected_date)
        if not data:
            print(f"\n❌ {selected_date} için veri bulunamadı!")
            print("\n💡 Öneriler:\n- Farklı bir tarih deneyin\n- İnternet bağlantınızı kontrol edin\n- TJK sitesinin erişilebilir olduğundan emin olun")
            return
        scraper.display_results(data)
        if input("\n💾 Sonuçları kaydet (e/h): ").lower() in {"e", "evet", "y", "yes"}:
            j, c = scraper.save_results(data, selected_date)
            print(f"\n✅ JSON: {j}")
            if c:
                print(f"✅ CSV : {c}")
            print("\n✅ İşlem tamamlandı!")
        else:
            print("\n✅ Veriler kaydedilmedi.")
    except KeyboardInterrupt:
        print("\n\n⏹️ İşlem kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
    finally:
        print("\n👋 Program sonlandırılıyor...")


if __name__ == "__main__":
    main()