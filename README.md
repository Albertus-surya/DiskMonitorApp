# Disk Health Monitor (Linux Native)

Aplikasi pemantau kesehatan penyimpanan (SSD/HDD/NVMe) yang ringan dan akurat, dirancang khusus untuk sistem operasi berbasis Linux. Aplikasi ini menggunakan komunikasi low-level langsung ke kernel untuk memberikan informasi real-time mengenai kondisi drive Anda.

---

## Fitur Utama

* **Native Communication:** Menggunakan sistem IOCTL untuk berbicara langsung dengan hardware tanpa perantara berat.
* **Support USB-NVMe Bridge:** Dirancang khusus untuk mengenali chipset adapter SSD eksternal (seperti Realtek RTL9210B, JMicron JMS583, dll) yang seringkali sulit dibaca oleh aplikasi biasa.
* **Estimasi Sisa Umur:** Menghitung sisa umur operasional disk dalam hitungan hari berdasarkan pola penggunaan.
* **Antarmuka Modern:** GUI berbasis Tkinter dengan tema *Deep Sea Blue* (Dark Mode) yang nyaman di mata.
* **Informasi Detail:** Menampilkan Suhu (Celsius), Lifetime Writes (TBW), Serial Number, dan Power On Time.

---

## Persyaratan Sistem

Aplikasi ini tidak memerlukan pustaka pihak ketiga dari `pip` (seperti pandas atau matplotlib). Semua dependensi berada pada level sistem:

* **Python 3.x**
* **python3-tk** (untuk antarmuka grafis)
* **smartmontools** (sebagai pendukung pembacaan beberapa tipe bridge USB)

---

## Panduan Instalasi & Penggunaan

### Metode 1: Instalasi via Paket `.deb` (Direkomendasikan)

Gunakan metode ini jika Anda ingin aplikasi terpasang secara permanen di menu aplikasi sistem Anda.

1.  Buka terminal di folder tempat file `.deb` berada.
2.  Instal paket dengan perintah:
    ```bash
    sudo dpkg -i disk-health.deb
    ```
3.  Jika terjadi error karena dependensi yang kurang, jalankan:
    ```bash
    sudo apt-get install -f
    ```
4.  Jalankan aplikasi dari terminal:
    ```bash
    sudo disk-health
    ```

---

### Metode 2: Menjalankan Langsung via Script Python

Gunakan metode ini untuk keperluan pengembangan atau pengujian cepat tanpa instalasi permanen.

1.  **Instal Dependensi Sistem:**
    ```bash
    sudo apt update
    sudo apt install python3 python3-tk smartmontools -y
    ```
2.  **Berikan Izin Eksekusi pada File:**
    ```bash
    chmod +x main.py
    ```
3.  **Jalankan Aplikasi:**
    Wajib menggunakan `sudo` karena aplikasi harus mengakses file device di `/dev/`.
    ```bash
    sudo python3 main.py
    ```

---

## Catatan Keamanan

* **Akses Root:** Aplikasi ini membutuhkan `sudo` hanya untuk membaca status hardware di level kernel.
* **Read-Only:** Aplikasi ini **tidak akan pernah** menulis data ke disk atau mengubah konfigurasi sistem Anda. Ia hanya membaca log kesehatan (SMART log).
* **Kecocokan Hardware:** Fitur *Lifetime Writes* mungkin menampilkan `N/A` pada HDD (Hard Disk Drive) karena keterbatasan teknologi hardware lama dalam mencatat statistik penulisan.

---

## Troubleshooting

* **Pesan "WAJIB dijalankan dengan SUDO":** Ini terjadi karena file perangkat keras di `/dev/nvme*` atau `/dev/sd*` hanya bisa diakses oleh administrator.
* **Disk Tidak Muncul:** Pastikan kabel koneksi (USB/SATA) terpasang dengan baik. Gunakan perintah `lsblk` di terminal untuk memastikan disk terdeteksi oleh sistem operasi.
* **Suhu 0°C atau N/A:** Beberapa adapter USB murah tidak memiliki chip yang mendukung penerusan perintah suhu ke sistem.

---
