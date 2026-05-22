#!/usr/pkg/bin/python
import os
import html
import sys
import subprocess
import re
from urllib.parse import parse_qs, quote_plus

# --- DICT SUNUCU AYARLARI ---
DICT_HOST = "dict.dict.org"

def clean_query(q):
    """Giriş metnini temizler"""
    if not q:
        return ""
    q = q.strip()
    q = re.sub(r'\s+', ' ', q)
    return q

def run_dict_cli(word, database="*", strategy="", info_mode=None):
    """
    Sistemdeki /usr/pkg/bin/dict aracını çağırır.
    Gelişmiş bilgi modlarını ve arama parametrelerini CLI argümanlarına eşler.
    """
    try:
        cmd = ["/usr/pkg/bin/dict", "-h", DICT_HOST]
        
        # Bilgi modları kontrolü
        if info_mode == "serverinfo":
            cmd.append("-I")
            result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
            return result.stdout + result.stderr, result.returncode
        elif info_mode == "dbinfo":
            cmd.extend(["-i", database])
            result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
            return result.stdout + result.stderr, result.returncode
            
        # Normal Arama Modu
        if strategy and strategy != "definitions":
            cmd.extend(["-s", strategy])
        if database:
            cmd.extend(["-d", database])
            
        cmd.append(word)
        
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        return result.stdout + result.stderr, result.returncode
    except Exception as e:
        return f"Hata: Komut çalıştırılamadı. ({str(e)})", 1

def process_dict_output(output, error_code, current_db="*", current_strat=""):
    """
    Gelen çıktıyı işler. Eşleşen kelimeleri veya tanımları
    kuran.php temasına uygun tıklanabilir linklere dönüştürür.
    """
    if error_code != 0:
        if re.search(r"no definitions found|no matches found", output, re.IGNORECASE):
            return f'<div class="results-box"><pre>Aranan kelimeye ait bir sonuç bulunamadı.</pre></div>'
        return f'<div class="results-box" style="color: #aa0000;"><b>Hata: {html.escape(output)}</b></div>'
    
    # Benzer Kelimeleri Listeleme Modu (Match)
    if current_strat and current_strat != "definitions":
        lines = output.split('\n')
        processed_lines = []
        for line in lines:
            match = re.match(r"^([^\s]+)\s+(.+)$", line.strip())
            if match:
                db_code = match.group(1)
                matched_word = match.group(2)
                # Tıklandığında doğrudan o kelimenin tanımına (definitions) yönlendirir
                link = f'<a class="dict-link" href="sozluk.cgi?q={quote_plus(matched_word)}&d={quote_plus(db_code)}&s=definitions">"{matched_word}"</a>'
                processed_lines.append(f'<span style="color:#777;">[{db_code}]</span> {link}')
            else:
                if line.strip():
                    processed_lines.append(html.escape(line))
        
        output_html = "<br>".join(processed_lines)
        return f'<div class="results-box"><pre>{output_html}</pre></div>'

    # Normal Tanım Modu (Definitions)
    # Veritabanı kaynak başlıklarını şerit blok haline getirir
    output = re.sub(
        r"(\n\nFrom )(.*)\n",
        r'\n\n<div class="db-title"><b>Kaynak: \2</b></div>',
        output
    )
    
    # Süslü parantez içindeki {çapraz referansları} yakalar ve Türkçe parametrelerle linke dönüştürür
    def replace_link(match):
        word = match.group(1)
        return f'<a class="dict-link" href="sozluk.cgi?q={quote_plus(word)}&d={quote_plus(current_db)}&s=definitions">{word}</a>'
        
    output = re.sub(r"\{+(.*?)\}+", replace_link, output)
    return f'<div class="results-box"><pre>{output}</pre></div>'

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
    
    # Bilgi Ekranları Yönetimi
    if serverinfo:
        output, error_code = run_dict_cli("", info_mode="serverinfo")
        result_html = f'<div class="db-title"><b>DICT Sunucu Bilgisi</b></div><div class="results-box"><pre>{html.escape(output)}</pre></div>'
    elif dbinfo:
        output, error_code = run_dict_cli("", database=dbinfo, info_mode="dbinfo")
        result_html = f'<div class="db-title"><b>Sözlük Künyesi ({dbinfo})</b></div><div class="results-box"><pre>{html.escape(output)}</pre></div>'
    elif q:
        output, error_code = run_dict_cli(q, selected_db, selected_strat)
        result_html = process_dict_output(output, error_code, selected_db, selected_strat)

    # Sözlük veritabanlarının Türkçe açıklamalı tam listesi
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
        ("gaz2k-counties", "gaz2k-counties - ABD Nüfus Sayım Bölgeleri"),
        ("gaz2k-places", "gaz2k-places - ABD Yerleşim Yerleri Dizini"),
        ("gaz2k-zips", "gaz2k-zips - ABD Posta Kodları Dizini"),
        ("fd-eng-tur", "fd-eng-tur - İngilizce-Türkçe FreeDict Sözlük"),
        ("fd-tur-eng", "fd-tur-eng - Türkçe-İngilizce FreeDict Sözlük"),
        ("fd-tur-deu", "fd-tur-deu - Türkçe-Almanca FreeDict Sözlük"),
        ("fd-deu-tur", "fd-deu-tur - Almanca-Türkçe FreeDict Sözlük"),
        ("fd-swe-tur", "fd-swe-tur - İsveççe-Türkçe FreeDict Sözlük"),
        ("fd-kur-tur", "fd-kur-tur - Kürtçe-Türkçe FreeDict Sözlük"),
        ("fd-ckb-kmr", "fd-ckb-kmr - Sorani-Kurmanci FreeDict Sözlük"),
        ("fd-deu-kur", "fd-deu-kur - Almanca-Kürtçe FreeDict Sözlük"),
        ("fd-kur-deu", "fd-kur-deu - Kürtçe-Almanca FreeDict Sözlük"),
        ("fd-kur-eng", "fd-kur-eng - Kürtçe-İngilizce FreeDict Sözlük"),
        ("fd-ara-eng", "fd-ara-eng - Arapça-İngilizce FreeDict Sözlük"),
        ("fd-eng-ara", "fd-eng-ara - İngilizce-Arapça FreeDict Sözlük"),
        ("fd-jpn-eng", "fd-jpn-eng - Japonca-İngilizce FreeDict Sözlük"),
        ("fd-eng-jpn", "fd-eng-jpn - İngilizce-Japonca FreeDict Sözlük"),
        ("fd-jpn-deu", "fd-jpn-deu - Japonca-Almanca FreeDict Sözlük"),
        ("fd-deu-eng", "fd-deu-eng - Almanca-İngilizce FreeDict Sözlük"),
        ("fd-eng-deu", "fd-eng-deu - İngilizce-Almanca FreeDict Sözlük"),
        ("fd-fra-eng", "fd-fra-eng - Fransızca-İngilizce FreeDict Sözlük"),
        ("fd-eng-fra", "fd-eng-fra - İngilizce-Fransızca FreeDict Sözlük"),
        ("fd-fra-deu", "fd-fra-deu - Fransızca-Almanca FreeDict Sözlük"),
        ("fd-deu-fra", "fd-deu-fra - Almanca-Fransızca FreeDict Sözlük"),
        ("fd-spa-eng", "fd-spa-eng - İspanyolca-İngilizce FreeDict Sözlük"),
        ("fd-eng-spa", "fd-eng-spa - İngilizce-İspanyolca FreeDict Sözlük"),
        ("fd-ita-eng", "fd-ita-eng - İtalyanca-İngilizce FreeDict Sözlük"),
        ("fd-eng-ita", "fd-eng-ita - İngilizce-İtalyanca FreeDict Sözlük"),
        ("fd-por-eng", "fd-por-eng - Portekizce-İngilizce FreeDict Sözlük"),
        ("fd-eng-por", "fd-eng-por - İngilizce-Portekizce FreeDict Sözlük"),
        ("fd-rus-eng", "fd-rus-eng - Rusça-İngilizce FreeDict Sözlük"),
        ("fd-epo-eng", "fd-epo-eng - Esperanto-İngilizce FreeDict Sözlük"),
        ("fd-lat-eng", "fd-lat-eng - Latince-İngilizce FreeDict Sözlük"),
        ("fd-eng-lat", "fd-eng-lat - İngilizce-Latince FreeDict Sözlük"),
        ("fd-ces-eng", "fd-ces-eng - Çekçe-İngilizce FreeDict Sözlük"),
        ("fd-eng-ces", "fd-eng-ces - İngilizce-Çekçe FreeDict Sözlük"),
        ("fd-hun-eng", "fd-hun-eng - Macarca-İngilizce FreeDict Sözlük"),
        ("fd-eng-hun", "fd-eng-hun - İngilizce-Macarca FreeDict Sözlük"),
        ("fd-pol-eng", "fd-pol-eng - Lehçe-İngilizce FreeDict Sözlük"),
        ("fd-eng-pol", "fd-eng-pol - İngilizce-Lehçe FreeDict Sözlük"),
        ("fd-fin-eng", "fd-fin-eng - Fince-İngilizce FreeDict Sözlük"),
        ("fd-eng-fin", "fd-eng-fin - İngilizce-Fince FreeDict Sözlük"),
        ("fd-swe-eng", "fd-swe-eng - İsveççe-İngilizce FreeDict Sözlük"),
        ("fd-eng-swe", "fd-eng-swe - İngilizce-İsveççe FreeDict Sözlük"),
        ("fd-dan-eng", "fd-dan-eng - Danimarkaca-İngilizce FreeDict Sözlük"),
        ("fd-nld-eng", "fd-nld-eng - Felemenkçe-İngilizce FreeDict Sözlük"),
        ("fd-eng-nld", "fd-eng-nld - İngilizce-Felemenkçe FreeDict Sözlük"),
        ("fd-hrv-eng", "fd-hrv-eng - Hırvatça-İngilizce FreeDict Sözlük"),
        ("fd-eng-hrv", "fd-eng-hrv - İngilizce-Hırvatça FreeDict Sözlük"),
        ("fd-bul-eng", "fd-bul-eng - Bulgarca-İngilizce FreeDict Sözlük"),
        ("fd-lit-eng", "fd-lit-eng - Litvanyaca-İngilizce FreeDict Sözlük"),
        ("fd-eng-lit", "fd-eng-lit - İngilizce-Litvanyaca FreeDict Sözlük"),
        ("fd-slk-eng", "fd-slk-eng - Slovakça-İngilizce FreeDict Sözlük"),
        ("fd-srp-eng", "fd-srp-eng - Sırpça-İngilizce FreeDict Sözlük"),
        ("fd-eng-srp", "fd-eng-srp - İngilizce-Sırpça FreeDict Sözlük"),
        ("fd-gle-eng", "fd-gle-eng - İrlandaca-İngilizce FreeDict Sözlük"),
        ("fd-eng-gle", "fd-eng-gle - İngilizce-İrlandaca FreeDict Sözlük"),
        ("fd-swh-eng", "fd-swh-eng - Svahili-İngilizce FreeDict Sözlük"),
        ("fd-eng-swh", "fd-eng-swh - İngilizce-Svahili FreeDict Sözlük"),
        ("fd-afr-eng", "fd-afr-eng - Afrikaanca-İngilizce FreeDict Sözlük"),
        ("fd-eng-afr", "fd-eng-afr - İngilizce-Afrikaanca FreeDict Sözlük"),
        ("fd-cym-eng", "fd-cym-eng - Galler Dili-İngilizce FreeDict Sözlük"),
        ("fd-eng-cym", "fd-eng-cym - İngilizce-Galler Dili FreeDict Sözlük"),
        ("fd-kha-eng", "fd-kha-eng - Khasi Dili-İngilizce FreeDict Sözlük"),
        ("english", "english - Kısa Yol (Tüm İngilizce Sözlükler)"),
        ("trans", "trans - Kısa Yol (Tüm Çeviri Sözlükleri)"),
    ]
    
    # Türkçe Arama Yöntemleri (Strategies)
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
  font-family: "Times New Roman", Times, serif, "Palatino Linotype", "Book Antiqua";
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
  text-align: left;
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
  margin-top: 0;
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
.new-search-btn:hover {{
  background-color: #eaddca;
}}
select, input[type="text"] {{
  padding: 6px 10px;
  font-size: 15px;
  font-family: inherit;
  border: 1px solid #c8bfa7;
  background-color: #fffdf9;
  border-radius: 4px;
  margin-right: 8px;
  margin-bottom: 10px;
}}
input[type="text"] {{
  width: 160px;
}}
select {{
  max-width: 320px;
}}
input[type="submit"] {{
  padding: 6px 15px;
  background: #1a5f7a;
  color: white;
  border: 1px solid #144d63;
  border-radius: 4px;
  cursor: pointer;
  font-family: inherit;
  font-size: 15px;
}}
input[type="submit"]:hover {{
  background: #144d63;
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
  color: #333333;
}}
.db-title {{
  background-color: #f0e6d2;
  padding: 4px 10px;
  border-left: 4px solid #1a5f7a;
  margin-top: 25px;
  margin-bottom: 5px;
  font-family: Georgia, serif;
  font-size: 15px;
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
        <a href="http://ku.sdf.org/sozluk.cgi">« Ana Sayfa</a>
    </div>

    <div class="form-section">
        <form name="form1" method="GET" action="sozluk.cgi">
            <div class="header-area">
                <h2>Sözlük Arama Paneli</h2>
                <a class="new-search-btn" href="http://ku.sdf.org/sozluk.cgi">↻ Yeni Arama</a>
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
        <a href="sozluk.cgi?dbinfo={selected_db if selected_db not in ['*', '!'] else 'fd-eng-tur'}">Seçili Sözlük Hakkında Bilgi</a> | 
        <a href="sozluk.cgi?serverinfo=1">DICT Sunucu Durumu</a>
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
