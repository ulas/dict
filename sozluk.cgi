#!/usr/pkg/bin/python
import os
import html
import sys
import subprocess
import re
from urllib.parse import parse_qs

# --- DICT SUNUCU AYARLARI ---
DICT_HOST = "dict.dict.org"
DICT_PORT = 2628

def clean_query(q):
    if not q:
        return ""
    q = q.strip()
    q = re.sub(r'\s+', ' ', q)
    return q

def run_dict_cli(word):
    try:
        cmd = ["/usr/pkg/bin/dict", "-h", "dict.dict.org", word]
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        combined_output = result.stdout + result.stderr
        return combined_output, result.returncode
    except Exception as e:
        return f"Hata: Komut çalıştırılamadı. ({str(e)})", 1

def process_dict_output(output, error_code):
    if error_code != 0:
        return f"<b>Error: {output}</b>"
    
    if re.search(r"no definitions found", output, re.IGNORECASE):
        output_processed = re.sub(
            r"(: +)([a-zA-Z0-9_-]+)",
            r'\1<a href="?q=\2" onclick="processLink(\'\2\'); return false;">\2</a>',
            output
        )
        return f"<pre>{output_processed}</pre>"
    else:
        lines = output.split('\n')
        if lines:
            lines[0] = f"<b>{lines[0]}</b>"
        output = '\n'.join(lines)
        
        output = re.sub(
            r"(\n\nFrom )(.*)\n",
            r'\n\n<table cellpadding="4" bgcolor="#F2F5A9"><tr><td><b>\2</b></td></tr></table>',
            output
        )
        
        output = re.sub(
            r"\{+(.*?)\}+",
            r'<a href="?q=\1" onclick="processLink(\'\1\'); return false;">\1</a>',
            output
        )
        return f"<pre>{output}</pre>"

def main():
    print("Content-Type: text/html; charset=utf-8\n")
    
    query_string = os.environ.get('QUERY_STRING', '')
    parsed_params = parse_qs(query_string)
    
    raw_q = parsed_params.get('q', [''])[0]
    q = clean_query(raw_q)
    value_attr = html.escape(q).replace('"', '&quot;')
    
    result_html = ""
    if q:
        output, error_code = run_dict_cli(q)
        result_html = process_dict_output(output, error_code)

    html_template = fr"""<html>
<head>
<title>
Dictionary search using "dict"
</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<meta name="google-site-verification" content="JXQRbR64aZ5QO8Bp5zM4cr194Cub3Rug3UDm4CdmZdk" />
<link href='http://fonts.googleapis.com/css?family=Terminal+Dosis+Light' rel='stylesheet' type='text/css'>
<style>
body {{
  font-family: 'Terminal Dosis Light', serif;
  font-size: 14px;
  font-style: bold;
  font-weight: 200;
  text-shadow: none;
  text-decoration: none;
  text-transform: none;
  letter-spacing: -0.011em;
  word-spacing: 0.021em;
  line-height: 1em;
}}
</style>
</head>
<body>
<script language="JavaScript">
function processLink(s)
{{
        s = s.replace(/\s+/g," ");
        // window.location.pathname yerine doğrudan mutlak/bağıl parametre yönlendirmesi
        window.location.href = "sozluk.cgi?q=" + encodeURIComponent(s);
}}
</script>
<BODY STYLE="background-color:#F7F8E0"><CENTER>
<DIV STYLE="width:700px;align:center;text-align:left;background-color:#F7F8E0">
<form name="form1" method="GET" action="sozluk.cgi">
<h1>Enter word for "dict" search:</h1>
<input value="{value_attr}" type="text" name="q" onChange="submit()"><p>
</form></h3>

{result_html}

<script language="JavaScript">
        document.form1.q.focus();
</script>
</div>
</center>
</body>
</html>
"""
    print(html_template)

if __name__ == "__main__":
    main()
