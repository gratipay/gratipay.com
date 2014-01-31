import misaka

def gfm(md):
    html = misaka.html( md
                      , misaka.EXT_STRIKETHROUGH | misaka.EXT_AUTOLINK
                      , misaka.HTML_SMARTYPANTS | misaka.HTML_TOC
                       )
    return html
