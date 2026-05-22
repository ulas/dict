#!/usr/pkg/bin/python
import os
import html
import sys
import socket
import re
from urllib.parse import parse_qs, quote_plus

# --- DICT SUNUCU AYARLARI ---
DICT_HOST = "dict.dict.org"
DICT_PORT = 2628  # Standart DICTD portu

def send_dict_command(command):
    """
    DICTD sunucusuna TCP soketi üzerinden doğrudan bağlanır,
    komutu gönderir ve dönen yanıtı RFC 2229 standartlarına göre okur.
    Hiçbir harici binary programa veya 'dict' komutuna ihtiyaç duymaz.
    """
    try:
        # Soket bağlantısı oluşturma (Bağlantı zaman aşımı: 10 saniye)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10.0)
        s.connect((DICT_HOST, DICT_PORT))
        
        # Sunucunun selamlama (banner) yanıtını oku
        initial_resp = s.recv(4096).decode('utf-8', errors='ignore')
        
        # Komutu gönder (Komutların sonu \r\n ile bitmelidir)
        s.sendall(f"{command}\r\n".encode('utf-8'))
        
        # Sunucudan gelen yanıtı biriktir
        buffer = []
        while True:
            data = s.recv(8192).decode('utf-8', errors='ignore')
            if not data:
                break
            buffer.append(data)
            
            # DICT protokolünde ana yanıtların bittiğini gösteren durum kodları ve bitiş şablonları
            full_text = "".join(buffer)
            if (re.search(r'^\d{3} .*\r\n$', data) and len(buffer) > 1) or \
               data.endswith("\n250 ok\r\n") or \
               data.endswith("\n552 no match\r\n") or \
               data.endswith("\n550 invalid database\r\n"):
                break
                
        # Bağlantıyı güvenli bir şekilde kapat ve çıkış komutu gönder
        try:
            s.sendall(b"QUIT\r\n")
        except:
            pass
        s.close()
        
        return "".join(buffer), 0
    except Exception as e:
        return f"Sunucuya bağlanırken hata oluştu: {str(e)}", 1

def clean_query(q):
    """Giriş metnini temizler"""
    if not q:
        return ""
    q = q.strip()
    q = re.sub(r'\s+', ' ', q)
    return q

def process_dict_output(output, error_code, current_db="*", current_strat=""):
    """
    Gelen DICTD ham metin çıktısını işler. Eşleşen kelimeleri veya tanımları
    kuran.php temasına uygun tıklanabilir HTML linklerine dönüştürür.
    """
    if error_code != 0:
        return f'<div class="results-box" style="color: #aa0000;"><b>Hata: {html.escape(output)}</b></div>'
        
    # Eğer sunucu 552 (Eşleşme bulunamadı) kodu döndüyse
    if output.startswith("552") or "no match" in output.lower():
        return f'<div class="results-box"><pre>Aranan kelimeye ait bir sonuç bulunamadı.</pre></div>'

    # Benzer Kelimeleri Listeleme Modu (Match)
    if current_strat and current_strat != "definitions":
        lines = output.split('\n')
        processed_lines = []
        for line in lines:
            # DICT sunucusu eşleşmeleri "veritabanı_adı kelime" formatında (152 kodu altında) döndürür
            match = re.match(r"^([^\s]+)\s+\"([^\"]+)\"", line.strip())
            if match:
                db_code = match.group(1)
                matched_word = match.group(2)
                link = f'<a class="dict-link" href="sozluk.py?q={quote_plus(matched_word)}&d={quote_plus(db_code)}&s=definitions">"{matched_word}"</a>'
                processed_lines.append(f'<span style="color:#777;">[{db_code}]</span> {link}')
            elif not line.startswith("152") and not line.startswith("250") and line.strip() and line.strip() != ".":
                parts = line.strip().split(' ', 1)
                if len(parts) > 1:
                    link = f'<a class="dict-link" href="sozluk.py?q={quote_plus(parts[1])}&d={quote_plus(current_db)}&s=definitions">"{parts[1]}"</a>'
                    processed_lines.append(f'<span style="color:#777;">[{parts[0]}]</span> {link}')
                else:
                    processed_lines.append(html.escape(line))
        
        if not processed_lines:
            return f'<div class="results-box"><pre>Aranan kritere uygun benzer kelime listesi boş.</pre></div>'
            
        output_html = "<br>".join(processed_lines)
        return f'<div class="results-box"><pre>{output_html}</pre></div>'

    # Normal Tanım Modu (Definitions - Sunucu Kodu: 151)
    def format_headers(match):
        db_desc = match.group(2)
        return f'\n\n<div class="db-title"><b>Kaynak: {db_desc}</b></div>\n'
        
    cleaned_output = re.sub(r'151\s+"[^"]+"\s+([^\s]+)\s+"([^"]+)"', format_headers, output)
    
    # DICT protokol satır numaralarını ve kapanış noktalarını temizle
    cleaned_output = re.sub(r'^\d{3} .*\r?\n', '', cleaned_output)
    cleaned_output = re.sub(r'^\.\r?\n', '', cleaned_output, flags=re.MULTILINE)
    cleaned_output = re.sub(r'^250 ok.*\r?\n', '', cleaned_output, flags=re.MULTILINE)

    # Süslü parantez içindeki {çapraz referansları} yakalar ve linke dönüştürür
    def replace_link(match):
        word = match.group(1)
        return f'<a class="dict-link" href="sozluk.py?q={quote_plus(word)}&d={quote_plus(current_db)}&s=definitions">{word}</a>'
        
    cleaned_output = re.sub(r"\{+(.*?)\}+", replace_link, cleaned_output)
    return f'<div class="results-box"><pre>{cleaned_output.strip()}</pre></div>'

def main():
    print("Content-Type: text/html; charset=utf-8\n")
    
    query_string = os.environ.get('QUERY_STRING', '')
    parsed_params = parse_qs(query_string)
    
    raw_q = parsed_params.get('q', [''])[0]
    selected_db = parsed_params.get('d', ['*'])[0]
    selected_strat = parsed_params.get('s', ['definitions'])[0]
    dbinfo = parsed_params.get('dbinfo', [''])[0]
    serverinfo = parsed_params.get('serverinfo', [''])[0]
    
    q = clean_query(raw_q)
    value_attr = html.escape(q).replace('"', '&quot;')
    
    result_html = ""
    
    # Bilgi Ekranları Yönetimi (Doğrudan soket üzerinden ağ sorguları)
    if serverinfo:
        output, error_code = send_dict_command("SHOW SERVER")
        result_html = f'<div class="db-title"><b>DICT Sunucu Bilgisi</b></div><div class="results-box"><pre>{html.escape(output)}</pre></div>'
    elif dbinfo:
        output, error_code = send_dict_command(f"SHOW INFO {dbinfo}")
        result_html = f'<div class="db-title"><b>Sözlük Künyesi ({dbinfo})</b></div><div class="results-box"><pre>{html.escape(output)}</pre></div>'
    elif q:
        if selected_strat and selected_strat != "definitions":
            cmd = f"MATCH {selected_db} {selected_strat} \"{q}\""
        else:
            cmd = f"DEFINE {selected_db} \"{q}\""
            
        output, error_code = send_dict_command(cmd)
        result_html = process_dict_output(output, error_code, selected_db, selected_strat)

    # Güncel ve zengin veritabanı listesi
    databases = [
        ("*", "Tüm Sözlüklerde Ara (İlk bulduğunda durur)"),
        ("!", "İlk Eşleşme (Sadece ilk veritabanından sonuç getirir)"),
        ("gcide", "gcide - Kapsamlı Uluslararası İngilizce Sözlük"),
        ("wn", "wn - WordNet 3.0 (İngilizce Çevrimiçi Eşanlamlılar Sözlüğü)"),
        ("moby-thesaurus", "moby-thesaurus - Moby Kavramlar Dizini II"),
        ("elements", "elements - Kimyasal Elementler Veritabanı"),
        ("vera", "vera - V.E.R.A. Bilişim Kısaltmaları Sözlüğü"),
        ("jargon", "jargon - Hacker Argosu ve Terimleri Sözlüğü"),
        ("foldoc", "foldoc - Özgür Çevrimiçi Bilgisayar Terimleri Sözlüğü"),
        ("easton", "easton - Easton 1897 Kitab-ı Mukaddes Sözlüğü"),
        ("hitchcock", "hitchcock - Hitchcock Dini İsimler Sözlüğü"),
        ("bouvier", "bouvier - Bouvier Hukuk Sözlüğü"),
        ("devil", "devil - Şeytanın Sözlüğü (Hiciv/Mizah)"),
        ("world02", "world02 - CIA Dünya Almanağı (2002)"),
        ("fd-eng-tur", "fd-eng-tur - İngilizce-Türkçe FreeDict Sözlük"),
        ("fd-tur-eng", "fd-tur-eng - Türkçe-İngilizce FreeDict Sözlük"),
        ("fd-tur-deu", "fd-tur-deu - Türkçe-Almanca FreeDict Sözlük"),
        ("fd-deu-tur", "fd-deu-tur - Almanca-Türkçe FreeDict Sözlük"),
    ]
    
    strategies = [
        ("definitions", "Tanım Getir (Kelimelerin Anlamı)"),
        ("exact", "Tam Eşleşme (Birebir Aynı Kelime)"),
        ("prefix", "Önek Eşleşmesi (Bu Harflerle Başlayanlar)"),
        ("substring", "İçerik Eşleşmesi (İçinde Bu Harfler Geçenler)"),
        ("suffix", "Sonek Eşleşmesi (Bu Harflerle Bitenler)"),
        ("soundex", "Okunuş Benzerliği (Fonetik Yakınlık)"),
        ("lev", "Yazım Yakınlığı (Harf Benzerliği)"),
    ]

    html_template = fr"""<html>
<head>
<title>Sözlük - DICT Arama Motoru</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<style>
body {{
  font-family: "Times New Roman", Times, serif;
  font-size: 16px;
  line-height: 1.5em;
  background-color: #fbf9f4;
  color: #2b2b2b;
  margin: 0;
  padding: 30px 20px;
}}
.container {{
  max-width: 900px;
  margin: 0 auto;
}}
a {{
  color: #1a5f7a;
  text-decoration: none;
}}
a:hover {{
  text-decoration: underline;
}}
.nav-top {{
  font-family: Georgia, serif;
  font-size: 14px;
  margin-bottom: 15px;
  border-bottom: 1px dashed #d3cbb6;
  padding-bottom: 8px;
}}
.nav-top a {{
  color: #7e6850;
  font-weight: bold;
}}
.dict-link {{
  color: #990000;
  font-weight: bold;
}}
.form-section {{
  border-bottom: 1px dashed #d3cbb6;
  padding-bottom: 20px;
  margin-bottom: 25px;
}}
.header-area {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}}
h2 {{
  font-family: Georgia, serif;
  color: #1a5f7a;
  margin: 0;
  font-weight: normal;
}}
.new-search-btn {{
  font-size: 14px;
  background-color: #f0e6d2;
  padding: 4px 10px;
  border: 1px solid #c8bfa7;
  border-radius: 4px;
  color: #1a5f7a !important;
}}
select, input[type="text"] {{
  padding: 6px 10px;
  font-size: 15px;
  border: 1px solid #c8bfa7;
  background-color: #fffdf9;
  border-radius: 4px;
  margin-right: 8px;
  margin-bottom: 10px;
}}
input[type="text"] {{
  width: 160px;
}}
input[type="submit"] {{
  padding: 6px 15px;
  background: #1a5f7a;
  color: white;
  border: 1px solid #144d63;
  border-radius: 4px;
  cursor: pointer;
}}
.results-box {{
  margin-top: 20px;
}}
pre {{
  background: #fffdf9;
  padding: 20px;
  border: 1px solid #eaddca;
  border-radius: 6px;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: "Courier New", Courier, monospace;
  font-size: 15px;
  line-height: 1.6em;
}}
.db-title {{
  background-color: #f0e6d2;
  padding: 4px 10px;
  border-left: 4px solid #1a5f7a;
  margin-top: 25px;
  margin-bottom: 5px;
  font-family: Georgia, serif;
}}
.footer-links {{
  margin-top: 30px;
  border-top: 1px dashed #d3cbb6;
  padding-top: 15px;
  text-align: center;
  font-size: 14px;
}}
</style>
</head>
<body>
<div class="container">
    <div class="nav-top">
        <a href="http://ku.sdf.org/sozluk.py">« Ana Sayfa</a>
    </div>

    <div class="form-section">
        <form name="form1" method="GET" action="sozluk.py">
            <div class="header-area">
                <h2>Sözlük Arama Paneli</h2>
                <a class="new-search-btn" href="http://ku.sdf.org/sozluk.py">↻ Yeni Arama</a>
            </div>
            
            <input value="{value_attr}" type="text" name="q" placeholder="Kelime yazın...">
            
            <select name="d">
                {"".join(f'<option value="{db[0]}" {"selected" if selected_db == db[0] else ""}>{db[1]}</option>' for db in databases)}
            </select>
            
            <select name="s">
                {"".join(f'<option value="{st[0]}" {"selected" if selected_strat == st[0] else ""}>{st[1]}</option>' for st in strategies)}
            </select>
            
            <input type="submit" value="Ara">
        </form>
    </div>

    {result_html}

    <div class="footer-links">
        <a href="sozluk.py?dbinfo={selected_db if selected_db not in ['*', '!'] else 'fd-eng-tur'}">Seçili Sözlük Hakkında Bilgi</a> | 
        <a href="sozluk.py?serverinfo=1">DICT Sunucu Durumu</a>
    </div>

    <script language="JavaScript">
        document.form1.q.focus();
    </script>
</div>
</body>
</html>
"""
    print(html_template)

if __name__ == "__main__":
    main()
