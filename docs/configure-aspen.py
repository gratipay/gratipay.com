from nav import NavItem
from os.path import basename, dirname

website.renderer_default = "jinja2"
website.renderer_factories['jinja2'].Renderer.global_context = {
    'range': range,
    'unicode': unicode,
    'enumerate': enumerate,
    'len': len,
    'float': float,
    'type': type,
    'str': str,
}


def add_nav_to_website(website):
    website.nav = NavItem(website, None, website.www_root, '')

def add_nav_current_to_context(request, website):
    fs = request.fs
    if basename(request.fs) in website.indices:
        fs = dirname(fs)
    if fs in website.nav.by_fs:
        request.context['nav_current'] = website.nav.by_fs[fs]

add_nav_to_website(website)

website.algorithm.insert_after('dispatch_request_to_filesystem', add_nav_to_website)
website.algorithm.insert_after('dispatch_request_to_filesystem', add_nav_current_to_context)
