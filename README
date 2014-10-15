<html>
<head>
<title>
Dictionary search using "dict"
</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<link href='http://fonts.googleapis.com/css?family=Terminal+Dosis+Light' rel='stylesheet' type='text/css'>
<style>
body {
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
}
</style>
</head>
<body>
<script language="JavaScript">
function processLink(s)
{
        s = s.replace(/\s+/g," ");
        location.href=self.name + "?q=" + escape(s);
}
</script>
<BODY STYLE="background-color:#F7F8E0"><CENTER>
<DIV STYLE="width:700px;align:center;text-align:left;background-color:#F7F8E0">
<center>
</center>
<h4><h4>
<form name="form1">
<h3>Enter word for "dict" search: <input value="<?php
error_reporting(E_ALL ^ E_NOTICE);
ini_set('error_reporting', E_ALL ^ E_NOTICE);
        $q = $_REQUEST['q'];
        # clean up passed value
        $q = preg_replace("/^\s+/","",$q);
        $q = preg_replace("/\s+$/","",$q);
        $q = preg_replace("/\s+/"," ",$q);
        $value = preg_replace("/\"/","&quot;",$q);
        echo "$value"
?>" type="text" name="q" onChange="submit()"><p>
</form></h3>
<?php
if($q != "") {
        $eq = escapeshellarg($q);
        exec("/usr/pkg/bin/dict -h pcai055.informatik.uni-leipzig.de $eq 2>&1",$output,$error);
        $output = implode("\n",$output);
        if($error) {
                echo "<pre><b>Error: $output<b></pre>";
        }
        else {
                if (preg_match("/no definitions found/i",$output)) {
                        # turn suggested alternatives into links
                        $output = preg_replace("/(: +)(\w+)/",
                                "\\1<a href=\"javascript:processLink('\\2');\">\\2</a>",$output);
                        echo "<pre>$output</pre>";
                }
                else {
                        # bold first line
                        $output = preg_replace("/^(.*)/","<b>\\1</b>",$output);
                        # wrap first line of each reference in table to control background color
                        $output = preg_replace("/(\n\nFrom )(.*)\n/","\n\n<table cellpadding=4
                                bgcolor=#F2F5A9><tr><td><b>\\2</b></td></tr></table>",$output);
                        # find and process document internal links
                        $output = preg_replace("/\{+(.*?)\}+/s",
                                "<a href=\"javascript:processLink('\\1');\">\\1</a>",$output);
                        echo "<pre>$output</pre>";
                }
        }
}
?>
<script language="JavaScript">
        document.form1.q.focus();
</script>
</body>
</html>

