# Disk Health Monitor

Program monitor kesehatan disk untuk Linux dan Windows.

## Instalasi

### Linux:
```bash
sudo apt install smartmontools
pip3 install matplotlib
```

### Windows:
```cmd
pip install matplotlib
```

## Cara Menjalankan

### Linux:
```bash
sudo python3 main.py
```

### Windows:
Buka Command Prompt sebagai Administrator, lalu:
```cmd
python main.py
```

## Fitur

- Monitor kesehatan disk real-time
- Deteksi SSD (NVMe & SATA) dan HDD
- Grafik history kesehatan
- Monitoring suhu (Linux)
- Auto-logging ke `health_log.csv`

## Catatan

- Linux: Harus pakai `sudo` untuk akses disk
- Windows: Jalankan sebagai Administrator
- Windows: Suhu tidak tersedia (keterbatasan sistem)