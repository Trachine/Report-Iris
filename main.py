import os
import sys
import shutil
import csv
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import Counter

# --- Warna ANSI ---
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"

TEMPLATE_DIR = "templates"
OUTPUT_DIR = "outputs"

# --- Shift ---
SHIFTS = {
    "3": ("Selamat Pagi", "00.00 - 08.00"),
    "1": ("Selamat Sore", "08.00 - 16.00"),
    "2": ("Selamat Malam", "16.00 - 00.00"),
}

# --- Mapping Bulan ---
BULAN_MAP = {
    "Jan": "Januari", "Feb": "Februari", "Mar": "Maret", "Apr": "April",
    "May": "Mei", "Jun": "Juni", "Jul": "Juli", "Aug": "Agustus",
    "Sep": "September", "Oct": "Oktober", "Nov": "November", "Dec": "Desember",
}

def get_default_shift():
    hour = datetime.now().hour
    if 0 <= hour < 8:
        return "3"  # Pagi
    elif 8 <= hour < 16:
        return "1"  # Sore
    else:
        return "2"  # Malam

# ---------------------- BAGIAN RAW.TXT ----------------------
def verticalize(raw):
    if not raw or raw == "-":
        return "-"
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    return "<br>\n".join(lines) + "<br>" if lines else "-"

def parse_raw_file(file_path):
    parsed_events = []
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t', quotechar='"')
        for parts in reader:
            if len(parts) <= 3:
                continue

            def get_part(idx):
                return parts[idx].strip() if len(parts) > idx else ""

            src_ip_raw = get_part(20)
            src_country_raw = get_part(21)
            dst_ip_raw = get_part(22)
            dst_port_raw = get_part(23)

            event = {
                "event_id": get_part(0),
                "analyst": get_part(1),
                "ticket_id": get_part(2),
                "event_type": get_part(3),
                "event_name": get_part(7) or get_part(4),
                "category": get_part(8),
                "magnitude": get_part(9),
                "tanggal": get_part(10),
                "waktu": get_part(11),
                "src_ip": verticalize(src_ip_raw),
                "src_country": verticalize(src_country_raw),
                "dst_ip": verticalize(dst_ip_raw),
                "dst_port": verticalize(dst_port_raw),
                "dst_asset": get_part(24),
                "query": verticalize(get_part(29) or "-"),
                "url": verticalize(get_part(28) or "-"),
            }
            parsed_events.append(event)
    return parsed_events

def clean_shift_folder(shift_key):
    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    if os.path.exists(shift_outdir):
        try:
            shutil.rmtree(shift_outdir)
        except PermissionError:
            print(f"{RED}[WARNING]{RESET} Tidak bisa hapus folder shift: {shift_outdir}")
    os.makedirs(shift_outdir, exist_ok=True)
    return shift_outdir

def write_wa(offenses, logs, shift_key, template_file):
    greeting, jam = SHIFTS[shift_key]
    tanggal = datetime.now().strftime("%d/%m/%Y")

    with open(template_file, "r", encoding="utf-8") as f:
        template = f.read()

    offenses_count = Counter(e['event_name'] for e in offenses)
    logs_count = Counter(e['event_name'] for e in logs)

    offenses_str = "\n".join(f"{i}. {name} ({count} events)" for i, (name, count) in enumerate(offenses_count.items(), 1)) or "Tidak ada event terdeteksi"
    logs_str = "\n".join(f"{i}. {name} ({count} events)" for i, (name, count) in enumerate(logs_count.items(), 1)) or "Tidak ada event terdeteksi"

    wa_text = template.replace("{salam}", greeting)\
                      .replace("{tanggal}", tanggal)\
                      .replace("{jam}", jam)\
                      .replace("{offenses}", offenses_str)\
                      .replace("{log_activity}", logs_str)

    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    out_file = os.path.join(shift_outdir, f"wa_shift{shift_key}.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(wa_text)

    print(f"{YELLOW}[INFO]{RESET} WA master tersimpan di {out_file}")

def check_template(event_name):
    filename = os.path.join(TEMPLATE_DIR, f"{event_name}.txt")
    if not os.path.exists(filename):
        print(f"{RED}[WARNING]{RESET} Template untuk '{event_name}' belum ditemukan, dilewati...")
        return False
    return True

def fill_template(template_content, event_data):
    filled_content = template_content
    for key, value in event_data.items():
        filled_content = filled_content.replace(f"{{{key}}}", str(value))
    return filled_content

def write_event_details(events, shift_key):
    shift_outdir = os.path.join(OUTPUT_DIR, f"shift{shift_key}")
    os.makedirs(shift_outdir, exist_ok=True)

    processed_event_names = set()

    for event_data in events:
        event_name = event_data["event_name"]
        if event_name in processed_event_names:
            continue

        if check_template(event_name):
            filename = os.path.join(TEMPLATE_DIR, f"{event_name}.txt")
            with open(filename, "r", encoding="utf-8") as f:
                template = f.read()

            filled_template = fill_template(template, event_data)
            ticket_id = event_data.get("ticket_id", "")
            out_file_unique = os.path.join(shift_outdir, f"{event_name}_{ticket_id}.txt")

            with open(out_file_unique, "w", encoding="utf-8") as f:
                f.write(filled_template)

            print(f"{GREEN}[OK]{RESET} File detail untuk '{event_name}' (Ticket ID: {ticket_id}) dibuat di {out_file_unique}")
            processed_event_names.add(event_name)

# ---------------------- BAGIAN RAW.XML ----------------------
def xml_to_excel(xml_file, shift_key):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    rows = []
    closed_date_sample = None

    for offense in root.findall("OffenseForm"):
        closed_date = offense.findtext("formattedClosedDate", "")
        if closed_date and not closed_date_sample:
            closed_date_sample = closed_date

        rows.append({
            "id": offense.findtext("id", ""),
            "magnitude": offense.findtext("magnitude", ""),
            "closeUser": offense.findtext("closeUser", ""),
            "formattedClosedDate": closed_date,
            "localizedCloseReason": offense.findtext("localizedCloseReason", ""),
            "deviceOrderBy": offense.findtext("deviceOrderBy", ""),
            "escapedFormattedOffenseSource": offense.findtext("escapedFormattedOffenseSource", ""),
            "formattedOffenseType": offense.findtext("formattedOffenseType", ""),
            "description": offense.findtext("description", ""),
            "severity": offense.findtext("severity", ""),
            "eventCount": offense.findtext("eventCount", ""),
            "eventDescription": offense.findtext("eventDescription", ""),
            "startTime": offense.findtext("startTime", ""),
            "endTime": offense.findtext("endTime", ""),
            "attacker": offense.findtext("attacker", ""),
            "target": offense.findtext("target", ""),
            "deviceCount": offense.findtext("deviceCount", ""),
            "targetNetwork": offense.findtext("targetNetwork", ""),
            "attackerNetwork": offense.findtext("attackerNetwork", ""),
            "usernameOrderBy": offense.findtext("usernameOrderBy", ""),
        })

    df = pd.DataFrame(rows)

    tanggal_file = "UnknownDate"
    if closed_date_sample:
        parts = closed_date_sample.split()
        if len(parts) >= 3:
            hari = parts[0].zfill(2)
            bulan = BULAN_MAP.get(parts[1], parts[1])
            tahun = parts[2]
            tanggal_file = f"{hari} {bulan} {tahun}"

    salam, jam = SHIFTS.get(shift_key, ("Shift Tidak Dikenal", ""))

    base_name = f"FollowUp & Closed Offenses List - {salam}, {jam} {tanggal_file} Shift {shift_key}.xlsx"
    output_excel = Path(base_name)
    df.to_excel(output_excel, index=False)
    print(f"{GREEN}[OK]{RESET} Excel berhasil dibuat: {output_excel}")

# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    default_shift = get_default_shift()

    print("Pilih mode:")
    print("1. Proses raw.txt (WA + Event Details)")
    print("2. Proses raw.xml (Excel Export)")
    mode = input("Mode [1/2]: ").strip()

    shift = input(f"Pilih shift (1=Sore, 2=Malam, 3=Pagi) [default={default_shift}]: ").strip() or default_shift

    if mode == "1":
        raw_file = "raw.txt"
        wa_template_file = os.path.join(TEMPLATE_DIR, "wa.txt")
        if not os.path.exists(raw_file):
            print(f"{RED}[ERROR]{RESET} raw.txt tidak ditemukan!")
            sys.exit(1)
        if not os.path.exists(wa_template_file):
            print(f"{RED}[ERROR]{RESET} Template WA '{wa_template_file}' tidak ditemukan!")
            sys.exit(1)

        clean_shift_folder(shift)
        all_events = parse_raw_file(raw_file)

        offenses = [e for e in all_events if e["event_type"].strip() == "Offensess"]
        log_activities = [e for e in all_events if e["event_type"].strip() == "Log Activity"]

        write_wa(offenses, log_activities, shift, wa_template_file)
        write_event_details(all_events, shift)

    elif mode == "2":
        xml_file = "raw.xml"
        if not os.path.exists(xml_file):
            print(f"{RED}[ERROR]{RESET} raw.xml tidak ditemukan!")
            sys.exit(1)
        xml_to_excel(xml_file, shift)

    else:
        print(f"{RED}[ERROR]{RESET} Mode tidak dikenal.")
