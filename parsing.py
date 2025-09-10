import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path

# Mapping singkatan bulan ke nama lengkap
BULAN_MAP = {
    "Jan": "Januari",
    "Feb": "Februari",
    "Mar": "Maret",
    "Apr": "April",
    "May": "Mei",
    "Jun": "Juni",
    "Jul": "Juli",
    "Aug": "Agustus",
    "Sep": "September",
    "Oct": "Oktober",
    "Nov": "November",
    "Dec": "Desember",
}

# Mapping shift
SHIFTS = {
    "3": ("Selamat Pagi", "00.00 - 08.00"),
    "1": ("Selamat Sore", "08.00 - 16.00"),
    "2": ("Selamat Malam", "16.00 - 00.00"),
}


def xml_to_excel(xml_file, shift_key):
    # Parse file XML
    tree = ET.parse(xml_file)
    root = tree.getroot()

    rows = []
    closed_date_sample = None  # simpan salah satu tanggal buat nama file

    # Loop tiap OffenseForm
    for offense in root.findall("OffenseForm"):
        closed_date = offense.findtext("formattedClosedDate", "")
        if closed_date and not closed_date_sample:
            closed_date_sample = closed_date  # ambil tanggal pertama

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

    # Buat DataFrame
    df = pd.DataFrame(rows)

    # Ambil tanggal untuk nama file
    tanggal_file = "UnknownDate"
    if closed_date_sample:
        # contoh format: "5 Sep 2025 09.41.39"
        parts = closed_date_sample.split()
        if len(parts) >= 3:
            hari = parts[0].zfill(2)  # tambahkan leading zero
            bulan = BULAN_MAP.get(parts[1], parts[1])
            tahun = parts[2]
            tanggal_file = f"{hari} {bulan} {tahun}"

    # Ambil shift info
    salam, jam = SHIFTS.get(shift_key, ("Shift Tidak Dikenal", ""))

    # Buat nama file sesuai format
    base_name = f"FollowUp & Closed Offenses List - {salam}, {jam} {tanggal_file} Shift {shift_input}.xlsx"
    output_excel = Path(base_name)

    # Simpan ke Excel
    df.to_excel(output_excel, index=False)
    print(f"Excel berhasil dibuat: {output_excel}")


if __name__ == "__main__":
    xml_file = "raw.xml"  # file input XML
    shift_input = input("Masukkan Shift (1=Sore, 2=Malam, 3=Pagi) [default=1]: ").strip()

    # Kalau kosong, default ke shift 1 (Sore)
    if not shift_input:
        shift_input = "1"

    xml_to_excel(xml_file, shift_input)
