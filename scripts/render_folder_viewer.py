"""Build an offline, zoomable folder viewer from the Mermaid hierarchy."""

from collections import defaultdict
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "docs/interview_demo"


def main():
    source = (ROOT / "folder_structure.mmd").read_text(encoding="utf-8")
    labels = dict(re.findall(r'(\w+)\["([^"\n]+)"\]', source))
    children = defaultdict(list)
    for parent, child in re.findall(r'^\s*(\w+)\s*-->\s*(\w+)', source, re.MULTILINE):
        children[parent].append(child)

    def node(key):
        label = escape(labels[key])
        tone = ' class="local"' if key in {"data", "persisted", "generated"} else (
            ' class="external"' if key in {"references", "vendors", "environment"} else "")
        if not children[key]:
            return f'<li{tone}><span class="leaf">{label}</span></li>'
        return f'<li{tone}><details open><summary>{label}</summary><ul>' + "".join(
            node(child) for child in children[key]) + '</ul></details></li>'

    page = '''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>RAG_Demo — Project folder structure</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#14283f;font:16px system-ui,sans-serif}
header{padding:16px 24px;background:white;border-bottom:1px solid #cbd6e1}
h1{font-size:21px;margin:0 0 10px}nav{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
button,a{font:inherit;color:#14283f}button{background:#fff;border:1px solid #b5c5d5;border-radius:6px;padding:7px 12px;cursor:pointer}
button:hover{background:#e5eff8}button:focus-visible,summary:focus-visible{outline:3px solid #087f8c}
#level{min-width:52px;text-align:center}small{display:block;margin-top:10px;color:#53657a}
#viewport{height:calc(100vh - 164px);overflow:auto;cursor:grab;touch-action:pan-x pan-y;padding:18px}
#viewport.dragging{cursor:grabbing;user-select:none}#canvas{position:relative;margin-inline:auto}#chart{position:absolute;left:0;top:0;transform-origin:top left;width:max-content;min-width:1050px;padding:24px 30px 44px;background:white;border:1px solid #d5dfe9;border-radius:12px}
ul{list-style:none;padding-left:32px;margin:0}#chart>ul{padding:0}li{position:relative;padding:5px 0}
li:before{content:"";position:absolute;left:-18px;top:0;width:16px;height:24px;border-left:1px solid #b8c9d8;border-bottom:1px solid #b8c9d8}
li:after{content:"";position:absolute;left:-18px;top:24px;bottom:-5px;border-left:1px solid #b8c9d8}
li:last-child:after{display:none}#chart>ul>li:before,#chart>ul>li:after{display:none}
summary,.leaf{line-height:1.65;padding:3px 10px;border-radius:5px;white-space:nowrap}
summary{cursor:pointer;color:#087f8c;font-weight:650}summary:hover{background:#e9f5f5}.leaf{display:inline-block;font-family:Consolas,monospace;font-size:15px}
.local>details>summary,.local>.leaf{background:#fff4df;color:#805118}
.external>details>summary,.external>.leaf{background:#edf0f5;color:#53657a}
#message{margin-left:8px;color:#53657a;font-size:13px}
</style></head><body>
<header><h1>RAG_Demo / Project folder structure</h1><nav>
<button id="out" aria-label="Zoom out">−</button><span id="level">100%</span><button id="in" aria-label="Zoom in">+</button>
<button id="actual">100%</button><button id="fit">Fit width</button>
<button id="expand">Expand all</button><button id="collapse">Collapse sections</button>
<button id="fullscreen">Full screen</button><a href="folder_structure.mmd">Mermaid source</a>
<span id="message" role="status"></span></nav>
<small>Scroll to explore. Ctrl + wheel to zoom. Drag blank space to pan. Click a folder to collapse it. F11 also toggles browser full screen.</small></header>
<main id="viewport" aria-label="Scrollable project folder map"><div id="canvas"><div id="chart"><ul>''' + node("root") + '''</ul></div></div></main>
<script>
const view=document.querySelector('#viewport'),chart=document.querySelector('#chart'),canvas=document.querySelector('#canvas');
let scale=1,drag=null;
function resize(){canvas.style.width=Math.ceil(chart.offsetWidth*scale)+'px';canvas.style.height=Math.ceil(chart.offsetHeight*scale)+'px';}
function zoom(value){scale=Math.min(2.5,Math.max(.4,value));chart.style.transform='scale('+scale+')';document.querySelector('#level').textContent=Math.round(scale*100)+'%';resize();}
document.querySelector('#in').onclick=()=>zoom(scale+.1);
document.querySelector('#out').onclick=()=>zoom(scale-.1);
document.querySelector('#actual').onclick=()=>zoom(1);
document.querySelector('#fit').onclick=()=>zoom((view.clientWidth-40)/chart.offsetWidth);
document.querySelector('#expand').onclick=()=>{chart.querySelectorAll('details').forEach(d=>d.open=true);resize();};
document.querySelector('#collapse').onclick=()=>{chart.querySelectorAll('details').forEach((d,i)=>d.open=i===0);resize();};
document.querySelector('#fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){document.querySelector('#message').textContent='Press F11 for browser full screen.';}};
view.addEventListener('wheel',e=>{if(e.ctrlKey){e.preventDefault();zoom(scale+(e.deltaY<0?.1:-.1));}},{passive:false});
view.addEventListener('pointerdown',e=>{if(e.button!==0||e.target.closest('summary,button,a'))return;drag={x:e.clientX,y:e.clientY,left:view.scrollLeft,top:view.scrollTop};view.classList.add('dragging');view.setPointerCapture(e.pointerId);});
view.addEventListener('pointermove',e=>{if(drag){view.scrollLeft=drag.left-(e.clientX-drag.x);view.scrollTop=drag.top-(e.clientY-drag.y);}});
function stop(){drag=null;view.classList.remove('dragging');}
view.addEventListener('pointerup',stop);view.addEventListener('pointercancel',stop);
chart.addEventListener('toggle',resize,true);window.addEventListener('resize',resize);new ResizeObserver(resize).observe(chart);resize();
</script></body></html>'''
    destination = ROOT / "folder_structure.html"
    destination.write_text(page, encoding="utf-8")
    print(f"FOLDER_VIEWER_READY: {destination.relative_to(ROOT.parents[1]).as_posix()}")


if __name__ == "__main__":
    main()
