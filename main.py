import sys
import os
import platform
import subprocess
import threading
import time
import re
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

# Konfigurasi Global
LOG_FILE = "health_log.csv"
IS_WINDOWS = platform.system() == "Windows"

class DiskMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Disk Health Monitor - Cross Platform")
        self.root.geometry("800x600")
        
        self.disks_data = []
        self.running = True

        self.setup_ui()
        
        # Mulai thread monitoring
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        btn_refresh = ttk.Button(main_frame, text="Refresh Data", command=self.refresh_data)
        btn_refresh.pack(anchor="ne", pady=5)

        # Label info jika kosong
        self.lbl_info = ttk.Label(main_frame, text="Memuat data...", foreground="gray")
        self.lbl_info.pack(pady=5)

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def monitoring_loop(self):
        while self.running:
            # Refresh otomatis pertama kali, lalu diam (bisa diaktifkan loopnya jika mau)
            time.sleep(1) 
            self.refresh_data()
            # Ubah time.sleep menjadi lama agar tidak refresh terus menerus di GUI thread main
            time.sleep(300) 

    def refresh_data(self):
        # Ambil data di thread terpisah agar GUI tidak macet, tapi untuk simpel kita panggil langsung
        # (Idealnya pakai after/queue, tapi ini cukup untuk project sederhana)
        self.disks_data = get_disk_info()
        
        # Update GUI harus di main thread
        self.root.after(0, self.update_gui_list)

    def update_gui_list(self):
        # Bersihkan tampilan lama
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.disks_data:
            self.lbl_info.config(text="Tidak ada disk terdeteksi.\nCoba jalankan VS Code sebagai 'Run as Administrator'")
        else:
            self.lbl_info.config(text=f"Ditemukan {len(self.disks_data)} Disk")

        # Tampilkan data ke UI
        for disk in self.disks_data:
            self.create_disk_card(disk)

    def create_disk_card(self, disk):
        card = ttk.LabelFrame(self.scrollable_frame, text=f"{disk['model']}", padding="10")
        card.pack(fill="x", pady=5, padx=5)

        # Tentukan warna status
        hp = disk['health_percent']
        status_color = "#4CAF50" if hp >= 88 else "#FFC107" if hp >= 70 else "#F44336" # Hijau, Kuning, Merah
        
        # Baris 1: Tipe dan Path
        frame_top = ttk.Frame(card)
        frame_top.pack(fill="x")
        ttk.Label(frame_top, text=f"Type: {disk['type']} | Path: {disk['device']}").pack(side="left")
        
        # Baris 2: Indikator Kesehatan Besar
        frame_health = tk.Frame(card, bg=status_color, pady=5, padx=10)
        frame_health.pack(fill="x", pady=5)
        
        tk.Label(frame_health, text=f"HEALTH: {hp}%", bg=status_color, fg="white", font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(frame_health, text=f"Status: {disk['status']}", bg=status_color, fg="white").pack(side="right")

        # Baris 3: Info Tambahan
        ttk.Label(card, text=f"Suhu: {disk['temp']}").pack(anchor="w")

        # Tombol Grafik
        btn_graph = ttk.Button(card, text="Lihat Grafik History", command=lambda d=disk: self.show_graph(d))
        btn_graph.pack(anchor="e", pady=5)

        self.save_log(disk)

    def save_log(self, disk):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(LOG_FILE, "a") as f:
                temp_val = str(disk['temp']).replace(" °C", "")
                f.write(f"{timestamp},{disk['model']},{disk['health_percent']},{temp_val}\n")
        except Exception as e:
            print(f"Gagal simpan log: {e}")

    def show_graph(self, disk):
        graph_window = tk.Toplevel(self.root)
        graph_window.title(f"History: {disk['model']}")
        graph_window.geometry("600x400")

        times, healths = [], []
        
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as f:
                    for line in f:
                        parts = line.strip().split(",")
                        # Filter berdasarkan nama model
                        if len(parts) >= 3 and parts[1] == disk['model']:
                            times.append(parts[0]) # Timestamp
                            healths.append(int(parts[2]))
            except:
                pass

        # Gambar Grafik
        fig, ax1 = plt.subplots(figsize=(5, 4))
        ax1.set_title(f"Kesehatan: {disk['model']}")
        ax1.set_xlabel('Data Point (Waktu)')
        ax1.set_ylabel('Health (%)', color='green')
        
        # Plot data (ambil 20 data terakhir biar rapi)
        ax1.plot(healths[-20:], color='green', marker='o', linestyle='-')
        ax1.grid(True, linestyle='--', alpha=0.7)

        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# ==========================================
# LOGIKA PENGAMBILAN DATA (UPDATED)
# ==========================================

def run_command(cmd):
    try:
        # Menjalankan command dan menangkap outputnya
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error Command: {e}")
        return ""

def get_disk_info():
    disks = []
    print(f"Mendeteksi Disk pada OS: {platform.system()}")

    if IS_WINDOWS:
        # --- TEKNIK BARU: POWERSHELL (Lebih Stabil di Windows 10/11) ---
        # Perintah ini mengambil: Nama Friendly, Tipe Media (SSD/HDD), dan Status Kesehatan
        ps_cmd = 'powershell "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus | ConvertTo-Csv -NoTypeInformation"'
        
        output = run_command(ps_cmd)
        print("Raw Output Windows:\n", output) # Debugging: Tampilkan output mentah

        lines = output.splitlines()
        for line in lines:
            # Skip baris header atau kosong
            if "FriendlyName" in line or not line.strip(): 
                continue
            
            # Parsing CSV sederhana dari PowerShell
            # Contoh format: "Samsung SSD 970","SSD","Healthy"
            parts = line.split(",")
            
            if len(parts) >= 3:
                # Bersihkan tanda kutip (")
                model = parts[0].replace('"', '')
                media_type = parts[1].replace('"', '')
                status_raw = parts[2].replace('"', '')

                # Konversi Status ke Persen (Simulasi Windows)
                health_percent = 100 if status_raw == "Healthy" else 40
                
                disks.append({
                    "device": "WindowsDisk",
                    "model": model,
                    "type": media_type,
                    "status": status_raw,
                    "health_percent": health_percent,
                    "temp": "N/A" # Windows native susah baca suhu tanpa admin tools
                })

    else:
        # --- LOGIKA LINUX (Tetap Pakai Smartctl) ---
        scan_output = run_command("sudo smartctl --scan")
        print("Scan Linux:", scan_output)
        
        for line in scan_output.splitlines():
            match = re.search(r"(/dev/\w+)", line)
            if match:
                device_path = match.group(1)
                disk_data = analyze_linux_disk(device_path)
                if disk_data:
                    disks.append(disk_data)
                    
    return disks

def analyze_linux_disk(device_path):
    output = run_command(f"sudo smartctl -a {device_path}")
    
    # Ambil Model
    model = "Unknown Disk"
    model_match = re.search(r"(?:Device Model|Model Number):\s+(.*)", output)
    if model_match: model = model_match.group(1).strip()

    # Ambil Suhu
    temp = "N/A"
    temp_match = re.search(r"Temperature_Celsius.*?\s+(\d+)", output)
    if temp_match: temp = f"{temp_match.group(1)} °C"

    # Deteksi Tipe & Hitung Health
    is_nvme = "NVMe" in output or "nvm" in device_path
    health = 100
    
    if is_nvme:
        used_match = re.search(r"Percentage Used:\s+(\d+)%", output)
        if used_match: health = 100 - int(used_match.group(1))
        dtype = "NVMe SSD"
    else:
        realloc = 0
        pending = 0
        re_match = re.search(r"Reallocated_Sector_Ct.*?\s+(\d+)$", output, re.MULTILINE)
        pen_match = re.search(r"Current_Pending_Sector.*?\s+(\d+)$", output, re.MULTILINE)
        
        if re_match: realloc = int(re_match.group(1))
        if pen_match: pending = int(pen_match.group(1))
        
        health = 100 - (realloc * 5) - (pending * 10)
        dtype = "SATA/HDD"

    if health < 0: health = 0

    return {
        "device": device_path,
        "model": model,
        "type": dtype,
        "status": "PASSED" if health > 50 else "FAIL",
        "health_percent": health,
        "temp": temp
    }

if __name__ == "__main__":
    # Cek root di Linux
    if not IS_WINDOWS and os.geteuid() != 0:
        print("PERINGATAN: Di Linux, jalankan script ini dengan 'sudo'!")
    
    root = tk.Tk()
    # Atur tema biar agak modern
    style = ttk.Style()
    style.theme_use('clam') 
    
    app = DiskMonitorApp(root)
    root.mainloop()