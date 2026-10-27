from pathlib import Path
import base64
import json

p = Path("eventx/release/presentation_20261012/rev2")
content = json.loads((p / "SLIDE_CONTENT.json").read_text())
data = []
for slide in content["slides"]:
    image_path = p / ".build" / "previews" / ("slide_" + str(slide["slidenum"]).zfill(2) + ".png")
    raw = image_path.read_bytes()
    assert raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n".decode("unicode_escape").encode("latin1"))
    data.append({
        "title": slide["title"],
        "image": "data:image/png;base64," + base64.b64encode(raw).decode(),
        "notes": slide["talktrack"],
    })
html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EventX progress presentation</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#14171b;color:#fff;font:18px system-ui,sans-serif}
main{height:calc(100vh - 66px);display:flex;align-items:center;justify-content:center}
#slide{width:100%;height:100%;object-fit:contain}
footer{height:66px;display:flex;align-items:center;justify-content:center;gap:16px;background:#20252c}
button{font:inherit;padding:8px 14px;border:1px solid #667080;border-radius:4px;background:#303945;color:white;cursor:pointer}
button:disabled{opacity:.4;cursor:default}
#counter{min-width:180px;text-align:center}aside{position:fixed;right:18px;top:18px;width:min(520px,90vw);max-height:calc(100vh - 100px);overflow:auto;padding:24px;background:#fff;color:#111;box-shadow:0 4px 30px #0008}
aside[hidden]{display:none}aside h2{margin-top:0;font-size:23px}#notes{white-space:pre-wrap;line-height:1.5}
@media print{footer,aside{display:none!important}body{background:white}.print-slide{break-after:page}main{display:none}.print-slide img{width:100%}}
@media screen{.print-slide{display:none}}
</style></head><body>
<main><img id="slide" alt=""></main>
<footer><button id="prev" aria-label="Previous slide">Previous</button><span id="counter" aria-live="polite"></span><button id="next" aria-label="Next slide">Next</button><button id="notesButton">Notes</button><button id="full">Full screen</button></footer>
<aside id="notesPanel" hidden><h2 id="notesTitle"></h2><div id="notes"></div></aside>
<script>
const slides=__DATA__;
let current=0;
const image=document.getElementById("slide"),counter=document.getElementById("counter"),panel=document.getElementById("notesPanel");
function show(index){current=Math.max(0,Math.min(slides.length-1,index));const s=slides[current];image.src=s.image;image.alt=s.title;counter.textContent=(current+1)+" / "+slides.length+(current>=9?" · Backup":" · Main talk");document.getElementById("prev").disabled=current===0;document.getElementById("next").disabled=current===slides.length-1;document.getElementById("notesTitle").textContent=s.title;document.getElementById("notes").textContent=s.notes;}
function toggleNotes(){panel.hidden=!panel.hidden;}
function fullscreen(){if(document.fullscreenElement){document.exitFullscreen();}else{document.documentElement.requestFullscreen().catch(()=>{});}}
document.getElementById("prev").onclick=()=>show(current-1);
document.getElementById("next").onclick=()=>show(current+1);
document.getElementById("notesButton").onclick=toggleNotes;
document.getElementById("full").onclick=fullscreen;
document.addEventListener("keydown",e=>{if(["ArrowRight","PageDown"," "].includes(e.key)){e.preventDefault();show(current+1);}else if(["ArrowLeft","PageUp"].includes(e.key)){e.preventDefault();show(current-1);}else if(e.key==="Home"){show(0);}else if(e.key==="End"){show(slides.length-1);}else if(e.key.toLowerCase()==="n"){toggleNotes();}else if(e.key.toLowerCase()==="f"){fullscreen();}});
for(const s of slides){const section=document.createElement("section");section.className="print-slide";const img=document.createElement("img");img.src=s.image;img.alt=s.title;section.appendChild(img);document.body.appendChild(section);}
show(0);
</script></body></html>
"""
html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))
output = p / "EVENTX_PROGRESS_PRESENTATION.html"
output.write_text(html)
print(json.dumps({"slides_embedded":len(data),"html_bytes":output.stat().st_size,"network_dependencies":0}))

