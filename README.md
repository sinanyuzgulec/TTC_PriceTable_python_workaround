# Tamriel Trade Centre (TTC) Price Table Auto-Sync

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS%20%7C%20Steam%20Deck-orange.svg)]()
[![ESO Compatible](https://img.shields.io/badge/ESO-AddOn%20Companion-gold.svg)](https://www.esoui.com/downloads/info1245-TamrielTradeCentre.html)

A lightweight, cross-platform automated updater for **Tamriel Trade Centre (TTC)** price table data in *The Elder Scrolls Online*.

Designed especially for **Linux (Proton / Steam Deck / Flatpak / Lutris)** and **macOS (Apple Silicon & Intel)** users who cannot conveniently run the official Windows `.NET Client.exe`, as well as **Windows** users looking for a clean, zero-bloat automated sync tool without running background `.NET` client executables.

---

## 🌟 Features

- **Cross-Platform**: Seamlessly works on **Linux** (native / Proton / Steam Deck), **Windows 10/11**, and **macOS** (including upcoming Apple Silicon support).
- **Auto-Detection**: Automatically detects your ESO AddOns directory (`Elder Scrolls Online/live/AddOns/TamrielTradeCentre`):
  - **Linux / Steam Deck**: Automatically scans Steam Proton compatdata (`306130`), Flatpak Steam, custom Steam libraries (`libraryfolders.vdf`), Lutris, Bottles, and Heroic prefixes.
  - **Windows**: Resolves true Documents directory (including OneDrive redirection and relocated user folders).
  - **macOS**: Resolves native Documents folder and Wine/CrossOver/Whisky prefixes.
- **Automated 12-Hour Background Updates**:
  - **Linux**: Creates and manages native `systemd --user` timer & service (survives reboots, zero root permissions needed, no GUI interruption).
  - **Windows**: Installs Windows Task Scheduler task using `pythonw.exe` (runs silently in the background without terminal flashing).
  - **macOS**: Installs user `launchd` LaunchAgent daemon.
  - **Daemon mode**: Optional built-in loop mode (`--daemon`) for containers, screen, or tmux.
- **Zero Third-Party Dependencies**: Built exclusively with Python standard library (`urllib`, `zipfile`, `pathlib`, `subprocess`). No `pip install` required!
- **Safe & Atomic Extraction**: Uses safe temporary-file extraction to prevent game crashes or file corruption if ESO is running during update.
- **Strict Security & Lua Whitelisting**: Validates ZIP magic bytes upon download and strictly extracts ONLY `.lua` data files. Any foreign, executable (`.exe`, `.dll`), script (`.bat`, `.sh`), or non-lua files are automatically blocked.
- **Megaserver Selection**: Supports **EU**, **NA**, or **Both** megaservers.
- **Detailed Status & History**: View file timestamps, age in hours, sync status, and scheduler state at a glance.
- **100% Free & Open Source**: MIT Licensed.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or newer (`python3` on Linux/macOS, `python` on Windows).

### 1. Clone or Download the Repository
```bash
git clone https://github.com/sinanyuzgulec/TTC_PriceTable_python_workaround.git
cd TTC_PriceTable_python_workaround
```

### 2. Check Detection Status
```bash
python3 main.py --status
```
*(On Windows, run `python main.py --status`)*

You will see your operating system, detected ESO AddOns path, current PriceTable file age, and scheduler status.

### 3. Immediate Sync (Run Once)
```bash
python3 main.py --sync
```
*(Or run `./sync_now.sh` on Linux/macOS, or double-click `sync_now.bat` on Windows)*

---

## ⏱️ Enable Automatic 12-Hour Sync

Set up the background scheduler with a single command:

### Linux / Steam Deck / macOS
```bash
python3 main.py --install-service
```
*(Or execute `./setup_service.sh`)*

- On **Linux**, this enables a `systemd --user` timer (`ttc-sync.timer`) that updates your price table every 12 hours automatically.
- Check timer status anytime with:
  ```bash
  systemctl --user status ttc-sync.timer
  ```

### Windows
```cmd
python main.py --install-service
```
*(Or double-click `setup_service.bat`)*

- This registers a task in **Windows Task Scheduler** (`TTC_PriceTable_Sync`) set to repeat every 12 hours silently in the background.

### Uninstall Scheduler
To stop and remove the background task:
```bash
python3 main.py --uninstall-service
```

---

## ⚙️ CLI Options & Configuration

```text
usage: main.py [-h] [--sync] [--status] [--daemon] [--install-service]
               [--uninstall-service] [--server {eu,na,both}] [--path PATH]
               [--interval INTERVAL] [--log-file LOG_FILE]

Tamriel Trade Centre (TTC) Price Table Auto-Sync for Elder Scrolls Online

options:
  -h, --help            Show this help message and exit
  --sync, --once        Download & update price table immediately once and exit.
  --status              Show current installation, addon paths, file age, and scheduler status.
  --daemon              Run in continuous background loop (every --interval hours).
  --install-service     Install automated OS scheduler (systemd timer on Linux, Task Scheduler on Windows, launchd on macOS).
  --uninstall-service   Remove automated OS scheduler.
  --server {eu,na,both} Select TTC megaserver (eu, na, or both). Default: eu.
  --path PATH           Specify custom path to ESO TamrielTradeCentre folder.
  --interval INTERVAL   Set sync interval in hours (default: 12).
  --log-file LOG_FILE   Path to write log records (default: ttc_sync.log).
```

### Examples

- **Switch to North America (NA) Megaserver:**
  ```bash
  python3 main.py --server na --sync
  ```

- **Update both EU and NA tables:**
  ```bash
  python3 main.py --server both --sync
  ```

- **Specify a custom path:**
  ```bash
  python3 main.py --path "/custom/path/to/AddOns/TamrielTradeCentre" --sync
  ```

- **Run in persistent daemon mode (e.g. inside tmux/docker):**
  ```bash
  python3 main.py --daemon --interval 12
  ```

---

## 🇹🇷 Türkçe Kullanım Kılavuzu (Turkish Guide)

Elder Scrolls Online için **Tamriel Trade Centre (TTC)** fiyat tablosu güncelleyicisi.

Linux (Proton / Steam Deck), macOS (Apple Silicon & Intel) ve Windows üzerinde TTC `Client.exe` çalıştırmaya gerek kalmadan fiyat tablosunu (`PriceTableEU.lua` / `PriceTableNA.lua` ve `ItemLookUpTable_*.lua`) otomatik olarak indirir ve AddOns klasörüne çıkartır.

### Kurulum ve Çalıştırma:

1. **Durumu Kontrol Edin:**
   ```bash
   python3 main.py --status
   ```
   Sisteminizdeki ESO AddOn klasörünü otomatik olarak bulacaktır.

2. **Hemen Güncelleyin:**
   ```bash
   python3 main.py --sync
   ```
   *(Veya Linux'ta `./sync_now.sh`, Windows'ta `sync_now.bat` çalıştırın)*

3. **12 Saatte Bir Otomatik Görev Başlatma:**
   ```bash
   python3 main.py --install-service
   ```
   *(Veya Linux'ta `./setup_service.sh`, Windows'ta `setup_service.bat`)*
   - **Linux**: Arka planda `systemd --user` zamanlayıcısı kurar, bilgisayar yeniden başlasa dahi 12 saatte bir kendini sessizce günceller.
   - **Windows**: Windows Görev Zamanlayıcısına ekler ve ekranınıza siyah konsol penceresi çıkarmadan `pythonw.exe` ile arka planda çalışır.

4. **Otomatik Görevi Kaldırmak İçin:**
   ```bash
   python3 main.py --uninstall-service
   ```

> **Yasal Uyarı & Sorumluluk Reddi:**
> - Bu depo ve geliştiricileri, [https://eu.tamrieltradecentre.com/pc/Trade/WebClient](https://eu.tamrieltradecentre.com/pc/Trade/WebClient) (TTC WebClient) tarafında veya TTC'nin resmi servislerinde meydana gelebilecek aksaklıklardan, veri uyuşmazlıklarından ya da hesap durumlarından **kesinlikle sorumlu değildir**.
> - **Güvenlik Koruması:** Bu araç yalnızca geçerli ZIP arşivlerini indirir ve içerisinden **yalnızca `.lua` uzantılı veri dosyalarını** çıkarır. ZIP içinde yer alabilecek `.exe`, `.bat`, `.sh` veya yabancı hiçbir dosya asla sisteme çıkarılmaz, otomatik olarak engellenir.

---

## 🙏 Respect & Attribution to Tamriel Trade Centre (TTC)

This project is a community-created open-source companion tool created to assist Linux, Steam Deck, macOS, and lightweight Windows players in keeping their local TTC addon price tables up to date.

We extend our deep gratitude, highest respect, and credit to the creators, developers, and maintainers of **Tamriel Trade Centre**:

> ### About Tamriel Trade Centre
> *"Tamriel Trade Centre is a fan created site for Elder Scrolls Online Tamriel Unlimited ([ESO Official site](http://www.elderscrollsonline.com/))*
> 
> *Since ZoS is not planning on implementing a global auction house in the near future, I created this site hoping to simplify the trading process for the community. You can think of this site as an addon driven trade forum. Unlike other forum you can actually post "item" instead of threads and there is an addon + client suite to do this automatically for you.*
> 
> *You can find us on [Facebook](https://www.facebook.com/tamrieltradecentre/) or [ESOUI](http://www.esoui.com/downloads/info1245-TamrielTradeCentre.html)*
> 
> [About](https://eu.tamrieltradecentre.com/About) | [Help](https://eu.tamrieltradecentre.com/help) | [Contact us](https://eu.tamrieltradecentre.com/Contact) | [Terms of Service](https://eu.tamrieltradecentre.com/TermsOfService) | [Privacy Policy](https://eu.tamrieltradecentre.com/PrivacyPolicy)
> 
> **© 2015-2026 TTC GAMING INC. All rights reserved.**

### Legal Disclaimers
- *Tamriel Trade Centre was created using content and materials from The Elder Scrolls® Online: Tamriel Unlimited™ © ZeniMax® Online Studios, LLC or its licensors. This site and this project are not affiliated with ZeniMax Online Studios, and ZeniMax Online Studios is not responsible for any of the content on, or the privacy policy of this site.*
- **TTC WebClient & Service Disclaimer:** *This repository and its maintainers are strictly NOT responsible for any issues, outages, data discrepancies, account-related actions, or errors that may occur on or in connection with the Tamriel Trade Centre WebClient ([https://eu.tamrieltradecentre.com/pc/Trade/WebClient](https://eu.tamrieltradecentre.com/pc/Trade/WebClient)) or official TTC services. This tool only downloads publicly available price table zip archives and extracts local `.lua` tables.*
- **Security & Strict Whitelisting:** *For user safety, this tool exclusively accepts ZIP archives and strictly extracts ONLY `.lua` files (`PriceTable*.lua`, `ItemLookUpTable_*.lua`). Any non-lua files, executables, scripts, or foreign extensions inside archives are blocked automatically.*
- *Windows®, Xbox® and their logos are registered trademarks of Microsoft Corporation.*
- *Sony PlayStation® and its logo are registered trademarks of Sony Inc.*

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - free and open source for everyone.
