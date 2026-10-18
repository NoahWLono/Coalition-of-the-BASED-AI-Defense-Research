"""Render the repository's verified prose as local HTML and portable PDFs."""
import argparse
import html
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import markdown
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cedar.export import THEME_CONTROL, theme_script

OUT = ROOT / 'output'
INK = colors.HexColor('#183348')
TEAL = colors.HexColor('#167680')
STYLE = """
*{box-sizing:border-box}body{margin:0;background:#eef3f6;color:#183348;font:16px/1.65 system-ui,sans-serif}a{color:#087681}main{max-width:1100px;margin:auto;padding:48px 32px}header{background:#153044;color:white;padding:48px 0}header>div{max-width:1100px;margin:auto;padding:0 32px}.eyebrow{color:#99d1d0;letter-spacing:.16em;text-transform:uppercase;font-size:12px;font-weight:700}h1{font-size:42px;line-height:1.12;letter-spacing:-.03em;margin:14px 0 24px}h2{font-size:26px;margin-top:42px}h3{font-size:19px;margin-top:30px}.lead{max-width:800px;font-size:20px;color:#d4e3eb}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}.card,article{background:white;border:1px solid #d9e3e9;border-radius:8px;padding:24px}.card h2{margin:0 0 12px;font-size:22px}.note{border-left:4px solid #bd9349;background:#fff9ed;padding:16px 20px}img,video{max-width:100%;height:auto;border:1px solid #d9e3e9;border-radius:6px}table{display:block;overflow:auto;border-collapse:collapse;font-size:14px}th,td{padding:10px;border:1px solid #d9e3e9;text-align:left;vertical-align:top}th{background:#e9f1f5}pre{overflow:auto;padding:20px;background:#152f43;color:#eef5f8;border-radius:5px}code{font-size:.9em}footer{font-size:13px;color:#526b7e;border-top:1px solid #cbd8e0;margin-top:42px;padding-top:18px}.pill{display:inline-block;padding:5px 10px;background:#edf7f6;border-radius:4px;font-size:13px;margin-right:8px}.actions a{display:inline-block;margin:5px 12px 5px 0;padding:11px 17px;background:#edf7f6;border:1px solid #bad6d6;border-radius:5px;text-decoration:none;font-weight:650}@media(max-width:600px){main{padding:25px 15px}header>div{padding:0 20px}h1{font-size:32px}article{padding:20px}table{font-size:12px}}
"""
STYLE += """
:root{color-scheme:dark}:root[data-theme="light"]{color-scheme:light}
.theme-control{display:flex;align-items:center;justify-content:flex-end;gap:9px;font-size:12px;font-weight:600;margin-bottom:18px}
.theme-control select{font:inherit;color:inherit;background:#152735;border:1px solid #557586;border-radius:5px;padding:8px 26px 8px 10px}
:root[data-theme="light"] .theme-control select{background:#fff;color:#183348}
header .theme-control{color:#d4e3eb}header .theme-control select{background:#203e53;color:#fff}
a:focus-visible,select:focus-visible{outline:3px solid #78d3d0;outline-offset:4px}
:root:not([data-theme="light"]) body{background:#0d1822;color:#e1edf4}
:root:not([data-theme="light"]) a{color:#8edbd7}
:root:not([data-theme="light"]) :is(.card,article){background:#152735;border-color:#354e5e}
:root:not([data-theme="light"]) .note{background:#372e20;border-color:#d4ac6d;color:#f0d7ac}
:root:not([data-theme="light"]) :is(img,video,th,td){border-color:#354e5e}
:root:not([data-theme="light"]) th{background:#213949}
:root:not([data-theme="light"]) :is(.pill,.actions a){background:#1e3c42;border-color:#42646b;color:#b4e6df}
:root:not([data-theme="light"]) footer{color:#a8becd;border-color:#354e5e}
@media print{:root{color-scheme:light}.theme-control{display:none}:root:not([data-theme="light"]) body{background:white;color:#183348}:root:not([data-theme="light"]) :is(.card,article){background:white;color:#183348}:root:not([data-theme="light"]) a{color:#087681}:root:not([data-theme="light"]) .note{background:#fff9ed;color:#183348}:root:not([data-theme="light"]) th{background:#e9f1f5;color:#183348}}
"""



def prose(path):
    return markdown.markdown(path.read_text(), extensions=['tables', 'fenced_code'], output_format='xhtml')


def write_html():
    target = OUT / 'html'
    target.mkdir(parents=True, exist_ok=True)
    for path in [ROOT/'README.md', *sorted((ROOT/'docs').glob('*.md'))]:
        content = prose(path)
        def link(match):
            attr, ref = match.groups()
            if re.match(r'\w+://|#|mailto:', ref):
                return match.group(0)
            resolved = (path.parent/ref).resolve()
            if resolved.suffix == '.md' and resolved.parent in {ROOT, ROOT/'docs'}:
                new = resolved.stem+'.html'
            else:
                try: new = '../../'+str(resolved.relative_to(ROOT))
                except ValueError: return match.group(0)
            return f'{attr}="{html.escape(new, quote=True)}"'
        content = re.sub(r'(href|src)="([^"]+)"', link, content)
        document = f'<!doctype html><html lang="{"fr" if path.stem.endswith("_FR") else "en"}" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Project 6 | CEDAR | {path.stem}</title><script>{theme_script()}</script><style>{STYLE}</style></head><body><main>{THEME_CONTROL}<p><a href="../../PORTFOLIO.html">Project 6: CEDAR portfolio</a> / {html.escape(path.stem)}</p><article>{content}</article><footer>Synthetic demonstration · Directed by Noah Weinberger · Implemented with AI assistance</footer></main></body></html>'
        (target/(path.stem+'.html')).write_text(document)
    evaluation = json.loads((ROOT/'artifacts/evaluation.json').read_text())
    browser = json.loads((ROOT/'artifacts/browser-check.json').read_text())
    cards = [
        ('Start the meeting', 'Read the concise management brief, then follow the recorded change-and-review story.', [('Executive brief - English','output/html/EXECUTIVE_BRIEF_EN.html'),('Note de synthèse - français','output/html/EXECUTIVE_BRIEF_FR.html'),('Bilingual brief PDF','output/pdf/cedar-executive-briefs.pdf')]),
        ('Inspect the engineering', 'Trace the evidence model, arithmetic, failure corrections and adoption limits.', [('Technical case study','output/html/CASE_STUDY.html'),('Technical portfolio PDF','output/pdf/cedar-technical-portfolio.pdf'),('Architecture and boundaries','output/html/ARCHITECTURE.html'),('Threat model','output/html/THREAT_MODEL.html')]),
        ('Verify the result', 'Open the portable decision, inspect its exact evidence, and reproduce the checks.', [('Sample decision report','artifacts/sample-decision/report.html'),('Portable decision ZIP','artifacts/full-decision.zip'),('Claims ledger','output/html/CLAIMS_LEDGER.html'),('Completion report','output/html/COMPLETION_REPORT.html')]),
        ('Prepare the next conversation', 'Use a bounded pilot proposal and implementation-grounded interview answers.', [('Four-week pilot','output/html/PILOT_PROPOSAL.html'),('Ten technical questions','output/html/INTERVIEW.html'),('Narration script','output/html/DEMO_SCRIPT.html'),('Setup and reproduction','output/html/README.html')])]
    card_html=''.join('<section class="card"><h2>'+title+'</h2><p>'+desc+'</p><ul>'+''.join(f'<li><a href="{url}">{label}</a></li>' for label,url in links)+'</ul></section>' for title,desc,links in cards)
    shots=''.join(f'<figure><a href="artifacts/screenshots/{name}.png"><img src="artifacts/screenshots/{name}.png" alt="{label}" loading="lazy"></a><figcaption>{label} · historical light appearance</figcaption></figure>' for name,label in [('overview','Actual application: procurement overview'),('evidence','Exact original passage and source version'),('sensitivity','Declared weight sensitivity'),('changes','Amendment effects and stale approvals')])
    document=f'''<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Project 6 | CEDAR | Noah Weinberger</title><script>{theme_script()}</script><style>{STYLE}</style></head><body>
<header><div>{THEME_CONTROL}<div class="eyebrow">Project 6 / Noah Weinberger / AI-assisted engineering portfolio</div><h1>CEDAR<br>Evidence behind a procurement decision.</h1><p class="lead">A local workbench that connects requirements to supplier evidence, exposes commercial uncertainty, and preserves decisions when the inputs change.</p></div></header>
<main><div class="note"><strong>Synthetic civilian demonstration.</strong> Fictional suppliers, unarmed inspection packages and synthetic software advisories. No customer validation, physical product testing or contractor endorsement is claimed.</div>
<p><span class="pill">12 configurations</span><span class="pill">40 requirements</span><span class="pill">36 base documents</span><span class="pill">601 baseline assertions</span></p>
<div class="actions"><a href="http://127.0.0.1:8765">Open the running local application</a><a href="README.md">Source and reproduction guide</a><a href="output/html/README.html">Launch instructions</a></div>
<div class="grid">{card_html}</div>
<h2>The demonstration</h2><p>Start with an incomplete low quotation. Inspect the evidence, change the cost assumption, review a decision, then apply a supplier amendment. The previous approval becomes stale. A new conditional record preserves the open question.</p>
<video controls preload="metadata" poster="artifacts/screenshots/overview.png"><source src="artifacts/cedar-demo.webm" type="video/webm"></video><p>Historical application capture, silent, recorded before the dark theme update. The recording and PDFs preserve the original light appearance. The accompanying narration script is a separate rehearsal guide. Recorded workflow duration: {browser['duration_seconds']:.1f} seconds, including browser finalization; the encoded video duration is recorded in the completion report.</p>
<h2>Evidence available for inspection</h2><p>The recorded synthetic evaluation compares 2,952 requirement states with separately authored expected results. No state mismatches or unsupported baseline citations were observed. The three text layouts were designed for this parser; this result does not establish accuracy on unseen customer files.</p>
<div class="grid">{shots}</div>
<footer>Synthetic portfolio, prepared October 2026. Historical checks and appearance are identified in the <a href="output/html/THEME_REFRESH.html">theme update record</a>. <a href="output/html/LIMITATIONS.html">Limits</a> · <a href="output/html/THIRD_PARTY.html">Attribution</a> · <a href="artifacts/evaluation.json">Machine-readable evaluation</a></footer></main></body></html>'''
    (ROOT/'PORTFOLIO.html').write_text(document)


def inline(node):
    result=html.escape(node.text or '')
    for child in node:
        inner=inline(child)
        if child.tag in {'strong','b'}: result+='<b>'+inner+'</b>'
        elif child.tag in {'em','i'}: result+='<i>'+inner+'</i>'
        elif child.tag=='code': result+='<font name="Courier">'+inner+'</font>'
        elif child.tag=='a' and child.get('href','').startswith('https://'): result+='<link href="'+html.escape(child.get('href'),quote=True)+'" color="#167680">'+inner+'</link>'
        elif child.tag=='br': result+='<br/>'
        elif child.tag=='img': pass
        else: result+=inner
        result+=html.escape(child.tail or '')
    return result.replace('—','-').replace('–','-').replace('\u2011','-')


def pdf_setup():
    fonts=Path(reportlab.__file__).parent/'fonts'
    for family,file in [('Vera','Vera.ttf'),('Vera-Bold','VeraBd.ttf'),('Vera-Italic','VeraIt.ttf'),('Vera-BoldItalic','VeraBI.ttf')]:
        pdfmetrics.registerFont(TTFont(family,str(fonts/file)))
    pdfmetrics.registerFontFamily('Vera',normal='Vera',bold='Vera-Bold',italic='Vera-Italic',boldItalic='Vera-BoldItalic')


def styles(brief=False):
    body=ParagraphStyle('Body',fontName='Vera',fontSize=9.7 if brief else 9.3,leading=13.5 if brief else 13.3,textColor=INK,spaceAfter=7 if brief else 8)
    return {'p':body,'li':ParagraphStyle('List',parent=body,leftIndent=12,firstLineIndent=-8,spaceAfter=6),
        'h1':ParagraphStyle('H1',parent=body,fontName='Vera-Bold',fontSize=23,leading=29,spaceAfter=17,keepWithNext=True),
        'h2':ParagraphStyle('H2',parent=body,fontName='Vera-Bold',fontSize=15,leading=20,spaceBefore=12,spaceAfter=8,keepWithNext=True,textColor=TEAL),
        'h3':ParagraphStyle('H3',parent=body,fontName='Vera-Bold',fontSize=11,leading=16,spaceBefore=10,spaceAfter=6,keepWithNext=True),
        'cell':ParagraphStyle('Cell',parent=body,fontSize=7.4,leading=10.5,spaceAfter=0),
        'code':ParagraphStyle('Code',parent=body,fontName='Courier',fontSize=7.5,leading=11,backColor=colors.HexColor('#eef3f6'),borderPadding=8)}


def flows(path,brief=False):
    s=styles(brief); root=ET.fromstring('<root>'+prose(path)+'</root>'); out=[]; width=A4[0]-100
    for node in root:
        if node.tag in {'h1','h2','h3','h4','p'}:
            for img in node.iter('img'):
                src=(path.parent/img.get('src')).resolve()
                if src.is_file():
                    image=Image(str(src));scale=min(width/image.imageWidth,300/image.imageHeight)
                    image.drawWidth=image.imageWidth*scale;image.drawHeight=image.imageHeight*scale
                    image.keepWithNext=True; gap=Spacer(1,8);gap.keepWithNext=True
                    out.extend([Spacer(1,8),image,gap])
            text=inline(node)
            if text.strip():out.append(Paragraph(text,s.get(node.tag,s['h3'])))
        elif node.tag in {'ul','ol'}:
            for index,li in enumerate(node.findall('li'),1):
                out.append(Paragraph((str(index)+'. ' if node.tag=='ol' else '• ')+inline(li),s['li']))
        elif node.tag=='table':
            rows=node.findall('.//tr');data=[[Paragraph(inline(c),s['cell']) for c in row] for row in rows]
            if data:
                table=Table(data,colWidths=[width/len(data[0])]*len(data[0]),repeatRows=1,hAlign='LEFT')
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6f0f2')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#cbd9e1')),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
                out.extend([table,Spacer(1,10)])
        elif node.tag=='pre':
            text=''.join(node.itertext())
            out.append(Paragraph(html.escape(text).replace('\n','<br/>'),s['code']))
        elif node.tag=='blockquote':out.append(Paragraph(inline(node),s['p']))
    return out


def page(canvas,doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#cbdae2'));canvas.setLineWidth(.5);canvas.line(50, A4[1]-40,A4[0]-50,A4[1]-40)
    canvas.setFont('Vera-Bold',8);canvas.setFillColor(TEAL);canvas.drawString(50,A4[1]-29,'CEDAR  /  PROCUREMENT & ASSURANCE')
    canvas.setFont('Vera',7);canvas.setFillColor(INK);canvas.drawString(50,28,'Synthetic demonstration · Noah Weinberger · AI-assisted implementation')
    canvas.drawRightString(A4[0]-50,28,str(doc.page))
    canvas.restoreState()


def write_pdfs():
    pdf_setup();(OUT/'pdf').mkdir(parents=True,exist_ok=True)
    briefs=[]
    for index,name in enumerate(['EXECUTIVE_BRIEF_EN','EXECUTIVE_BRIEF_FR']):
        if index:briefs.append(PageBreak())
        briefs.extend(flows(ROOT/'docs'/f'{name}.md',brief=True))
    SimpleDocTemplate(str(OUT/'pdf/cedar-executive-briefs.pdf'),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=56,bottomMargin=48,title='CEDAR - Executive briefs / Notes de synthèse',author='Noah Weinberger; AI-assisted implementation').build(briefs,onFirstPage=page,onLaterPages=page)
    story=[]
    for index,name in enumerate(['CASE_STUDY','PILOT_PROPOSAL','INTERVIEW']):
        if index:story.append(PageBreak())
        story.extend(flows(ROOT/'docs'/f'{name}.md'))
    SimpleDocTemplate(str(OUT/'pdf/cedar-technical-portfolio.pdf'),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=56,bottomMargin=48,title='CEDAR - Technical portfolio and pilot',author='Noah Weinberger; AI-assisted implementation').build(story,onFirstPage=page,onLaterPages=page)


def sample_report():
    sys.path.insert(0,str(ROOT))
    from cedar.export import verify_package
    package=ROOT/'artifacts/full-decision.zip'
    checked=verify_package(package.read_bytes())
    if not checked['valid']:raise RuntimeError(checked)
    target=ROOT/'artifacts/sample-decision';target.mkdir(exist_ok=True)
    # Only this project's already verified output is unpacked for convenient review.
    with zipfile.ZipFile(package) as archive:archive.extractall(target)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--html-only', action='store_true', help='Refresh HTML while preserving historical PDFs')
    args = parser.parse_args()
    sample_report();write_html()
    if not args.html_only:write_pdfs()
    print(json.dumps({'landing':'PORTFOLIO.html','pdfs_preserved':args.html_only,'pdfs':['output/pdf/cedar-executive-briefs.pdf','output/pdf/cedar-technical-portfolio.pdf'],'html_documents':len(list((OUT/'html').glob('*.html')))}))
