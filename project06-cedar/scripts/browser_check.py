"""Real Chromium walkthrough, screenshots, and optional paced silent recording."""
import argparse,json,os,socket,subprocess,sys,tempfile,time,urllib.request,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright,expect
from cedar.export import verify_package

ROOT=Path(__file__).resolve().parents[1]

def run(record=False):
    out=ROOT/'artifacts';shots=out/'screenshots';shots.mkdir(parents=True,exist_ok=True)
    errors=[];steps=[];start=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='cedar-browser-') as tmp:
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        log=open(out/'browser-server.log','w')
        server=subprocess.Popen([sys.executable,'-m','cedar','demo','--port',str(port),'--db',str(Path(tmp)/'browser.sqlite')],cwd=ROOT,stdout=log,stderr=log)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=.5);break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('Browser test server did not start')
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True)
                options={'viewport':{'width':1440,'height':960},'reduced_motion':'reduce'}
                if record:options.update(record_video_dir=str(Path(tmp)/'video'),record_video_size={'width':1440,'height':960})
                context=browser.new_context(**options);page=context.new_page()
                page.on('pageerror',lambda e:errors.append(str(e)))
                def pause(label,seconds=15):
                    steps.append(label);print(label,flush=True)
                    if record:page.wait_for_timeout(seconds*1000)
                def nav(view):
                    page.locator(f'#navigation [data-view="{view}"]').click();page.locator('#main-content h1').wait_for()
                def close():
                    if page.locator('#detail-dialog').is_visible():page.get_by_role('button',name='Close evidence panel').click()
                def sign(role):
                    close();page.locator('#session-button').click();page.select_option('#login-role',role);page.fill('#login-password','cedar-'+role)
                    page.locator('#login-form button[type=submit]').click();expect(page.locator('#login-dialog')).not_to_be_visible()
                    expect(page.locator('#session-button')).to_contain_text(role.capitalize())
                def review_approve(kind,role):
                    sign(role);page.locator(f'[data-action="snapshot-{kind}"]').first.click()
                    page.fill('#snapshot-action-note','Demonstration '+kind+': evidence and limitations inspected; no purchase authorized.')
                    page.locator('#snapshot-action-form button[type=submit]').click();expect(page.locator('#detail-dialog')).not_to_be_visible()
                page.goto(f'http://127.0.0.1:{port}');expect(page.locator('.commercial-table tbody tr')).to_have_count(12)
                assert '601 traceable assertions' in page.locator('body').inner_text()
                page.screenshot(path=shots/'overview.png');pause('01 Imported twelve synthetic packages and forty requirements',18)
                nav('requirements');page.screenshot(path=shots/'requirements.png')
                page.select_option('#requirement-package','P01')
                page.locator('.state-button[data-requirement="R02"]').click()
                expect(page.locator('#detail-body')).to_contain_text('Conflicting')
                page.locator('#detail-body [data-action="assertion"]').first.click()
                expect(page.locator('.source-lines')).to_be_visible()
                page.screenshot(path=shots/'evidence.png');pause('02 Inspected the battery conflict and exact source version',22)
                close();nav('evidence');page.select_option('#evidence-package','P01');page.screenshot(path=shots/'ledger.png')
                sign('analyst');nav('comparison');page.select_option('#compare-package','P03')
                page.fill('#replacement-rate','2');page.get_by_role('button',name='Save assumptions',exact=True).click()
                expect(page.locator('#revision-label')).to_contain_text('1')
                expect(page.locator('#main-content')).to_contain_text('$162,654.48')
                page.screenshot(path=shots/'comparison.png');pause('03 Changed the replacement assumption and inspected the resulting cost',20)
                page.get_by_role('heading',name='Weight sensitivity',exact=True).scroll_into_view_if_needed()
                page.screenshot(path=shots/'sensitivity.png');pause('04 Compared five declared weight scenarios and conservative dominance',20)
                nav('assurance');page.select_option('#assurance-package','P03')
                expect(page.locator('#main-content')).to_contain_text('2026-09-15')
                page.screenshot(path=shots/'assurance.png');pause('05 Inspected synthetic component exposure and its procurement consequence',18)
                nav('decisions');page.select_option('#decision-package','P03');page.select_option('#decision-kind','eligible')
                page.fill('#decision-rationale','Retain Birch Inspect Standard for documentary consideration under current evidence. No field capability or purchase authorization is implied.')
                page.get_by_role('button',name='Create snapshot',exact=True).click();expect(page.locator('article.snapshot')).to_have_count(1)
                pause('06 Created a snapshot tied to the current evidence and assumptions',14)
                review_approve('review','reviewer');pause('07 A technical reviewer recorded a digest-bound review',12)
                review_approve('approve','approver');expect(page.locator('article.snapshot').first).to_contain_text('Approved')
                page.locator('article.snapshot').first.scroll_into_view_if_needed();page.screenshot(path=shots/'approved.png');pause('08 A separate demonstration approver approved the recorded consideration',14)
                sign('analyst');nav('changes');page.get_by_role('button',name='Apply AMD01',exact=True).click()
                expect(page.locator('#revision-label')).to_contain_text('2')
                expect(page.locator('#main-content')).to_contain_text('1 stale decision snapshot')
                page.screenshot(path=shots/'changes.png');pause('09 Applied the supplier amendment; the old approval is visibly stale',24)
                nav('decisions');expect(page.locator('article.snapshot')).to_contain_text('Stale')
                page.select_option('#decision-package','P03');page.select_option('#decision-kind','conditional')
                page.fill('#decision-rationale','Hold for clarification: the support amendment does not meet the buyer requirement. This conditional decision preserves the open gate and requires a new commitment.')
                page.get_by_role('button',name='Create snapshot',exact=True).click();expect(page.locator('article.snapshot')).to_have_count(2)
                review_approve('review','reviewer');review_approve('approve','approver')
                page.locator('article.snapshot').first.scroll_into_view_if_needed();page.screenshot(path=shots/'decision.png')
                with page.expect_download() as download:
                    page.locator('article.snapshot').first.get_by_role('link',name='Export decision ZIP',exact=True).click()
                target=out/'browser-decision.zip';download.value.save_as(target)
                check=verify_package(target.read_bytes());assert check['valid'],check
                pause('10 Exported the new reviewed conditional record; package verification passed',24)
                close();nav('overview');page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), 'Mobile page overflows'
                page.screenshot(path=shots/'mobile.png',full_page=True)
                page.set_viewport_size({'width':1440,'height':960})
                page.keyboard.press('Tab');assert page.evaluate('document.activeElement.tagName') in ['A','BUTTON','SELECT','INPUT','MAIN']
                video=page.video
                context.close()
                if record:video.save_as(out/'cedar-demo.webm')
                browser.close()
                assert not errors,errors
        finally:
            server.terminate();server.wait(timeout=10);log.close()
    result={'passed':True,'executed_at':datetime.now(timezone.utc).isoformat(),'steps':steps,'page_errors':errors,'desktop':'1440x960','mobile':'390x844',
        'duration_seconds':round(time.perf_counter()-start,2),'recorded':record,'recording':'cedar-demo.webm' if record else None,
        'limits':'Automated interaction in one Chromium build. Silent recording of the actual application; narration script supplied separately. Not a human usability study.'}
    (out/'browser-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--record',action='store_true');run(ap.parse_args().record)
