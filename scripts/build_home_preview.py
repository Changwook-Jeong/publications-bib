"""Build an isolated, noindex Home proposal; never deploys or edits Google Sites."""
from __future__ import annotations
import argparse
from datetime import date
from pathlib import Path
import build_explorer as explorer
import build_publications as library


def build(output: Path, as_of: date | None = None) -> None:
    root=output/'publications-bib'
    root.mkdir(parents=True,exist_ok=True)
    source=explorer.ROOT
    page=library.build_page(library.parse_bibtex((source/'publications.bib').read_text(encoding='utf-8-sig')),
        library.load_roles(source/'author-roles.json'),(source/'web/index.template.html').read_text(encoding='utf-8'),
        library.load_members(source/'group-members.json'))
    (root/'index.html').write_text(page,encoding='utf-8')
    for asset in ('styles.css','app.js'):
        (root/asset).write_text((source/'web'/asset).read_text(encoding='utf-8'),encoding='utf-8')
    papers=explorer.build(root/'research-preview',as_of=as_of)
    context=explorer.group_context(papers).replace('href="cryogenic-transistors/"','href="publications-bib/research-preview/cryogenic-transistors/"').replace('href="chip-scale-multiphysics/"','href="publications-bib/research-preview/chip-scale-multiphysics/"').replace('href="semimetal-contact-physics/"','href="publications-bib/research-preview/semimetal-contact-physics/"')
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow"><title>Home proposal · Jeong Research Group · Preview only</title><link rel="stylesheet" href="publications-bib/research-preview/research.css"><style>
    .preview-notice{padding:10px 24px;background:#fff7de;font:12px/1.5 Arial,sans-serif;color:#6a542b}.home-brand{padding:18px 32px;color:white;font-weight:700;font-size:19px;background:#354f55}.home-hero{color:white;background:linear-gradient(125deg,#35494d 0 32%,#49636a 32% 63%,#3c5861 63%);padding:65px max(28px,calc((100% - 1160px)/2)) 75px}.home-hero h1{font-size:clamp(30px,4vw,42px);line-height:1.25;font-weight:400}.home-hero strong{display:block;font-size:15px;margin:28px 0 23px}.home-hero p{max-width:1100px;font-size:17px;line-height:1.7}.native-preview{width:min(1440px,calc(100% - 64px));margin:auto}.native-preview .group-context{margin:0 18px}.preview-frame{display:block;width:100%;border:0;min-height:1200px}.native-preview .join-strip{margin:15px 18px 0}.native-preview .join-strip h2{font-family:Georgia,serif}.preview-help{font-size:11px;color:#61717a;line-height:1.7;padding:14px 18px;border-top:1px solid #d7e2e2}.home-preview-footer{padding:24px 32px;color:#61717a;font-size:11px;border-top:1px solid #d7e2e2}@media(max-width:760px){.native-preview{width:calc(100% - 20px)}.native-preview .group-context{margin:0 8px}.home-hero{padding:40px 25px 45px}.home-brand{font-size:17px;padding:16px 25px}.preview-notice{padding:9px 20px}}
    </style></head><body><div class="preview-notice">LOCAL PREVIEW · Citation estimates + search-ready identity/source links. Not published to Google Sites or GitHub. Preview and unreviewed explanations remain noindex.</div><div class="home-brand">Jeong Research Group</div><header class="home-hero"><h1>Designing the next semiconductor frontier.</h1><strong>PHYSICS × COMPUTATION × INTELLIGENCE</strong><p>We combine atomic-scale physics, multiscale simulation, and device engineering with physics-grounded AI to understand and design emerging semiconductor materials and devices.</p></header><div class="native-preview">'''+context+'''
    <iframe id="research-preview-frame" class="preview-frame" title="Research activity, citation impact and recent papers" src="publications-bib/research-preview/?embed=1"></iframe>
    <section class="join-strip"><div><p class="eyebrow">YOUR NEXT RESEARCH QUESTION</p><h2>Find a question that moves you.</h2><p>Connect materials, processes, device behavior and data-driven design.</p></div><a class="join-link" href="https://sites.google.com/view/jeong-research-group/join-us">Explore opportunities at UNIST ↗</a></section><p class="preview-help">Search preparation: PI/group identity and selected-paper links above are ordinary page text, outside the iframe. Metadata and canonical URLs are added to research pages. No search-exposure or indexing change is active until a reviewed release.</p></div><footer class="home-preview-footer">© 2022–2026 Changwook Jeong Research Group · Local Home layout proposal</footer><script>
    const frame=document.getElementById('research-preview-frame');frame.addEventListener('load',()=>{const doc=frame.contentDocument;const resize=()=>{frame.style.height=(Math.ceil(doc.body.getBoundingClientRect().height)+5)+'px';};new ResizeObserver(resize).observe(doc.body);resize();});
    </script></body></html>'''
    page=page.replace('</style>','.home-hero{background:#405a61 url("https://ssl.gstatic.com/atari/images/simple-header-blended.png") center/cover}</style>')
    output.mkdir(parents=True,exist_ok=True)
    (output/'index.html').write_text(page,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--as-of',type=date.fromisoformat,default=None)
    args=parser.parse_args()
    build(args.output,as_of=args.as_of)
    print('Built isolated Home proposal; no deployment performed.')
