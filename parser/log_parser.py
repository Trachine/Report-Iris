import os
from utils.logger import log_warning

# --- Fungsi membaca multiline ---
def read_raw_multiline_manual(file_path):
    """
    Membaca file raw.txt yang memiliki field multiline dalam tanda kutip.
    Menggabungkan multiline menjadi satu record utuh.
    """
    records = []
    with open(file_path, "r", encoding="utf-8") as f:
        buffer = ""
        inside_quotes = False
        for line in f:
            line = line.rstrip('\n')
            quote_count = line.count('"')

            if not inside_quotes:
                buffer = line
                if quote_count % 2 == 1:  # mulai multiline
                    inside_quotes = True
                else:
                    records.append(buffer)
                    buffer = ""
            else:
                buffer += "\n" + line
                if quote_count % 2 == 1:  # tutup multiline
                    inside_quotes = False
                    records.append(buffer)
                    buffer = ""

        if buffer and not inside_quotes:
            records.append(buffer)
    return records

# --- Fungsi parsing file raw ---
def parse_raw_file(file_path):
    """
    Mengubah raw.txt menjadi list of dictionaries.
    Event name panjang dan multiline tetap dipertahankan.
    """
    records = read_raw_multiline_manual(file_path)
    parsed_events = []

    for record in records:
        parts = record.split('\t')

        # Minimal kolom yang penting
        if len(parts) < 8:
            print(f"[WARNING] Baris terlalu pendek, dilewati: {record[:50]}...")
            continue

        event = {
            "event_id": parts[0].strip(),
            "analyst": parts[1].strip() if len(parts) > 1 else "",
            "ticket_id": parts[2].strip() if len(parts) > 2 else "",
            "event_type": parts[3].strip() if len(parts) > 3 else "",
            "event_name": parts[7].strip() if len(parts) > 7 else "",
            "category": parts[8].strip() if len(parts) > 8 else "",
            "magnitude": parts[9].strip() if len(parts) > 9 else "",
            "tanggal": parts[10].strip() if len(parts) > 10 else "",
            "waktu": parts[11].strip() if len(parts) > 11 else "",
            "src_ip": parts[20].strip().replace('\n', ', ') if len(parts) > 20 else "",
            "src_country": parts[21].strip().replace('\n', ', ') if len(parts) > 21 else "",
            "dst_ip": parts[22].strip().replace('\n', ', ') if len(parts) > 22 else "",
            "dst_port": parts[23].strip() if len(parts) > 23 else "",
            "dst_asset": parts[24].strip() if len(parts) > 24 else "",
            "query": parts[27].strip() if len(parts) > 27 else "",
        }

        parsed_events.append(event)

    return parsed_events
