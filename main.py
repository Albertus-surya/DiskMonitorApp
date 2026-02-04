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
            time.sleep(1) 
            self.refresh_data()
            time.sleep(300) 

    def refresh_data(self):
        self.disks_data = get_disk_info()
        self.root.after(0, self.update_gui_list)

    def update_gui_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.disks_data:
            error_msg = "Tidak ada disk terdeteksi.\n"
            if IS_WINDOWS:
                error_msg += "Coba jalankan sebagai Administrator"
            else:
                error_msg += "Pastikan smartmontools sudah terinstall:\nsudo apt install smartmontools"
            self.lbl_info.config(text=error_msg)
        else:
            self.lbl_info.config(text=f"Ditemukan {len(self.disks_data)} Disk")

        for disk in self.disks_data:
            self.create_disk_card(disk)

    def create_disk_card(self, disk):
        card = ttk.LabelFrame(self.scrollable_frame, text=f"{disk['model']}", padding="10")
        card.pack(fill="x", pady=5, padx=5)

        hp = disk['health_percent']
        status_color = "#4CAF50" if hp >= 88 else "#FFC107" if hp >= 70 else "#F44336"
        
        frame_top = ttk.Frame(card)
        frame_top.pack(fill="x")
        ttk.Label(frame_top, text=f"Type: {disk['type']} | Path: {disk['device']}").pack(side="left")
        
        frame_health = tk.Frame(card, bg=status_color, pady=5, padx=10)
        frame_health.pack(fill="x", pady=5)
        
        tk.Label(frame_health, text=f"HEALTH: {hp}%", bg=status_color, fg="white", font=("Arial", 10, "bold")).pack(side="left")
        tk.Label(frame_health, text=f"Status: {disk['status']}", bg=status_color, fg="white").pack(side="right")

        ttk.Label(card, text=f"Suhu: {disk['temp']}").pack(anchor="w")

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
                        if len(parts) >= 3 and parts[1] == disk['model']:
                            times.append(parts[0])
                            healths.append(int(parts[2]))
            except:
                pass

        fig, ax1 = plt.subplots(figsize=(5, 4))
        ax1.set_title(f"Kesehatan: {disk['model']}")
        ax1.set_xlabel('Data Point (Waktu)')
        ax1.set_ylabel('Health (%)', color='green')
        
        ax1.plot(healths[-20:], color='green', marker='o', linestyle='-')
        ax1.grid(True, linestyle='--', alpha=0.7)

        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# ==========================================
# LOGIKA PENGAMBILAN DATA
# ==========================================

def run_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        print(f"Error Command: {e}")
        return "", str(e)

def check_smartctl_installed():
    stdout, stderr = run_command("smartctl --version")
    return "smartctl" in stdout.lower()

def get_disk_info():
    disks = []
    print(f"Mendeteksi Disk pada OS: {platform.system()}")

    if IS_WINDOWS:
        ps_cmd = 'powershell "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus | ConvertTo-Csv -NoTypeInformation"'
        
        output, error = run_command(ps_cmd)
        print("Raw Output Windows:\n", output)

        lines = output.splitlines()
        for line in lines:
            if "FriendlyName" in line or not line.strip(): 
                continue
            
            parts = line.split(",")
            
            if len(parts) >= 3:
                model = parts[0].replace('"', '')
                media_type = parts[1].replace('"', '')
                status_raw = parts[2].replace('"', '')

                health_percent = 100 if status_raw == "Healthy" else 40
                
                disks.append({
                    "device": "WindowsDisk",
                    "model": model,
                    "type": media_type,
                    "status": status_raw,
                    "health_percent": health_percent,
                    "temp": "N/A"
                })

    else:
        # LINUX - Cek smartctl terinstall
        if not check_smartctl_installed():
            print("ERROR: smartctl tidak ditemukan!")
            print("Install dengan: sudo apt install smartmontools")
            return []
        
        # Scan semua disk
        scan_output, scan_error = run_command("smartctl --scan")
        print("Scan Linux:", scan_output)
        
        if not scan_output:
            # Fallback: coba scan manual common devices
            print("Mencoba fallback scan...")
            common_devices = ["/dev/sda", "/dev/sdb", "/dev/nvme0n1", "/dev/nvme1n1"]
            for device in common_devices:
                if os.path.exists(device):
                    print(f"Menganalisa {device}...")
                    disk_data = analyze_linux_disk(device)
                    if disk_data:
                        disks.append(disk_data)
        else:
            for line in scan_output.splitlines():
                match = re.search(r"(/dev/\w+)", line)
                if match:
                    device_path = match.group(1)
                    disk_data = analyze_linux_disk(device_path)
                    if disk_data:
                        disks.append(disk_data)
                    
    return disks

def analyze_linux_disk(device_path):
    output, error = run_command(f"smartctl -a {device_path}")
    
    if not output or "Unable to detect" in output:
        print(f"Gagal baca {device_path}: {error}")
        return None
    
    # Ambil Model
    model = "Unknown Disk"
    model_match = re.search(r"(?:Device Model|Model Number|Model Family):\s+(.*)", output)
    if model_match: 
        model = model_match.group(1).strip()

    # Ambil Suhu
    temp = "N/A"
    temp_match = re.search(r"Temperature_Celsius.*?\s+(\d+)", output)
    if temp_match: 
        temp = f"{temp_match.group(1)} °C"
    else:
        # Coba format NVMe
        temp_match_nvme = re.search(r"Temperature:\s+(\d+)\s+Celsius", output)
        if temp_match_nvme:
            temp = f"{temp_match_nvme.group(1)} °C"

    # Deteksi Tipe & Hitung Health
    is_nvme = "NVMe" in output or "nvme" in device_path
    health = 100
    
    if is_nvme:
        used_match = re.search(r"Percentage Used:\s+(\d+)%", output)
        if used_match: 
            health = 100 - int(used_match.group(1))
        dtype = "NVMe SSD"
    else:
        realloc = 0
        pending = 0
        re_match = re.search(r"Reallocated_Sector_Ct.*?\s+(\d+)$", output, re.MULTILINE)
        pen_match = re.search(r"Current_Pending_Sector.*?\s+(\d+)$", output, re.MULTILINE)
        
        if re_match: realloc = int(re_match.group(1))
        if pen_match: pending = int(pen_match.group(1))
        
        health = 100 - (realloc * 5) - (pending * 10)
        
        # Deteksi SSD vs HDD
        if "SSD" in model or "Solid State" in output:
            dtype = "SATA SSD"
        else:
            dtype = "SATA HDD"

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
        print("Contoh: sudo python3 disk_monitor.py")
        sys.exit(1)
    
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('clam') 
    
    app = DiskMonitorApp(root)
    root.mainloop()