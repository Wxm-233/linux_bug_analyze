"""Optional real-browser smoke test; synthetic commits and a mock LLM only.

Run: python -X utf8 -m tests.review_browser_smoke
Requires playwright and an installed Chrome (or PLAYWRIGHT_CHANNEL).
"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace as NS

from playwright.sync_api import sync_playwright, expect

from linux_bug_analyze.config import FileSettings, CommitSourceSettings
from linux_bug_analyze.review_config import ReviewSettings
from linux_bug_analyze.review_workflow import ReviewWorkflow
from linux_bug_analyze.review_web import ReviewApplication, make_server
from tests.test_commit_source import _git, _commit
from tests.test_screening import response
from tests.test_review_reading import response as reading_response


def main():
    with TemporaryDirectory() as d:
        root=Path(d);repo=root/'linux';repo.mkdir()
        _git('init',cwd=repo);_git('config','user.email','tests@example.test',cwd=repo)
        _git('config','user.name','Tests',cwd=repo)
        hashes=[_commit(repo,'kernel/test.c',f'line {i}\n',title) for i,title in enumerate([
            'arm memory ordering fix','x86 spelling typo','riscv cache fix','mips alignment fix',
            's390 memory bug','arm64 page table fix','dma ordering fix','ordinary typo'])]
        settings=FileSettings(linux_dir=repo,commit_source=CommitSourceSettings(since='2000-01-01'),
            review=ReviewSettings(output_dir=root/'work',training_target=2,validation_size=2,
                                  audit_minimum=2,boundary_sample=1,workers=1))
        workflow=ReviewWorkflow(settings)
        original_screen=workflow.screen
        calls=[]
        def create(**kw):calls.append(kw);return response('related')
        workflow.screen=lambda: original_screen(NS(chat=NS(completions=NS(create=create))))
        reading_calls=[]
        def create_reading(**kw):
            reading_calls.append(kw)
            # Current article recovers once; the next exhausts its automatic retries.
            return reading_response('bad JSON') if len(reading_calls) in (1,3,4,5,6) else reading_response()
        workflow.reading_client=lambda:NS(chat=NS(completions=NS(create=create_reading)))
        app=ReviewApplication(workflow);server=make_server(app,0)
        thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(channel=os.environ.get('PLAYWRIGHT_CHANNEL','chrome'),headless=True)
                page=browser.new_page(viewport={'width':1280,'height':900})
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('dialog',lambda dialog:dialog.accept())
                page.goto(f'http://127.0.0.1:{server.server_port}/#{app.token}')
                page.locator('[data-action="prepare"]').click()
                expect(page.locator('#record')).to_be_visible(timeout=30000)
                expect(page.locator('#error')).to_have_text('')
                page.locator('#seed-search > summary').click()
                for h,label in zip(hashes[:2],['related','unrelated']):
                    page.locator('#query').fill(h)
                    page.locator('#search').click()
                    page.locator('#search-results button').first.click()
                    expect(page.locator('#identity')).to_contain_text(h)
                    page.locator('#note').fill('人工测试依据')
                    page.locator(f'[data-label="{label}"]').click()
                    expect(page.locator('#progress')).not_to_contain_text('运行中',timeout=30000)
                    expect(page.locator('#error')).to_have_text('')
                page.locator('[data-action="freeze"]').click()
                expect(page.locator('#role')).to_have_value('validation')
                expect(page.locator('#progress')).not_to_contain_text('运行中',timeout=30000)
                assert reading_calls == [], 'No summary API before opt-in'
                expect(page.locator('#record')).to_be_visible(timeout=30000)
                current_hash=page.locator('#identity').inner_text()
                page.locator('#note').fill('保留人工备注')
                page.locator('#auto-summary').check()
                expect(page.locator('#reading-summary')).to_contain_text('提交修改了内存访问方式',timeout=30000)
                expect(page.locator('#identity')).to_have_text(current_hash)
                expect(page.locator('#note')).to_have_value('保留人工备注')
                expect(page.locator('#reading-state')).to_contain_text('已用完 3 次自动重试',timeout=30000)
                expect(page.locator('#auto-summary')).to_be_checked()
                expect(page.locator('#note')).to_have_value('保留人工备注')
                assert len(reading_calls)==6
                page.locator('#auto-summary').uncheck()
                page.locator('#auto-summary').check()
                expect(page.locator('#reading-state')).to_contain_text('已就绪',timeout=30000)
                assert len(reading_calls)==7, 'Only failed next article should be requested again'
                # Hold an idle status response across a label submission. It must not
                # consume the completion transition or re-enable the old article.
                page.wait_for_function('() => !refreshing && !submitting')
                page.evaluate('''() => {
                    const originalFetch = window.fetch;
                    let hold = true;
                    window.fetch = async (...args) => {
                        const response = await originalFetch(...args);
                        if (hold && args[0] === '/api/status') {
                            hold = false;
                            window.statusHeld = true;
                            await new Promise(resolve => window.releaseStatus = resolve);
                        }
                        return response;
                    };
                    void refresh();
                }''')
                page.wait_for_function('() => window.statusHeld')
                for i in range(2):
                    expect(page.locator('#record')).to_be_visible(timeout=30000)
                    page.locator('[data-label="unrelated"]').click()
                    if i == 0:
                        page.evaluate('window.releaseStatus()')
                    expect(page.locator('#progress')).not_to_contain_text('运行中',timeout=30000)
                page.locator('#threshold').fill('0')
                page.locator('#auto-summary').uncheck()
                page.locator('#preview').click()
                expect(page.locator('#preview-result')).to_contain_text('"count": 3')
                page.locator('#select').click()
                expect(page.locator('#progress')).not_to_contain_text('运行中',timeout=30000)
                assert calls == [], 'No LLM calls before explicit confirmation'
                page.locator('#approve-api').check()
                page.locator('#screen').click()
                expect(page.locator('#progress')).not_to_contain_text('运行中',timeout=30000)
                expect(page.locator('#llm-status')).to_contain_text('相关 3')
                page.locator('[data-action="sample"]').click()
                expect(page.locator('#role')).to_have_value('audit')
                for _ in range(3):
                    expect(page.locator('#record')).to_be_visible(timeout=30000)
                    page.locator('[data-label="related"]').click()
                    expect(page.locator('#progress')).not_to_contain_text('运行中',timeout=30000)
                expect(page.locator('#audit-stats')).to_contain_text('100.0%')
                page.locator('[data-action="export"]').click()
                expect(page.locator('#progress')).not_to_contain_text('运行中',timeout=30000)
                with page.expect_download() as download:
                    page.locator('[data-download="summary.md"]').click()
                assert download.value.suggested_filename == 'summary.md'
                assert not errors, errors
                assert len(calls)==3
                assert workflow.summary()['summary_assisted_labels']['validation']==2
                browser.close()
                print('Browser smoke passed: prepare -> seeds -> freeze -> validation -> threshold -> mock LLM -> blind audit -> download.')
        finally:
            app.reading.close()
            server.shutdown();server.server_close();thread.join()
            if app.thread:app.thread.join()


if __name__=='__main__':
    main()
